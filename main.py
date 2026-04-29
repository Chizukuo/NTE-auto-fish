"""
main.py — NTE 自动钓鱼主程序
支持两种模式：
  - headless: python main.py（无需 dearpygui）
  - GUI:      python start_gui.py（通过 BotBridge 通信）
"""
import csv
import json
import logging
import os
import sys
import time
import ctypes
from typing import TYPE_CHECKING, Optional

try:
    import cv2
except ImportError as exc:
    raise ImportError(
        "Missing required dependency 'opencv-python-headless'. "
        "Please install dependencies with `pip install -r requirements.txt` "
        "or `pip install opencv-python-headless`."
    ) from exc

from config import CFG, AppConfig
from modules.io_module import CaptureModule, InputModule
from modules.logic import FishingState, FishingStateMachine, PIDController
from modules.vision import VisionModule

# 延迟导入：headless 模式无需 GUI 依赖
if TYPE_CHECKING:
    from gui.bridge import BotBridge

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("fishing_bot.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("NTEFish")

# 冻结为 EXE 时，__file__ 指向临时解压目录；模板文件应与 exe 同目录
if getattr(sys, 'frozen', False):
    os.chdir(os.path.dirname(sys.executable))
else:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))


class NTEFishingBot:
    def __init__(self, cfg: AppConfig = CFG, bridge: Optional["BotBridge"] = None) -> None:
        self.cfg = cfg
        self.bridge = bridge
        self.capture = CaptureModule()
        self.input = InputModule()
        self.vision = VisionModule()
        self.sm = FishingStateMachine()
        self.pid = PIDController(
            kp=cfg.pid.kp, ki=cfg.pid.ki, kd=cfg.pid.kd,
            integral_limit=cfg.pid.integral_limit,
            deadband=cfg.pid.deadband,
            adaptive=cfg.pid.adaptive,
        )

        self._roi_button: dict = dict(cfg.roi.button)
        self._roi_bar:    dict = dict(cfg.roi.bar)
        self._lost_frames: int = 0
        self._lost_cursor_frames: int = 0
        self._lost_target_frames: int = 0
        self._fish_count:  int = 0
        self._screen_w:    int = 0
        self._screen_h:    int = 0

        self._last_pid_out = 0.0
        self._cursor_x_rel = None
        self._target_x_rel = None
        self._session_start = time.time()
        self._is_paused = False
        self._stop_flag = False
        self._fps = 0.0
        self._last_time = time.time()

        self._log("Bot initialized.")

    # ---- Logging ----
    def _log(self, msg: str, level: int = logging.INFO):
        log.log(level, msg)
        if self.bridge:
            self.bridge.push_log(msg)

    # ---- Bridge communication ----
    def _push_status(self):
        if not self.bridge:
            return
        from gui.bridge import BotStatus
        self.bridge.push_status(BotStatus(
            state=self.sm.state,
            fish_count=self._fish_count,
            session_secs=time.time() - self._session_start,
            pid_output=self._last_pid_out,
            cursor_x=self._cursor_x_rel,
            target_x=self._target_x_rel,
            bar_width=self._roi_bar["width"],
            fps=self._fps,
            is_running=not self._is_paused,
        ))

    def _poll_commands(self):
        if not self.bridge:
            return
        cmd = self.bridge.poll_cmd()
        if cmd == "pause":
            self._is_paused = True
            self.input.release_all()
            self._log("Bot paused by user.")
        elif cmd == "resume":
            self._is_paused = False
            self._log("Bot resumed by user.")
        elif cmd == "recalibrate":
            self.calibrate()
        elif cmd == "stop":
            self._stop_flag = True
            self._log("Bot stop requested.")

    # ---- Calibration ----
    def calibrate(self) -> None:
        self._log("[Calibration] Grabbing full screen...")
        scene = self.capture.grab_full_screen()
        self._screen_w, self._screen_h = self.capture.get_screen_size()
        pad = self.cfg.calibration.roi_padding

        self._log(f"[Calibration] Screen resolution detected: {self._screen_w}x{self._screen_h}")

        def get_fallback_button():
            base_w, base_h = 3840, 2160
            scale_w, scale_h = self._screen_w / base_w, self._screen_h / base_h
            return {
                "top": int(1760 * scale_h), "left": int(3400 * scale_w),
                "width": int(440 * scale_w), "height": int(360 * scale_h),
            }

        def get_fallback_bar():
            # 使用用户提供的 4K 捕获基准 (118, 1209, 1441, 64)
            base_w, base_h = 3840, 2160
            scale_w, scale_h = self._screen_w / base_w, self._screen_h / base_h
            return {
                "top": int(118 * scale_h), "left": int(1209 * scale_w),
                "width": int(1441 * scale_w), "height": int(64 * scale_h),
            }

        tmpl_f = cv2.imread("templates/button_f.png")
        if tmpl_f is None:
            self._log("templates/button_f.png not found, using resolution fallback.", logging.WARNING)
            self._roi_button = get_fallback_button()
        else:
            result = self.vision.find_template_multi_scale(scene, tmpl_f)
            if result:
                x1, y1, x2, y2 = result
                self._roi_button = {
                    "top": max(0, y1 - pad), "left": max(0, x1 - pad),
                    "width": (x2 - x1) + pad * 2, "height": (y2 - y1) + pad * 2,
                }
                self._log(f"F Button ROI -> {self._roi_button}")
            else:
                self._log("F Button match failed. Using resolution fallback.", logging.WARNING)
                self._roi_button = get_fallback_button()
                self._log(f"F Button ROI (Fallback) -> {self._roi_button}")

        # 优先从 progress.json 加载精确比例
        progress_json = os.path.join(os.path.dirname(__file__), "templates", "progress.json")
        if os.path.exists(progress_json):
            try:
                with open(progress_json, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if data and isinstance(data, list) and "ratios" in data[0]:
                    r = data[0]["ratios"]
                    self._roi_bar = {
                        "top": round(self._screen_h * r["top"]),
                        "left": round(self._screen_w * r["left"]),
                        "width": round(self._screen_w * r["width"]),
                        "height": round(self._screen_h * r["height"]),
                    }
                    self._log(f"[Calibration] Loaded progress ROI from {progress_json} -> {self._roi_bar}")
                    self._log("[Calibration] Done.")
                    return
                self._log(
                    f"[Calibration] {progress_json} does not contain valid ratio data, using template/fallback.",
                    logging.WARNING)
            except Exception as e:
                self._log(f"Failed to load {progress_json}: {e}", logging.ERROR)
        else:
            self._log(f"{progress_json} not found, using template/fallback.", logging.WARNING)

        tmpl_bar = cv2.imread("templates/bar_icon_left.png")
        if tmpl_bar is None:
            self._log("templates/bar_icon_left.png not found, using resolution fallback.", logging.WARNING)
            self._roi_bar = get_fallback_bar()
        else:
            result = self.vision.find_template_multi_scale(scene, tmpl_bar)
            if result:
                x1, y1, x2, y2 = result
                icon_h = y2 - y1
                bar_left = x2 + 10
                # 如果模板匹配成功，依然可以使用 4K 基准的比例宽度来限定，防止太宽
                bar_width = int(self._screen_w * 0.375) # 1441/3840 ≈ 0.375
                self._roi_bar = {
                    "top": max(0, y1 - pad), "left": max(0, bar_left - pad),
                    "width": bar_width + pad * 2, "height": icon_h + pad * 2,
                }
                self._log(f"Progress Bar ROI -> {self._roi_bar}")
            else:
                self._log("Bar icon match failed. Using resolution fallback.", logging.WARNING)
                self._roi_bar = get_fallback_bar()
                self._log(f"Progress Bar ROI (Fallback) -> {self._roi_bar}")

        self._log("[Calibration] Done.")

    # ---- Main loop ----
    def run(self) -> None:
        self._log("Main loop started.")
        self._session_start = time.time()
        self._last_time = time.time()
        try:
            while not self._stop_flag:
                now = time.time()
                dt = now - self._last_time
                self._last_time = now
                if dt > 0:
                    current_fps = 1.0 / dt
                    # Simple EMA to smooth the FPS display
                    self._fps = self._fps * 0.9 + current_fps * 0.1

                self._poll_commands()
                self._push_status()

                if self._is_paused:
                    time.sleep(0.1)
                    continue

                s = self.sm.state
                if s is FishingState.IDLE:
                    self._handle_idle()
                elif s is FishingState.WAITING:
                    self._handle_waiting()
                elif s is FishingState.STRUGGLING:
                    self._handle_struggling()
                elif s is FishingState.RESULT:
                    self._handle_result()
        except KeyboardInterrupt:
            self._log("Ctrl+C received.")
        finally:
            self.input.release_all()
            self._log(f"Bot stopped. Fish caught: {self._fish_count}")

    # ---- State handlers ----
    def _handle_idle(self) -> None:
        self._log("[IDLE] Casting...")
        self.input.press(self.cfg.keys.cast,
                         self.cfg.timing.key_press_duration)
        time.sleep(self.cfg.timing.cast_animation_secs)
        self.sm.transition(FishingState.WAITING)

    def _handle_waiting(self) -> None:
        if self.sm.time_in_state > self.cfg.timing.bite_timeout_secs:
            self._log("[WAITING] Timeout, re-casting.", logging.WARNING)
            self.sm.transition(FishingState.IDLE)
            return
        btn_img = self.capture.grab_bgr(self._roi_button)
        if self.vision.check_blue_trigger(btn_img):
            self._log("[WAITING] Fish hooked!")
            self.input.press(self.cfg.keys.cast,
                             self.cfg.timing.key_press_duration)
            self.pid.reset()
            self._lost_frames = 0
            self._lost_cursor_frames = 0
            self._lost_target_frames = 0
            
            # 清空上一条鱼的坐标记忆，强制时空连贯性算法从最中间（50%）重新开始寻找！
            self._cursor_x_rel = None
            self._target_x_rel = None

            # 初始化数据记录
            with open("fishing_data.csv", "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([f"--- NEW FISH #{self._fish_count + 1} ---"])
                writer.writerow(["Time", "Cursor_X", "Target_X", "Error", "PID_Out", "Action"])

            self.sm.transition(FishingState.STRUGGLING)
        else:
            time.sleep(self.cfg.timing.waiting_poll_interval)

    def _handle_struggling(self) -> None:
        bar_img = self.capture.grab_bgr(self._roi_bar)
        cursor_x, _ = self.vision.get_hsv_centroid_x(
            bar_img, self.cfg.hsv.cursor.lower, self.cfg.hsv.cursor.upper, 
            ignore_margin_ratio=0.02, last_known_x=self._cursor_x_rel)
        target_x, _ = self.vision.get_hsv_centroid_x(
            bar_img, self.cfg.hsv.safe_zone.lower, self.cfg.hsv.safe_zone.upper, 
            ignore_margin_ratio=0.02, last_known_x=self._target_x_rel)

        self._cursor_x_rel = cursor_x
        self._target_x_rel = target_x

        output = 0.0
        action = "NONE"
        error = 0.0

        if cursor_x is not None and target_x is not None:
            self.pid.update_params(
                kp=self.cfg.pid.kp, ki=self.cfg.pid.ki, kd=self.cfg.pid.kd,
                deadband=self.cfg.pid.deadband, adaptive=self.cfg.pid.adaptive
            )
            self._lost_frames = 0
            self._lost_cursor_frames = 0
            self._lost_target_frames = 0
            error = float(target_x) - float(cursor_x)
            output = self.pid.update(float(cursor_x), float(target_x))
            self._last_pid_out = output
            dead = self.cfg.pid.deadband
            if output > dead:
                self.input.hold(self.cfg.keys.right)
                self.input.release(self.cfg.keys.left)
                action = "RIGHT"
            elif output < -dead:
                self.input.hold(self.cfg.keys.left)
                self.input.release(self.cfg.keys.right)
                action = "LEFT"
            else:
                self.input.release(self.cfg.keys.left)
                self.input.release(self.cfg.keys.right)
        else:
            self.input.release(self.cfg.keys.left)
            self.input.release(self.cfg.keys.right)
            self._last_pid_out = 0.0
            if cursor_x is None:
                self._lost_cursor_frames += 1
            else:
                self._lost_cursor_frames = 0
            if target_x is None:
                self._lost_target_frames += 1
            else:
                self._lost_target_frames = 0
            self._lost_frames = max(self._lost_cursor_frames, self._lost_target_frames)
            action = "LOST"

            # Log specific loss reason every 10 frames to avoid spamming but keep user informed
            if self._lost_frames % 10 == 0:
                missing = []
                if cursor_x is None: missing.append("Cursor")
                if target_x is None: missing.append("SafeZone")
                self._log(f"[STRUGGLING] Missing: {', '.join(missing)} ({self._lost_frames}/{self.cfg.timing.lost_frames_threshold})", logging.DEBUG)

        # 无论是否跟丢，如果开启 debug_mode，都强制写入 CSV
        if self.cfg.debug_mode:
            c_str = f"{cursor_x}" if cursor_x is not None else "None"
            t_str = f"{target_x}" if target_x is not None else "None"
            with open("fishing_data.csv", "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([f"{time.time():.3f}", c_str, t_str, f"{error:.1f}", f"{output:.3f}", action])

        if (self._lost_cursor_frames >= self.cfg.timing.lost_frames_threshold and
                self._lost_target_frames >= self.cfg.timing.lost_frames_threshold):
            missing = []
            if cursor_x is None: missing.append("Cursor")
            if target_x is None: missing.append("SafeZone")
            self._log(f"[STRUGGLING] Lost track of {', '.join(missing)} for too long ({self._lost_frames} frames). Exiting.")
            self.input.release_all()
            self.sm.transition(FishingState.RESULT)
        
        # 显式控制采样频率，防止 CPU 占用过高并稳定 PID 计算 (替代了原先调试窗口 waitKey 的延迟作用)
        time.sleep(self.cfg.timing.struggling_poll_interval)

    def _handle_result(self) -> None:
        self._fish_count += 1
        self._log(f"[RESULT] Fish #{self._fish_count}!")
        time.sleep(self.cfg.timing.result_wait_secs)
        if self.cfg.result_close_method == 'click':
            cx = self._screen_w // 2 if self._screen_w else 960
            cy = self._screen_h // 2 if self._screen_h else 540
            self.input.click(cx, cy)
        else:
            self.input.press(self.cfg.keys.exit,
                             self.cfg.timing.key_press_duration)
        time.sleep(0.5)
        self.sm.transition(FishingState.IDLE)


if __name__ == "__main__":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
    bot = NTEFishingBot()
    bot.calibrate()
    bot.run()

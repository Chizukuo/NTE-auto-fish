"""Core NTE Auto-Fish runtime.

Entry points:
  - Headless: python main.py
  - GUI:      python start_gui.py
"""
import csv
import ctypes
import json
import logging
import os
import sys
import time
from typing import TYPE_CHECKING, Optional

try:
    import cv2
except ImportError as exc:
    raise ImportError(
        "Missing required dependency 'opencv-python-headless'. "
        "Please install dependencies with `pip install -r requirements.txt` "
        "or `pip install opencv-python-headless`."
    ) from exc

from config import CFG, AppConfig  # noqa: E402
from modules.io_module import CaptureModule, InputModule  # noqa: E402
from modules.logic import FishingState, FishingStateMachine, PIDController  # noqa: E402
from modules.vision import VisionModule  # noqa: E402

if TYPE_CHECKING:
    from gui.bridge import BotBridge  # noqa: E402


def _app_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


APP_DIR = _app_dir()
os.chdir(APP_DIR)


def _resource_path(*parts: str) -> str:
    return os.path.join(APP_DIR, *parts)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("fishing_bot.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("NTEFish")


class NTEFishingBot:
    def __init__(
        self,
        cfg: AppConfig = CFG,
        bridge: Optional["BotBridge"] = None,
    ) -> None:
        self.cfg = cfg
        self.bridge = bridge
        self.capture = CaptureModule()
        self.input = InputModule()
        self.vision = VisionModule()
        self.sm = FishingStateMachine()
        self.pid = PIDController(
            kp=cfg.pid.kp,
            ki=cfg.pid.ki,
            kd=cfg.pid.kd,
            integral_limit=cfg.pid.integral_limit,
            deadband=cfg.pid.deadband,
            adaptive=cfg.pid.adaptive,
        )

        self._roi_button: dict = dict(cfg.roi.button)
        self._roi_bar: dict = dict(cfg.roi.bar)
        self._lost_frames = 0
        self._lost_cursor_frames = 0
        self._lost_target_frames = 0
        self._fish_count = 0
        self._screen_w = 0
        self._screen_h = 0

        self._last_pid_out = 0.0
        self._cursor_x_rel = None
        self._target_x_rel = None
        self._session_start = time.time()
        self._is_paused = False
        self._stop_flag = False
        self._is_stopped = True
        self._fps = 0.0
        self._last_time = time.time()

        self._log("Bot initialized.")

    @property
    def is_stopped(self) -> bool:
        return self._is_stopped

    def prepare_for_run(self, paused: bool = False) -> None:
        self._stop_flag = False
        self._is_stopped = False
        self._is_paused = paused
        self.sm = FishingStateMachine()
        self.pid.reset()
        self._fish_count = 0
        self._lost_frames = 0
        self._lost_cursor_frames = 0
        self._lost_target_frames = 0
        self._last_pid_out = 0.0
        self._cursor_x_rel = None
        self._target_x_rel = None
        self._fps = 0.0
        self._session_start = time.time()
        self._last_time = time.time()

    def request_stop(self) -> None:
        self._stop_flag = True
        self._is_paused = True
        self._is_stopped = True
        self._last_pid_out = 0.0
        self._fps = 0.0
        self.input.release_all()

    def publish_status(self) -> None:
        self._push_status()

    def _log(self, msg: str, level: int = logging.INFO):
        log.log(level, msg)
        if self.bridge:
            self.bridge.push_log(msg)

    def _push_status(self):
        if not self.bridge:
            return
        from gui.bridge import BotStatus

        self.bridge.push_status(
            BotStatus(
                state=self.sm.state,
                fish_count=self._fish_count,
                session_secs=time.time() - self._session_start,
                pid_output=self._last_pid_out,
                cursor_x=self._cursor_x_rel,
                target_x=self._target_x_rel,
                bar_width=self._roi_bar["width"],
                button_roi=self._roi_tuple(self._roi_button),
                bar_roi=self._roi_tuple(self._roi_bar),
                fps=0.0 if self._is_paused or self._is_stopped else self._fps,
                lost_frames=self._lost_frames,
                lost_cursor_frames=self._lost_cursor_frames,
                lost_target_frames=self._lost_target_frames,
                is_running=(
                    not self._is_paused
                    and not self._stop_flag
                    and not self._is_stopped
                ),
                is_stopped=self._is_stopped,
            )
        )

    @staticmethod
    def _roi_tuple(roi: dict) -> tuple[int, int, int, int]:
        return (
            int(roi.get("left", 0)),
            int(roi.get("top", 0)),
            int(roi.get("width", 0)),
            int(roi.get("height", 0)),
        )

    def _poll_commands(self):
        if not self.bridge:
            return
        while True:
            cmd = self.bridge.poll_cmd()
            if cmd is None:
                break
            self._handle_command(cmd)
            if self._stop_flag:
                break

    def _handle_command(self, cmd: str) -> None:
        if cmd == "pause":
            self._is_paused = True
            self.input.release_all()
            self._log("Bot paused by user.")
        elif cmd == "resume":
            if not self._is_stopped:
                self._is_paused = False
                self._log("Bot resumed by user.")
        elif cmd == "recalibrate":
            self._is_paused = True
            self.input.release_all()
            self._log("Recalibration requested.")
            self.calibrate()
        elif cmd == "stop":
            self.request_stop()
            self._log("Bot stop requested.")

    def calibrate(self) -> None:
        self._log("[Calibration] Capturing full screen...")
        scene = self.capture.grab_full_screen()
        self._screen_w, self._screen_h = self.capture.get_screen_size()
        pad = self.cfg.calibration.roi_padding
        self._log(
            f"[Calibration] Screen resolution: {self._screen_w}x{self._screen_h}"
        )

        def get_fallback_button():
            base_w, base_h = 3840, 2160
            scale_w = self._screen_w / base_w
            scale_h = self._screen_h / base_h
            return {
                "top": int(1760 * scale_h),
                "left": int(3400 * scale_w),
                "width": int(440 * scale_w),
                "height": int(360 * scale_h),
            }

        def get_fallback_bar():
            base_w, base_h = 3840, 2160
            scale_w = self._screen_w / base_w
            scale_h = self._screen_h / base_h
            return {
                "top": int(118 * scale_h),
                "left": int(1209 * scale_w),
                "width": int(1441 * scale_w),
                "height": int(64 * scale_h),
            }

        tmpl_f = cv2.imread(_resource_path("templates", "button_f.png"))
        if tmpl_f is None:
            self._log(
                "templates/button_f.png not found; using resolution fallback.",
                logging.WARNING,
            )
            self._roi_button = get_fallback_button()
        else:
            result = self.vision.find_template_multi_scale(
                scene,
                tmpl_f,
                self.cfg.calibration,
            )
            if result:
                x1, y1, x2, y2 = result
                self._roi_button = {
                    "top": max(0, y1 - pad),
                    "left": max(0, x1 - pad),
                    "width": (x2 - x1) + pad * 2,
                    "height": (y2 - y1) + pad * 2,
                }
                self._log(f"F button ROI -> {self._roi_button}")
            else:
                self._log(
                    "F button match failed; using resolution fallback.",
                    logging.WARNING,
                )
                self._roi_button = get_fallback_button()
                self._log(f"F button ROI (fallback) -> {self._roi_button}")

        progress_json = _resource_path("templates", "progress.json")
        if os.path.exists(progress_json):
            try:
                with open(progress_json, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                if data and isinstance(data, list) and "ratios" in data[0]:
                    ratios = data[0]["ratios"]
                    self._roi_bar = {
                        "top": round(self._screen_h * ratios["top"]),
                        "left": round(self._screen_w * ratios["left"]),
                        "width": round(self._screen_w * ratios["width"]),
                        "height": round(self._screen_h * ratios["height"]),
                    }
                    self._log(
                        "[Calibration] Loaded progress ROI from "
                        f"{progress_json} -> {self._roi_bar}"
                    )
                    self._log("[Calibration] Done.")
                    return
                self._log(
                    f"[Calibration] {progress_json} has no valid ratio data; "
                    "using template/fallback.",
                    logging.WARNING,
                )
            except Exception as exc:
                self._log(f"Failed to load {progress_json}: {exc}", logging.ERROR)
        else:
            self._log(
                f"{progress_json} not found; using template/fallback.",
                logging.WARNING,
            )

        tmpl_bar = cv2.imread(_resource_path("templates", "bar_icon_left.png"))
        if tmpl_bar is None:
            self._log(
                "templates/bar_icon_left.png not found; using resolution fallback.",
                logging.WARNING,
            )
            self._roi_bar = get_fallback_bar()
        else:
            result = self.vision.find_template_multi_scale(
                scene,
                tmpl_bar,
                self.cfg.calibration,
            )
            if result:
                x1, y1, x2, y2 = result
                icon_h = y2 - y1
                bar_left = x2 + 10
                bar_width = int(self._screen_w * 0.375)
                self._roi_bar = {
                    "top": max(0, y1 - pad),
                    "left": max(0, bar_left - pad),
                    "width": bar_width + pad * 2,
                    "height": icon_h + pad * 2,
                }
                self._log(f"Progress bar ROI -> {self._roi_bar}")
            else:
                self._log(
                    "Bar icon match failed; using resolution fallback.",
                    logging.WARNING,
                )
                self._roi_bar = get_fallback_bar()
                self._log(f"Progress bar ROI (fallback) -> {self._roi_bar}")

        self._log("[Calibration] Done.")

    def run(self) -> None:
        if self._stop_flag:
            self._is_paused = True
            self._is_stopped = True
            self._push_status()
            return

        self._is_stopped = False
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
                    self._fps = self._fps * 0.9 + current_fps * 0.1

                self._poll_commands()
                self._push_status()

                if self._is_paused:
                    time.sleep(0.1)
                    continue

                state = self.sm.state
                if state is FishingState.IDLE:
                    self._handle_idle()
                elif state is FishingState.WAITING:
                    self._handle_waiting()
                elif state is FishingState.STRUGGLING:
                    self._handle_struggling()
                elif state is FishingState.RESULT:
                    self._handle_result()
        except KeyboardInterrupt:
            self._log("Ctrl+C received.")
        finally:
            self._is_paused = True
            self._is_stopped = True
            self._last_pid_out = 0.0
            self._fps = 0.0
            self.input.release_all()
            self.capture.close()
            self._push_status()
            self._log(f"Bot stopped. Fish caught: {self._fish_count}")

    def _handle_idle(self) -> None:
        self._log("[IDLE] Casting...")
        self.input.press(self.cfg.keys.cast, self.cfg.timing.key_press_duration)
        time.sleep(self.cfg.timing.cast_animation_secs)
        self.sm.transition(FishingState.WAITING)

    def _handle_waiting(self) -> None:
        if self.sm.time_in_state > self.cfg.timing.bite_timeout_secs:
            self._log("[WAITING] Timeout, recasting.", logging.WARNING)
            self.sm.transition(FishingState.IDLE)
            return

        btn_img = self.capture.grab_bgr(self._roi_button)
        if self.vision.check_blue_trigger(
            btn_img,
            self.cfg.hsv.blue,
            self.cfg.min_blue_pixels,
        ):
            self._log("[WAITING] Fish hooked.")
            self.input.press(self.cfg.keys.cast, self.cfg.timing.key_press_duration)
            self.pid.reset()
            self._lost_frames = 0
            self._lost_cursor_frames = 0
            self._lost_target_frames = 0
            self._cursor_x_rel = None
            self._target_x_rel = None

            with open("fishing_data.csv", "a", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow([f"--- NEW FISH #{self._fish_count + 1} ---"])
                writer.writerow(
                    ["Time", "Cursor_X", "Target_X", "Error", "PID_Out", "Action"]
                )

            self.sm.transition(FishingState.STRUGGLING)
        else:
            time.sleep(self.cfg.timing.waiting_poll_interval)

    def _handle_struggling(self) -> None:
        bar_img = self.capture.grab_bgr(self._roi_bar)
        cursor_x, _ = self.vision.get_hsv_centroid_x(
            bar_img,
            self.cfg.hsv.cursor.lower,
            self.cfg.hsv.cursor.upper,
            ignore_margin_ratio=self.cfg.roi.ignore_margin_ratio,
            last_known_x=self._cursor_x_rel,
        )
        target_x, _ = self.vision.get_hsv_centroid_x(
            bar_img,
            self.cfg.hsv.safe_zone.lower,
            self.cfg.hsv.safe_zone.upper,
            ignore_margin_ratio=self.cfg.roi.ignore_margin_ratio,
            last_known_x=self._target_x_rel,
        )

        self._cursor_x_rel = cursor_x
        self._target_x_rel = target_x

        output = 0.0
        action = "NONE"
        error = 0.0

        if cursor_x is not None and target_x is not None:
            self.pid.update_params(
                kp=self.cfg.pid.kp,
                ki=self.cfg.pid.ki,
                kd=self.cfg.pid.kd,
                deadband=self.cfg.pid.deadband,
                adaptive=self.cfg.pid.adaptive,
                integral_limit=self.cfg.pid.integral_limit,
            )
            self._lost_frames = 0
            self._lost_cursor_frames = 0
            self._lost_target_frames = 0
            error = float(target_x) - float(cursor_x)
            output = self.pid.update(float(cursor_x), float(target_x))
            self._last_pid_out = output

            deadband = self.cfg.pid.deadband
            if output > deadband:
                self.input.hold(self.cfg.keys.right)
                self.input.release(self.cfg.keys.left)
                action = "RIGHT"
            elif output < -deadband:
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
            self._lost_frames = max(
                self._lost_cursor_frames,
                self._lost_target_frames,
            )
            action = "LOST"

            if self._lost_frames % 10 == 0:
                missing = []
                if cursor_x is None:
                    missing.append("Cursor")
                if target_x is None:
                    missing.append("Safe zone")
                self._log(
                    f"[STRUGGLING] Missing: {', '.join(missing)} "
                    f"({self._lost_frames}/{self.cfg.timing.lost_frames_threshold})",
                    logging.DEBUG,
                )

        if self.cfg.debug_mode:
            cursor_text = f"{cursor_x}" if cursor_x is not None else "None"
            target_text = f"{target_x}" if target_x is not None else "None"
            with open("fishing_data.csv", "a", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(
                    [
                        f"{time.time():.3f}",
                        cursor_text,
                        target_text,
                        f"{error:.1f}",
                        f"{output:.3f}",
                        action,
                    ]
                )

        if (
            self._lost_cursor_frames >= self.cfg.timing.lost_frames_threshold
            and self._lost_target_frames >= self.cfg.timing.lost_frames_threshold
        ):
            missing = []
            if cursor_x is None:
                missing.append("Cursor")
            if target_x is None:
                missing.append("Safe zone")
            self._log(
                f"[STRUGGLING] Lost track of {', '.join(missing)} "
                f"for too long ({self._lost_frames} frames)."
            )
            self.input.release_all()
            self.sm.transition(FishingState.RESULT)

        time.sleep(self.cfg.timing.struggling_poll_interval)

    def _handle_result(self) -> None:
        self._fish_count += 1
        self._log(f"[RESULT] Fish #{self._fish_count}.")
        time.sleep(self.cfg.timing.result_wait_secs)
        if self.cfg.result_close_method == "click":
            cx = self._screen_w // 2 if self._screen_w else 960
            cy = self._screen_h // 2 if self._screen_h else 540
            self.input.click(cx, cy)
        else:
            self.input.press(self.cfg.keys.exit, self.cfg.timing.key_press_duration)
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

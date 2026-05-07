"""Core NTE Auto-Fish runtime.

Entry points:
  - Headless: python main.py
  - GUI:      python start_gui.py
"""
import argparse
import csv
import ctypes
import json
import logging
import os
import sys
import threading
import time
from dataclasses import asdict
from typing import TYPE_CHECKING, Optional

from screeninfo import get_monitors

from config import CFG, AppConfig, DEFAULT_SETTINGS_PATH
from modules.logic import FishingState, FishingStateMachine, PIDController
from modules.utils import APP_DIR, bundled_path

# Third-party imports — deferred so deps can be auto-installed in __main__.
try:
    import cv2
    from modules.io_module import CaptureModule, InputModule
    from modules.vision import VisionModule
    _TP_LOADED = True
except ImportError:
    cv2 = CaptureModule = InputModule = VisionModule = None  # type: ignore[assignment]
    _TP_LOADED = False

if TYPE_CHECKING:
    from gui.bridge import BotBridge  # noqa: E402

# CWD is set inside run() to avoid side effects on import

_DEFAULT_SCREEN_W = 3840
_DEFAULT_SCREEN_H = 2160
_RESULT_CLOSE_FALLBACK_X = 960
_RESULT_CLOSE_FALLBACK_Y = 540
_BAR_WIDTH_RATIO = 0.375
_MAX_STRUGGLE_SECS = 120.0
_BAIT_ERROR_THRESHOLD = 3


def _resource_path(*parts: str) -> str:
    return bundled_path(*parts)


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
        self._roi_error: dict = {}
        self._bait_error_count = 0
        self._lost_frames = 0
        self._lost_cursor_frames = 0
        self._lost_target_frames = 0
        self._fish_count = 0
        self._screen_w = 0
        self._screen_h = 0
        self._scaled_min_area = 50.0

        self._last_pid_out = 0.0
        self._cursor_x_rel = None
        self._target_x_rel = None
        self._session_start = time.time()
        self._is_paused = False
        self._stop_flag = False
        self._stop_event = threading.Event()
        self._is_stopped = True
        self._fps = 0.0
        self._last_time = time.time()

        self._log("Bot initialized.")

    @property
    def is_stopped(self) -> bool:
        return self._is_stopped

    def prepare_for_run(self, paused: bool = False) -> None:
        self._stop_flag = False
        self._stop_event.clear()
        self._is_stopped = False
        self._is_paused = paused
        self.sm = FishingStateMachine()
        self.pid.reset()
        self._fish_count = 0
        self._bait_error_count = 0
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
        self._stop_event.set()
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
                bar_width=self._roi_bar.get("width", 0),
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

    @staticmethod
    def get_active_monitor():
        monitors = get_monitors()

        index = max(0, min(CFG.monitor_index, len(monitors) - 1))

        return monitors[index]

    def calibrate(self) -> None:
        self._log("[Calibration] Capturing full screen...")

        mon = self.get_active_monitor()

        region = {
            "left": mon.x,
            "top": mon.y,
            "width": mon.width,
            "height": mon.height,
        }

        scene = self.capture.grab_bgr(region)
        self._screen_w, self._screen_h = mon.width, mon.height
        scale = min(self._screen_w / _DEFAULT_SCREEN_W, self._screen_h / _DEFAULT_SCREEN_H)
        self._scaled_min_area = max(50.0 * scale * scale, 1.0)
        pad = self.cfg.calibration.roi_padding
        self._log(
            f"[Calibration] Screen resolution: {self._screen_w}x{self._screen_h}"
        )

        # --- Bar ROI (ratio-based, primary method) ---
        progress_json = _resource_path("templates", "progress.json")
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
                self._log(f"[Calibration] Bar ROI (ratio) -> {self._roi_bar}")
            else:
                raise ValueError("no valid ratio data")
        except Exception:
            scale_w = self._screen_w / _DEFAULT_SCREEN_W
            scale_h = self._screen_h / _DEFAULT_SCREEN_H
            self._roi_bar = {
                "top": int(118 * scale_h),
                "left": int(1209 * scale_w),
                "width": int(1441 * scale_w),
                "height": int(64 * scale_h),
            }
            self._log(f"[Calibration] Bar ROI (fallback) -> {self._roi_bar}")

        # --- Button ROI (template matching with resolution fallback) ---
        scale_w = self._screen_w / _DEFAULT_SCREEN_W
        scale_h = self._screen_h / _DEFAULT_SCREEN_H
        button_fallback = {
            "top": int(1760 * scale_h),
            "left": int(3400 * scale_w),
            "width": int(440 * scale_w),
            "height": int(360 * scale_h),
        }

        tmpl_f = cv2.imread(_resource_path("templates", "button_f.png"))
        if tmpl_f is not None:
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
                self._log(f"[Calibration] Button ROI (template) -> {self._roi_button}")
            else:
                self._roi_button = button_fallback
                self._log(f"[Calibration] Button ROI (fallback) -> {self._roi_button}")
        else:
            self._roi_button = button_fallback
            self._log(f"[Calibration] Button ROI (fallback) -> {self._roi_button}")

        self._load_error_roi()

        self._log("[Calibration] Done.")

    def _load_error_roi(self) -> None:
        error_json = _resource_path("templates", "error.json")
        if not os.path.exists(error_json):
            return
        try:
            with open(error_json, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            if data and isinstance(data, list) and "ratios" in data[0]:
                ratios = data[0]["ratios"]
                self._roi_error = {
                    "top": round(self._screen_h * ratios["top"]),
                    "left": round(self._screen_w * ratios["left"]),
                    "width": round(self._screen_w * ratios["width"]),
                    "height": round(self._screen_h * ratios["height"]),
                }
                self._log(f"[Calibration] Loaded error ROI -> {self._roi_error}")
        except Exception as exc:
            self._log(f"Failed to load {error_json}: {exc}", logging.ERROR)

    def run(self) -> None:
        os.chdir(APP_DIR)

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
                    self._stop_event.wait(timeout=0.1)
                    continue

                state = self.sm.state

                # --- Priority 1: bar element detection → immediate STRUGGLING ---
                if state is not FishingState.STRUGGLING and self._roi_bar:
                    bar_img = self.capture.grab_bgr(self._roi_bar)
                    cur_x, _ = self.vision.get_hsv_centroid_x(
                        bar_img,
                        self.cfg.hsv.cursor.lower,
                        self.cfg.hsv.cursor.upper,
                        min_area=self._scaled_min_area,
                        ignore_margin_ratio=self.cfg.roi.ignore_margin_ratio,
                    )
                    tgt_x, _ = self.vision.get_hsv_centroid_x(
                        bar_img,
                        self.cfg.hsv.safe_zone.lower,
                        self.cfg.hsv.safe_zone.upper,
                        min_area=self._scaled_min_area,
                        ignore_margin_ratio=0.0,
                    )
                    if cur_x is not None or tgt_x is not None:
                        self._log(f"[{state.value}] Bar detected → STRUGGLING.")
                        self._enter_struggling()
                        self._push_status()
                        continue

                # --- Priority 2: error dialog detection (IDLE only) ---
                if state is FishingState.IDLE and self._roi_error:
                    err_img = self.capture.grab_bgr(self._roi_error)
                    if self.vision.check_error_region(err_img):
                        self._bait_error_count += 1
                        self._log(
                            f"[ERROR] Cast error ({self._bait_error_count}/{_BAIT_ERROR_THRESHOLD}), "
                            "waiting for dialog to dismiss..."
                        )
                        self.input.release_all()
                        self._stop_event.wait(timeout=5.0)
                        if self._bait_error_count >= _BAIT_ERROR_THRESHOLD:
                            self._log("[ERROR] Bait likely exhausted, stopping bot.")
                            self.request_stop()
                            self._push_status()
                            continue
                        self.sm.transition(FishingState.IDLE)
                        self._push_status()
                        continue

                # --- State handlers ---
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
        except Exception as exc:
            self._log(f"Bot crashed: {exc}", logging.ERROR)
        finally:
            self._is_paused = True
            self._is_stopped = True
            self._last_pid_out = 0.0
            self._fps = 0.0
            try:
                self.input.release_all()
            except Exception:
                pass
            try:
                self.capture.close()
            except Exception:
                pass
            try:
                self._push_status()
                self._log(f"Bot stopped. Fish caught: {self._fish_count}")
            except Exception:
                pass

    def _enter_struggling(self) -> None:
        """Common setup when transitioning into STRUGGLING from any state."""
        self._bait_error_count = 0
        self.input.press(self.cfg.keys.cast, self.cfg.timing.key_press_duration)
        self.pid.reset()
        self._lost_frames = 0
        self._lost_cursor_frames = 0
        self._lost_target_frames = 0
        self._cursor_x_rel = None
        self._target_x_rel = None
        self.sm.transition(FishingState.STRUGGLING)

    def _handle_idle(self) -> None:
        self._log("[IDLE] Casting...")
        self.input.press(self.cfg.keys.cast, self.cfg.timing.key_press_duration)
        self._stop_event.wait(timeout=self.cfg.timing.cast_animation_secs)
        if self._stop_flag:
            return
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
            self._log("[WAITING] Fish hooked (blue trigger).")
            self._enter_struggling()
        else:
            self._stop_event.wait(timeout=self.cfg.timing.waiting_poll_interval)

    def _handle_struggling(self) -> None:
        if self.sm.time_in_state > _MAX_STRUGGLE_SECS:
            self._log(
                f"[STRUGGLING] Max duration ({_MAX_STRUGGLE_SECS}s) reached, ending.",
                logging.WARNING,
            )
            self.input.release_all()
            self.sm.transition(FishingState.RESULT)
            return

        bar_img = self.capture.grab_bgr(self._roi_bar)
        cursor_x, _ = self.vision.get_hsv_centroid_x(
            bar_img,
            self.cfg.hsv.cursor.lower,
            self.cfg.hsv.cursor.upper,
            min_area=self._scaled_min_area,
            ignore_margin_ratio=self.cfg.roi.ignore_margin_ratio,
            last_known_x=self._cursor_x_rel,
        )
        target_x, _ = self.vision.get_hsv_centroid_x(
            bar_img,
            self.cfg.hsv.safe_zone.lower,
            self.cfg.hsv.safe_zone.upper,
            min_area=self._scaled_min_area,
            ignore_margin_ratio=0.0,
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
                ema_alpha=self.cfg.pid.ema_alpha,
                max_dt=self.cfg.pid.max_dt,
            )
            self._lost_frames = 0
            self._lost_cursor_frames = 0
            self._lost_target_frames = 0
            error = float(target_x) - float(cursor_x)
            bar_half = self._roi_bar.get("width", 400) / 2
            output = self.pid.update(float(cursor_x), float(target_x), bar_half_width=bar_half)
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
            try:
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
            except OSError:
                pass

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

        self._stop_event.wait(timeout=self.cfg.timing.struggling_poll_interval)

    def _handle_result(self) -> None:
        self._stop_event.wait(timeout=self.cfg.timing.result_wait_secs)
        if self._stop_flag:
            return

        # Verify the mini-game actually ended before counting a fish.
        # If the cursor or safe zone is still visible on the bar, the
        # STRUGGLING → RESULT transition was premature (tracking was
        # temporarily lost). Release keys and go back to IDLE to recast.
        bar_img = self.capture.grab_bgr(self._roi_bar)
        cur_x, _ = self.vision.get_hsv_centroid_x(
            bar_img,
            self.cfg.hsv.cursor.lower,
            self.cfg.hsv.cursor.upper,
            min_area=self._scaled_min_area,
            ignore_margin_ratio=self.cfg.roi.ignore_margin_ratio,
        )
        tgt_x, _ = self.vision.get_hsv_centroid_x(
            bar_img,
            self.cfg.hsv.safe_zone.lower,
            self.cfg.hsv.safe_zone.upper,
            min_area=self._scaled_min_area,
            ignore_margin_ratio=0.0,
        )
        if cur_x is not None or tgt_x is not None:
            self._log(
                "[RESULT] Mini-game still active (bar elements detected) — "
                "recovering to IDLE.",
                logging.WARNING,
            )
            self.input.release_all()
            self.sm.transition(FishingState.IDLE)
            return

        self._fish_count += 1
        self._log(f"[RESULT] Fish #{self._fish_count}.")
        if self.cfg.result_close_method == "click":
            cx = self._screen_w // 2 if self._screen_w else _RESULT_CLOSE_FALLBACK_X
            cy = self._screen_h // 2 if self._screen_h else _RESULT_CLOSE_FALLBACK_Y
            self.input.click(cx, cy)
        else:
            self.input.press(self.cfg.keys.exit, self.cfg.timing.key_press_duration)
        self._stop_event.wait(timeout=0.5)
        if self._stop_flag:
            return
        self.sm.transition(FishingState.IDLE)


def _set_dpi_awareness() -> None:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# CLI command handlers
# ---------------------------------------------------------------------------

def _cmd_start(_args: argparse.Namespace) -> None:
    bot = NTEFishingBot()
    bot.calibrate()
    bot.run()


def _cmd_calibrate(_args: argparse.Namespace) -> None:
    bot = NTEFishingBot()
    bot.calibrate()
    print(f"Button ROI: {bot._roi_button}")
    print(f"Bar ROI:    {bot._roi_bar}")
    if bot._roi_error:
        print(f"Error ROI:  {bot._roi_error}")
    print("Calibration complete.")


def _cmd_reset(_args: argparse.Namespace) -> None:
    CFG.reset()
    print(f"Configuration reset to defaults: {DEFAULT_SETTINGS_PATH}")


def _cmd_config_show(args: argparse.Namespace) -> None:
    data = asdict(CFG)
    section = getattr(args, "section", None)
    if section:
        parts = section.split(".")
        obj = data
        for p in parts:
            if isinstance(obj, dict) and p in obj:
                obj = obj[p]
            else:
                print(f"Unknown config path: {section}")
                return
        print(json.dumps({parts[-1]: obj} if isinstance(obj, (dict, list)) else {parts[-1]: obj}, indent=4, ensure_ascii=False))
    else:
        print(json.dumps(data, indent=4, ensure_ascii=False))


def _resolve_cfg_path(path: str):
    """Walk the CFG dataclass by dot-separated path. Returns (parent, attr, current_value)."""
    parts = path.split(".")
    obj = CFG
    for p in parts[:-1]:
        if not hasattr(obj, p):
            return None, None, None
        child = getattr(obj, p)
        if hasattr(child, "__dataclass_fields__"):
            obj = child
        else:
            return None, None, None
    attr = parts[-1]
    if not hasattr(obj, attr):
        return None, None, None
    return obj, attr, getattr(obj, attr)


def _parse_value(raw: str, target):
    """Convert a string value to match the target's type."""
    if isinstance(target, bool):
        return raw.lower() in ("true", "1", "yes")
    if isinstance(target, tuple):
        return tuple(int(x.strip()) for x in raw.strip("() ").split(","))
    if isinstance(target, int):
        return int(raw)
    if isinstance(target, float):
        return float(raw)
    return raw


def _cmd_config_set(args: argparse.Namespace) -> None:
    parent, attr, current = _resolve_cfg_path(args.key)
    if parent is None:
        print(f"Unknown config key: {args.key}")
        return
    try:
        new_val = _parse_value(args.value, current)
    except (ValueError, TypeError) as exc:
        print(f"Invalid value '{args.value}' for {args.key}: {exc}")
        return
    setattr(parent, attr, new_val)
    CFG.save()
    print(f"{args.key} = {new_val!r}")


def _interactive_menu() -> None:
    while True:
        print()
        print("=== NTE Auto-Fish ===")
        print("1. Start fishing bot")
        print("2. Calibrate (show ROI results)")
        print("3. Show configuration")
        print("4. Edit configuration")
        print("5. Reset configuration to defaults")
        print("0. Exit")
        choice = input("\nSelect [0-5]: ").strip()

        if choice == "1":
            _cmd_start(argparse.Namespace())
            break
        elif choice == "2":
            _cmd_calibrate(argparse.Namespace())
        elif choice == "3":
            _cmd_config_show(argparse.Namespace(section=None))
        elif choice == "4":
            _interactive_edit_config()
        elif choice == "5":
            confirm = input("Reset all settings to defaults? [y/N]: ").strip().lower()
            if confirm == "y":
                _cmd_reset(argparse.Namespace())
        elif choice == "0":
            print("Bye.")
            break
        else:
            print("Invalid choice.")


def _interactive_edit_config() -> None:
    categories = [
        ("PID parameters", [
            ("pid.kp", "Proportional gain"),
            ("pid.ki", "Integral gain"),
            ("pid.kd", "Derivative gain"),
            ("pid.integral_limit", "Integral limit"),
            ("pid.deadband", "Deadband"),
            ("pid.adaptive", "Adaptive (true/false)"),
            ("pid.ema_alpha", "EMA alpha"),
            ("pid.max_dt", "Max dt"),
        ]),
        ("HSV thresholds", [
            ("hsv.blue.lower", "Blue lower (H,S,V)"),
            ("hsv.blue.upper", "Blue upper (H,S,V)"),
            ("hsv.safe_zone.lower", "Safe zone lower (H,S,V)"),
            ("hsv.safe_zone.upper", "Safe zone upper (H,S,V)"),
            ("hsv.cursor.lower", "Cursor lower (H,S,V)"),
            ("hsv.cursor.upper", "Cursor upper (H,S,V)"),
        ]),
        ("Key bindings", [
            ("keys.cast", "Cast key"),
            ("keys.left", "Left key"),
            ("keys.right", "Right key"),
            ("keys.exit", "Exit key"),
        ]),
        ("Timing", [
            ("timing.cast_animation_secs", "Cast animation (s)"),
            ("timing.bite_timeout_secs", "Bite timeout (s)"),
            ("timing.lost_frames_threshold", "Lost frames threshold"),
            ("timing.result_wait_secs", "Result wait (s)"),
            ("timing.key_press_duration", "Key press duration (s)"),
        ]),
        ("Other", [
            ("min_blue_pixels", "Min blue pixels"),
            ("result_close_method", "Result close (click/esc)"),
            ("debug_mode", "Debug mode (true/false)"),
        ]),
    ]

    while True:
        print()
        print("--- Edit Configuration ---")
        for i, (name, _) in enumerate(categories, 1):
            print(f"  {i}. {name}")
        print("  0. Back")
        cat_choice = input("\nSelect category [0-5]: ").strip()
        if cat_choice == "0":
            return
        try:
            idx = int(cat_choice) - 1
            cat_name, fields = categories[idx]
        except (ValueError, IndexError):
            print("Invalid choice.")
            continue

        while True:
            print(f"\n--- {cat_name} ---")
            for i, (key, desc) in enumerate(fields, 1):
                _, _, val = _resolve_cfg_path(key)
                print(f"  {i}. {desc} ({key}) = {val!r}")
            print("  0. Back")
            field_choice = input("\nSelect field to edit [0, 1-{}]: ".format(len(fields))).strip()
            if field_choice == "0":
                break
            try:
                fi = int(field_choice) - 1
                key, desc = fields[fi]
            except (ValueError, IndexError):
                print("Invalid choice.")
                continue
            _, _, current = _resolve_cfg_path(key)
            new_val = input(f"  New value for {desc} (current: {current!r}): ").strip()
            if not new_val:
                print("  Cancelled.")
                continue
            _cmd_config_set(argparse.Namespace(key=key, value=new_val))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Auto-install missing dependencies before anything else
    if not _TP_LOADED:
        from modules.deps import ensure_dependencies, CLI_PACKAGES
        ensure_dependencies(CLI_PACKAGES)
        import cv2  # noqa: F811
        from modules.io_module import CaptureModule, InputModule  # noqa: F811
        from modules.vision import VisionModule  # noqa: F811

    _set_dpi_awareness()

    parser = argparse.ArgumentParser(
        prog="NTE-Auto-Fish",
        description="NTE Auto-Fishing bot — headless/CLI mode",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("start", help="Run the fishing bot")
    sub.add_parser("calibrate", help="Calibrate and show ROI results")
    sub.add_parser("reset", help="Reset settings.json to defaults")

    cfg_parser = sub.add_parser("config", help="View or edit configuration")
    cfg_sub = cfg_parser.add_subparsers(dest="config_action")

    show_parser = cfg_sub.add_parser("show", help="Show current configuration")
    show_parser.add_argument("section", nargs="?", default=None,
                             help="Dot path to show (e.g. pid, hsv.blue)")

    set_parser = cfg_sub.add_parser("set", help="Set a config value")
    set_parser.add_argument("key", help="Dot path, e.g. pid.kp")
    set_parser.add_argument("value", help="New value")

    args = parser.parse_args()

    if args.command is None:
        _interactive_menu()
    elif args.command == "start":
        _cmd_start(args)
    elif args.command == "calibrate":
        _cmd_calibrate(args)
    elif args.command == "reset":
        _cmd_reset(args)
    elif args.command == "config":
        if args.config_action == "show":
            _cmd_config_show(args)
        elif args.config_action == "set":
            _cmd_config_set(args)
        else:
            cfg_parser.print_help()
    else:
        parser.print_help()

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
import logging.handlers
import os
import sys
import threading
import time
from dataclasses import asdict
from random import SystemRandom
from typing import TYPE_CHECKING, Optional

from config import CFG, AppConfig, DEFAULT_SETTINGS_PATH, jitter as cfg_jitter, sample_noise, sample_reaction
from modules.logic import FishingState, FishingStateMachine, PIDController
from modules.utils import APP_DIR, bundled_path

# Third-party imports — deferred so entrypoints can validate dependencies first.
try:
    import cv2
    from screeninfo import get_monitors
    from modules.io_module import CaptureModule, InputModule
    from modules.vision import VisionModule
    _TP_LOADED = True
except ImportError:
    cv2 = CaptureModule = InputModule = VisionModule = None  # type: ignore[assignment]
    get_monitors = None  # type: ignore[assignment]
    _TP_LOADED = False

if TYPE_CHECKING:
    from gui.bridge import BotBridge  # noqa: E402

# CWD is set inside run() to avoid side effects on import
_RNG = SystemRandom()

_DEFAULT_SCREEN_W = 3840
_DEFAULT_SCREEN_H = 2160
_RESULT_CLOSE_FALLBACK_X = 960
_RESULT_CLOSE_FALLBACK_Y = 540
_BAR_WIDTH_RATIO = 0.375
# _MAX_STRUGGLE_SECS and _BAIT_ERROR_THRESHOLD moved to TimingConfig


def _resource_path(*parts: str) -> str:
    return bundled_path(*parts)


LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
DATE_FORMAT = "%H:%M:%S"

logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=DATE_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.handlers.RotatingFileHandler(
            os.path.join(APP_DIR, "fishing_bot.log"),
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        ),
    ],
)
log = logging.getLogger("NTEFish")


class NTEFishingBot:
    def __init__(
        self,
        cfg: AppConfig = CFG,
        bridge: Optional["BotBridge"] = None,
    ) -> None:
        if not _TP_LOADED:
            raise RuntimeError(
                "Missing runtime dependencies. Install with: "
                f"{sys.executable} -m pip install -r requirements.txt"
            )

        self.cfg = cfg
        self.bridge = bridge
        
        if bridge:
            from gui.bridge import BridgeHandler
            handler = BridgeHandler(bridge)
            handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
            # Add to root logger to capture all messages, or just 'NTEFish'
            logging.getLogger().addHandler(handler)

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
        self._mon_x = 0
        self._mon_y = 0
        self._current_scale = 1.0
        self._scaled_min_area = 30.0
        self._scaled_blue_pixels = 300
        self._scaled_error_white_min = 1200

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
        self._last_action = "NONE"
        self._consecutive_waiting_timeouts = 0

        self._log("Bot initialized.")
        self._csv_handle = None
        self._csv_writer = None

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
        self._last_action = "NONE"
        self._consecutive_waiting_timeouts = 0

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
                scaled_min_area=self._scaled_min_area,
                current_scale=self._current_scale,
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
                self._bait_error_count = 0
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

    def get_active_monitor(self):
        monitors = get_monitors()

        index = max(0, min(self.cfg.monitor_index, len(monitors) - 1))

        return monitors[index]

    def _offset_roi(self, roi: dict) -> dict:
        """Shift a monitor-local ROI to screen-absolute coordinates."""
        return {
            "left": roi["left"] + self._mon_x,
            "top": roi["top"] + self._mon_y,
            "width": roi["width"],
            "height": roi["height"],
        }

    def calibrate(self) -> None:
        self._log("[Calibration] Capturing full screen...")

        mon = self.get_active_monitor()

        region = {
            "left": mon.x,
            "top": mon.y,
            "width": mon.width,
            "height": mon.height,
        }

        try:
            scene = self.capture.grab_bgr(region)
        except Exception as e:
            self._log(f"[Calibration] Failed to capture screen: {e}. Is the game fullscreen and minimized?", logging.ERROR)
            self.request_stop()
            return

        self._screen_w, self._screen_h = mon.width, mon.height
        self._mon_x, self._mon_y = mon.x, mon.y
        self._current_scale = min(self._screen_w / _DEFAULT_SCREEN_W, self._screen_h / _DEFAULT_SCREEN_H)
        
        # Scale area and pixel thresholds quadratically with resolution
        scale_sq = self._current_scale * self._current_scale
        self._scaled_min_area = max(self.cfg.detection_min_area * scale_sq, 1.0)
        self._scaled_blue_pixels = int(max(self.cfg.min_blue_pixels * scale_sq, 1.0))
        self._scaled_error_white_min = int(max(1200 * scale_sq, 10.0))
        
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
                self._roi_bar = self._offset_roi({
                    "top": round(self._screen_h * ratios["top"]),
                    "left": round(self._screen_w * ratios["left"]),
                    "width": round(self._screen_w * ratios["width"]),
                    "height": round(self._screen_h * ratios["height"]),
                })
                self._log(f"[Calibration] Bar ROI (ratio) -> {self._roi_bar}")
            else:
                raise ValueError("no valid ratio data")
        except Exception:
            scale_w = self._screen_w / _DEFAULT_SCREEN_W
            scale_h = self._screen_h / _DEFAULT_SCREEN_H
            self._roi_bar = self._offset_roi({
                "top": int(118 * scale_h),
                "left": int(1209 * scale_w),
                "width": int(1441 * scale_w),
                "height": int(64 * scale_h),
            })
            self._log(f"[Calibration] Bar ROI (fallback) -> {self._roi_bar}")

        # --- Button ROI (template matching with resolution fallback) ---
        scale_w = self._screen_w / _DEFAULT_SCREEN_W
        scale_h = self._screen_h / _DEFAULT_SCREEN_H
        button_fallback = self._offset_roi({
            "top": int(1760 * scale_h),
            "left": int(3400 * scale_w),
            "width": int(440 * scale_w),
            "height": int(360 * scale_h),
        })

        tmpl_f = cv2.imread(_resource_path("templates", "button_f.png"))
        if tmpl_f is not None:
            result = self.vision.find_template_multi_scale(
                scene,
                tmpl_f,
                self.cfg.calibration,
            )
            if result:
                x1, y1, x2, y2 = result
                self._roi_button = self._offset_roi({
                    "top": max(0, y1 - pad),
                    "left": max(0, x1 - pad),
                    "width": (x2 - x1) + pad * 2,
                    "height": (y2 - y1) + pad * 2,
                })
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
                self._roi_error = self._offset_roi({
                    "top": round(self._screen_h * ratios["top"]),
                    "left": round(self._screen_w * ratios["left"]),
                    "width": round(self._screen_w * ratios["width"]),
                    "height": round(self._screen_h * ratios["height"]),
                })
                self._log(f"[Calibration] Loaded dialog ROI -> {self._roi_error}")
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
                    hsv_img = self.vision.to_hsv(bar_img)
                    cur_x, _ = self.vision.get_hsv_centroid_x(
                        bar_img,
                        self.cfg.hsv.cursor.lower,
                        self.cfg.hsv.cursor.upper,
                        min_area=self._scaled_min_area,
                        ignore_margin_ratio=self.cfg.roi.ignore_margin_ratio,
                        hsv_img=hsv_img,
                    )
                    tgt_x, _ = self.vision.get_hsv_centroid_x(
                        bar_img,
                        self.cfg.hsv.safe_zone.lower,
                        self.cfg.hsv.safe_zone.upper,
                        min_area=self._scaled_min_area,
                        ignore_margin_ratio=0.0,
                        hsv_img=hsv_img,
                    )
                    if cur_x is not None or tgt_x is not None:
                        self._log(f"[{state.value}] Bar detected → STRUGGLING.")
                        self._enter_struggling()
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
        except Exception:
            log.exception("Bot crashed")
        finally:
            self._is_paused = True
            self._is_stopped = True
            self._last_pid_out = 0.0
            self._fps = 0.0
            try:
                self.input.release_all()
            except Exception:
                log.debug("Failed to release held keys during shutdown.", exc_info=True)
            try:
                self.capture.close()
            except Exception:
                log.debug("Failed to close capture module during shutdown.", exc_info=True)
            try:
                if self._csv_handle:
                    self._csv_handle.close()
                    self._csv_handle = None
            except Exception:
                log.debug("Failed to close debug CSV handle during shutdown.", exc_info=True)
            try:
                self._push_status()
                self._log(f"Bot stopped. Fish caught: {self._fish_count}")
            except Exception:
                log.debug("Failed to push final status during shutdown.", exc_info=True)

    def _enter_struggling(self) -> None:
        """Common setup when transitioning into STRUGGLING from any state."""
        self._bait_error_count = 0
        self._consecutive_waiting_timeouts = 0
        self._bar_detected_in_struggle = False

        # Humanized hook reaction latency
        if self.cfg.humanization.enabled:
            react = _RNG.uniform(
                self.cfg.humanization.hook_reaction_min,
                self.cfg.humanization.hook_reaction_max
            )
            if react > 0:
                self._stop_event.wait(timeout=react)
        hook_dur = self.cfg.timing.key_press_duration
        if self.cfg.humanization.enabled:
            hook_dur = cfg_jitter(hook_dur, self.cfg.humanization.cast_hold_jitter, minimum=0.02)
        self.input.press(self.cfg.keys.cast, hook_dur)
        self.pid.reset()
        self._lost_frames = 0
        self._lost_cursor_frames = 0
        self._lost_target_frames = 0
        self._cursor_x_rel = None
        self._target_x_rel = None
        self.sm.transition(FishingState.STRUGGLING)

    def _handle_idle(self) -> None:
        self._log("[IDLE] Casting...")
        cast_dur = self.cfg.timing.key_press_duration
        if self.cfg.humanization.enabled:
            cast_dur = cfg_jitter(cast_dur, self.cfg.humanization.cast_hold_jitter, minimum=0.02)
        self.input.press(self.cfg.keys.cast, cast_dur)
        # Check for error dialog shortly after cast (dialog appears immediately)
        self._stop_event.wait(timeout=0.3)
        if self._roi_error:
            err_img = self.capture.grab_bgr(self._roi_error)
            if self.vision.check_error_region(err_img, white_pixel_min=self._scaled_error_white_min):
                self._bait_error_count += 1
                self._log(
                    f"[ERROR] Cast error ({self._bait_error_count}/{self.cfg.timing.bait_error_threshold}), "
                    "waiting for dialog to dismiss..."
                )
                self.input.release_all()
                err_wait = 5.0
                if self.cfg.humanization.enabled:
                    err_wait = cfg_jitter(err_wait, self.cfg.humanization.error_dialog_jitter, minimum=3.0)
                self._stop_event.wait(timeout=err_wait)
                if self._bait_error_count >= self.cfg.timing.bait_error_threshold:
                    self._log("[ERROR] Bait likely exhausted, stopping bot.")
                    self.request_stop()
                    self._push_status()
                    return
                self.sm.transition(FishingState.IDLE)
                self._push_status()
                return
        # No error, wait out the rest of the cast animation
        anim_secs = self.cfg.timing.cast_animation_secs
        if self.cfg.humanization.enabled:
            anim_secs = cfg_jitter(anim_secs, self.cfg.humanization.cast_animation_jitter, minimum=0.8)
        remaining = anim_secs - 0.3
        if remaining > 0:
            self._stop_event.wait(timeout=remaining)
        if self._stop_flag:
            return
        self.sm.transition(FishingState.WAITING)

    def _handle_waiting(self) -> None:
        if self.sm.time_in_state > self.cfg.timing.bite_timeout_secs:
            self._consecutive_waiting_timeouts += 1
            if self._consecutive_waiting_timeouts >= 2:
                self._log(
                    f"[WAITING] Consecutive timeout ({self._consecutive_waiting_timeouts}), "
                    "checking if stuck in result screen...",
                    logging.WARNING,
                )
                self._dismiss_result()
                self._consecutive_waiting_timeouts = 0
            else:
                self._log("[WAITING] Timeout, recasting.", logging.WARNING)

            self.sm.transition(FishingState.IDLE)
            return

        btn_img = self.capture.grab_bgr(self._roi_button)
        if self.vision.check_blue_trigger(
            btn_img,
            self.cfg.hsv.blue,
            self._scaled_blue_pixels,
        ):
            self._log("[WAITING] Fish hooked (blue trigger).")
            self._enter_struggling()
        else:
            self._stop_event.wait(timeout=self.cfg.timing.waiting_poll_interval)

    def _handle_struggling(self) -> None:
        if self.sm.time_in_state > self.cfg.timing.max_struggle_secs:
            self._log(
                f"[STRUGGLING] Max duration ({self.cfg.timing.max_struggle_secs}s) reached, ending.",
                logging.WARNING,
            )
            self.input.release_all()
            self.sm.transition(FishingState.RESULT)
            return

        bar_img = self.capture.grab_bgr(self._roi_bar)
        hsv_img = self.vision.to_hsv(bar_img)
        
        cursor_x, _ = self.vision.get_hsv_centroid_x(
            bar_img,
            self.cfg.hsv.cursor.lower,
            self.cfg.hsv.cursor.upper,
            min_area=self._scaled_min_area,
            ignore_margin_ratio=self.cfg.roi.ignore_margin_ratio,
            last_known_x=self._cursor_x_rel,
            hsv_img=hsv_img,
        )
        target_x, _ = self.vision.get_hsv_centroid_x(
            bar_img,
            self.cfg.hsv.safe_zone.lower,
            self.cfg.hsv.safe_zone.upper,
            min_area=self._scaled_min_area,
            ignore_margin_ratio=0.0,
            last_known_x=self._target_x_rel,
            hsv_img=hsv_img,
        )

        self._cursor_x_rel = cursor_x
        self._target_x_rel = target_x

        output = 0.0
        action = "NONE"
        error = 0.0

        if cursor_x is not None or target_x is not None:
            self._bar_detected_in_struggle = True

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
            hcfg = self.cfg.humanization
            deadband = self.cfg.pid.deadband
            bar_width = self._roi_bar.get("width", 400)
            intensity = min(1.0, abs(error) / max(bar_width / 2, 1.0))

            if hcfg.enabled:
                now = time.perf_counter()
                
                # Initialize state variables on first run or transition
                if not hasattr(self, "_hum_reaction_end"):
                    self._hum_reaction_end = 0.0
                    self._hum_pulse_end = 0.0
                    self._hum_pulse_state = "IDLE"
                    self._hum_target_action = "NONE"

                # PID noise overlay
                if hcfg.pid_noise_enabled:
                    output += sample_noise(hcfg.pid_noise_amplitude, hcfg.pid_noise_dist)

                # Determine the desired action based on PID output
                desired_action = "NONE"
                if output > deadband:
                    desired_action = "RIGHT"
                elif output < -deadband:
                    desired_action = "LEFT"

                # Check if we need to start a new reaction delay
                if desired_action != self._hum_target_action:
                    self._hum_target_action = desired_action
                    
                    # Adaptive humanization
                    if hcfg.adaptive_enabled:
                        latency_factor = max(hcfg.adaptive_latency_min_scale, 1.0 - intensity * (1.0 - hcfg.adaptive_latency_min_scale))
                    else:
                        latency_factor = 1.0
                        
                    react_delay = sample_reaction(
                        hcfg.reaction_latency_min * latency_factor,
                        hcfg.reaction_latency_max * latency_factor,
                        hcfg.reaction_latency_dist,
                    )
                    
                    # If we are just stopping, or continuing a similar motion, reduce latency
                    if desired_action == "NONE" or \
                       (desired_action == "RIGHT" and self._last_action == "RIGHT") or \
                       (desired_action == "LEFT" and self._last_action == "LEFT"):
                        react_delay *= 0.3
                        
                    self._hum_reaction_end = now + react_delay

                # Determine the *effective* action we should take right now
                if now < self._hum_reaction_end:
                    # Still in reaction time, keep doing whatever we were doing (or NONE if we just started)
                    effective_action = self._last_action
                else:
                    effective_action = self._hum_target_action

                # Handle pulsing logic for the effective action
                if effective_action == "RIGHT" or effective_action == "LEFT":
                    target_key = self.cfg.keys.right if effective_action == "RIGHT" else self.cfg.keys.left
                    opposite_key = self.cfg.keys.left if effective_action == "RIGHT" else self.cfg.keys.right
                    
                    # Release the opposite key immediately
                    self.input.release(opposite_key)

                    # Manage pulsing state machine
                    if self._hum_pulse_state == "IDLE" or now >= self._hum_pulse_end:
                        if self._hum_pulse_state == "GAP" or self._hum_pulse_state == "IDLE":
                            # Transition to HOLD
                            if hcfg.adaptive_enabled:
                                hold_factor = 1.0 + intensity * (hcfg.adaptive_pulse_hold_max_scale - 1.0)
                            else:
                                hold_factor = 1.0
                            hold_t = _RNG.uniform(hcfg.pulse_hold_min * hold_factor, hcfg.pulse_hold_max * hold_factor)
                            self._hum_pulse_end = now + hold_t
                            self._hum_pulse_state = "HOLD"
                            self.input.hold(target_key)
                        else:
                            # Transition to GAP (Release)
                            if hcfg.adaptive_enabled:
                                gap_factor = max(hcfg.adaptive_pulse_gap_min_scale, 1.0 - intensity * (1.0 - hcfg.adaptive_pulse_gap_min_scale))
                            else:
                                gap_factor = 1.0
                            gap_t = _RNG.uniform(hcfg.pulse_release_min * gap_factor, hcfg.pulse_release_max * gap_factor)
                            self._hum_pulse_end = now + gap_t
                            self._hum_pulse_state = "GAP"
                            self.input.release(target_key)
                            
                    action = effective_action
                else:
                    # Effective action is NONE
                    self.input.release(self.cfg.keys.left)
                    self.input.release(self.cfg.keys.right)
                    self._hum_pulse_state = "IDLE"
                    
                    if hcfg.deadband_tap_enabled and _RNG.random() < hcfg.deadband_tap_chance:
                        tap_dir = self.cfg.keys.right if error > 0 else self.cfg.keys.left
                        tap_dur = _RNG.uniform(hcfg.deadband_tap_duration_min, hcfg.deadband_tap_duration_max)
                        # We use pulse_hold here safely since deadband taps are tiny and rare, 
                        # but ideally this should also be non-blocking. Let's just use pulse_hold as it's quick.
                        # Wait, tap_dur is ~0.02s, which is a tiny block, acceptable in deadband.
                        self.input.pulse_hold(tap_dir, tap_dur, 0.0, self._stop_event)
                        
                    action = "NONE"
            else:
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
                    action = "NONE"
            
            self._last_action = action
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
                if not self._csv_handle:
                    self._csv_handle = open("fishing_data.csv", "a", newline="", encoding="utf-8")
                    self._csv_writer = csv.writer(self._csv_handle)
                
                self._csv_writer.writerow(
                    [
                        f"{time.time():.3f}",
                        cursor_text,
                        target_text,
                        f"{error:.1f}",
                        f"{output:.3f}",
                        action,
                    ]
                )
                # Flush occasionally or let OS handle it for performance
                if _RNG.random() < 0.05:
                    self._csv_handle.flush()
            except Exception:
                log.debug("Failed to append debug CSV row.", exc_info=True)

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
            if getattr(self, "_bar_detected_in_struggle", False):
                self.sm.transition(FishingState.RESULT)
            else:
                self._log(
                    "[STRUGGLING] Never saw bar elements — assuming false hook, recasting.",
                    logging.WARNING,
                )
                self.input.release_all()
                self.sm.transition(FishingState.IDLE)

        poll = self.cfg.timing.struggling_poll_interval
        if self.cfg.humanization.enabled:
            poll = cfg_jitter(poll, poll * 0.3, minimum=0.005)
        self._stop_event.wait(timeout=poll)

    def _handle_result(self) -> None:
        # Check for error dialog early — it auto-dismisses in ~2s
        if self._roi_error:
            err_img = self.capture.grab_bgr(self._roi_error)
            if self.vision.check_error_region(err_img, white_pixel_min=self._scaled_error_white_min):
                self._log("[RESULT] Error dialog detected (fish escaped?).")
                self.sm.transition(FishingState.IDLE)
                self._push_status()
                return

        result_w = self.cfg.timing.result_wait_secs
        if self.cfg.humanization.enabled:
            result_w = cfg_jitter(result_w, self.cfg.humanization.result_wait_jitter, minimum=1.0)
        self._stop_event.wait(timeout=result_w)
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
        self._dismiss_result()
        self.sm.transition(FishingState.IDLE)

    def _dismiss_result(self) -> None:
        """Dismiss the result screen by clicking or pressing the exit key."""
        if self._stop_flag:
            return

        if self.cfg.result_close_method == "click":
            base_x = self._screen_w // 2 if self._screen_w else _RESULT_CLOSE_FALLBACK_X
            # Typically click towards the lower middle (e.g. around 75% height)
            base_y = int(self._screen_h * 0.75) if self._screen_h else int(_RESULT_CLOSE_FALLBACK_Y * 1.5)
            
            if self.cfg.humanization.enabled:
                hcfg = self.cfg.humanization
                cx = self._mon_x + base_x + _RNG.randint(-hcfg.mouse_offset_x, hcfg.mouse_offset_x)
                cy = self._mon_y + base_y + _RNG.randint(-hcfg.mouse_offset_y, hcfg.mouse_offset_y)
                self.input.humanized_click(
                    cx, cy,
                    amp=hcfg.mouse_move_curve_amplitude,
                    d_min=hcfg.mouse_move_duration_min,
                    d_max=hcfg.mouse_move_duration_max
                )
            else:
                cx = self._mon_x + base_x
                cy = self._mon_y + base_y
                self.input.click(cx, cy)
        else:
            exit_dur = self.cfg.timing.key_press_duration
            if self.cfg.humanization.enabled:
                exit_dur = cfg_jitter(exit_dur, self.cfg.humanization.cast_hold_jitter, minimum=0.02)
            self.input.press(self.cfg.keys.exit, exit_dur)

        close_delay = 0.5
        if self.cfg.humanization.enabled:
            close_delay = cfg_jitter(close_delay, self.cfg.humanization.post_close_jitter, minimum=0.2)
        self._stop_event.wait(timeout=close_delay)


def _set_dpi_awareness() -> None:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        log.debug("SetProcessDpiAwareness failed; trying SetProcessDPIAware.", exc_info=True)
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            log.debug("SetProcessDPIAware failed.", exc_info=True)


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
        ("Humanization", [
            ("humanization.enabled", "Enabled (true/false)"),
            ("humanization.mouse_move_curve_amplitude", "Mouse curve amplitude (px)"),
            ("humanization.mouse_move_duration_min", "Mouse move duration min (s)"),
            ("humanization.mouse_move_duration_max", "Mouse move duration max (s)"),
            ("humanization.mouse_offset_x", "Mouse click offset X (px)"),
            ("humanization.mouse_offset_y", "Mouse click offset Y (px)"),
            ("humanization.hook_reaction_min", "Hook reaction delay min (s)"),
            ("humanization.hook_reaction_max", "Hook reaction delay max (s)"),
            ("humanization.pulse_hold_min", "Pulse hold min (s)"),
            ("humanization.pulse_hold_max", "Pulse hold max (s)"),
            ("humanization.pulse_release_min", "Pulse release min (s)"),
            ("humanization.pulse_release_max", "Pulse release max (s)"),
            ("humanization.reaction_latency_min", "Struggle reaction min (s)"),
            ("humanization.reaction_latency_max", "Struggle reaction max (s)"),
            ("humanization.pid_noise_enabled", "PID noise (true/false)"),
            ("humanization.pid_noise_amplitude", "PID noise amplitude (px)"),
            ("humanization.adaptive_enabled", "Adaptive focus (true/false)"),
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
    # Validate dependencies before runtime startup.
    from modules.deps import CLI_PACKAGES, exit_if_missing_dependencies

    exit_if_missing_dependencies(CLI_PACKAGES)

    if not _TP_LOADED:
        import cv2  # noqa: F811
        from screeninfo import get_monitors  # noqa: F811
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

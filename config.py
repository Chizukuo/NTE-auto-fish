"""Single source of runtime configuration for NTE Auto-Fish."""
import json
import logging
import os
from dataclasses import asdict, dataclass, field
from random import SystemRandom
from typing import Tuple

from modules.utils import APP_DIR

DEFAULT_SETTINGS_PATH = os.path.join(APP_DIR, "settings.json")
log = logging.getLogger("NTEFish")
_RNG = SystemRandom()


@dataclass
class HsvRange:
    lower: Tuple[int, int, int]
    upper: Tuple[int, int, int]


@dataclass
class HsvConfig:
    blue: HsvRange = field(
        default_factory=lambda: HsvRange((100, 160, 140), (130, 255, 255))
    )
    safe_zone: HsvRange = field(
        default_factory=lambda: HsvRange((75, 190, 190), (100, 255, 255))
    )
    cursor: HsvRange = field(
        default_factory=lambda: HsvRange((18, 115, 240), (40, 150, 255))
    )


@dataclass
class PidConfig:
    kp: float = 0.45
    ki: float = 0.05
    kd: float = 0.005
    integral_limit: float = 150.0
    deadband: float = 5.0
    adaptive: bool = True
    ema_alpha: float = 0.25
    max_dt: float = 0.1


@dataclass
class RoiConfig:
    button: dict = field(
        default_factory=lambda: {
            "top": 1760,
            "left": 3400,
            "width": 440,
            "height": 360,
        }
    )
    bar: dict = field(
        default_factory=lambda: {
            "top": 60,
            "left": 700,
            "width": 2440,
            "height": 160,
        }
    )
    ignore_margin_ratio: float = 0.02


@dataclass
class TimingConfig:
    cast_animation_secs: float = 1.8
    bite_timeout_secs: float = 45.0
    lost_frames_threshold: int = 40
    result_wait_secs: float = 3.0
    key_press_duration: float = 0.05
    waiting_poll_interval: float = 0.05
    struggling_poll_interval: float = 0.01
    bait_error_threshold: int = 3
    max_struggle_secs: float = 120.0


@dataclass
class HumanizationConfig:
    enabled: bool = True

    # Key hold pulse modulation (STRUGGLING)
    pulse_hold_min: float = 0.030
    pulse_hold_max: float = 0.080
    pulse_release_min: float = 0.008
    pulse_release_max: float = 0.025

    # Deadband micro-corrections (STRUGGLING)
    deadband_tap_enabled: bool = True
    deadband_tap_chance: float = 0.30
    deadband_tap_duration_min: float = 0.015
    deadband_tap_duration_max: float = 0.035

    # Reaction latency (STRUGGLING)
    reaction_latency_min: float = 0.04
    reaction_latency_max: float = 0.12
    reaction_latency_dist: str = "uniform"  # "uniform" / "gaussian" / "exponential"

    # PID output noise overlay (STRUGGLING)
    pid_noise_enabled: bool = True
    pid_noise_amplitude: float = 3.0  # pixels
    pid_noise_dist: str = "gaussian"  # "uniform" / "gaussian"

    # Adaptive humanization (Intensity-based focus)
    adaptive_enabled: bool = True
    adaptive_latency_min_scale: float = 0.3
    adaptive_pulse_gap_min_scale: float = 0.2
    adaptive_pulse_hold_max_scale: float = 1.5

    # Timing jitter spreads (+/- on base values)
    cast_hold_jitter: float = 0.015
    cast_animation_jitter: float = 0.20
    result_wait_jitter: float = 0.25
    post_close_jitter: float = 0.12
    error_dialog_jitter: float = 0.40

    # Mouse Trajectory (RESULT stage)
    mouse_move_curve_amplitude: int = 150
    mouse_move_duration_min: float = 0.15
    mouse_move_duration_max: float = 0.30
    mouse_offset_x: int = 150
    mouse_offset_y: int = 50
    
    # Hook Reaction Latency (WAITING stage)
    hook_reaction_min: float = 0.1
    hook_reaction_max: float = 0.25


@dataclass
class CalibrationConfig:
    scale_min: float = 0.5
    scale_max: float = 2.0
    scale_steps: int = 30
    confidence_threshold: float = 0.72
    roi_padding: int = 25


@dataclass
class KeyConfig:
    cast: str = "f"
    left: str = "a"
    right: str = "d"
    exit: str = "esc"


@dataclass
class HotkeyConfig:
    toggle: str = "f8"
    stop: str = "f12"


@dataclass
class AppConfig:
    hsv: HsvConfig = field(default_factory=HsvConfig)
    pid: PidConfig = field(default_factory=PidConfig)
    roi: RoiConfig = field(default_factory=RoiConfig)
    timing: TimingConfig = field(default_factory=TimingConfig)
    calibration: CalibrationConfig = field(default_factory=CalibrationConfig)
    keys: KeyConfig = field(default_factory=KeyConfig)
    hotkeys: HotkeyConfig = field(default_factory=HotkeyConfig)
    humanization: HumanizationConfig = field(default_factory=HumanizationConfig)
    detection_min_area: float = 30.0
    min_blue_pixels: int = 300
    result_close_method: str = "click"
    debug_mode: bool = False
    always_on_top: bool = True
    monitor_index: int = 0
    fish_logging_enabled: bool = False
    ocr_name_roi_ratios: tuple = (0.35, 0.30, 0.65, 0.42)
    ocr_weight_roi_ratios: tuple = (0.45, 0.43, 0.55, 0.52)

    def save(self, path=None):
        path = path or DEFAULT_SETTINGS_PATH
        tmp_path = f"{path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(asdict(self), handle, indent=4)
        os.replace(tmp_path, path)

    def reset(self, path=None):
        default_cfg = AppConfig()
        
        def reset_obj(target, source):
            for field_name in target.__dataclass_fields__:
                val = getattr(source, field_name)
                attr = getattr(target, field_name)
                if hasattr(attr, "__dataclass_fields__"):
                    reset_obj(attr, val)
                else:
                    setattr(target, field_name, val)
        
        reset_obj(self, default_cfg)
        self.save(path)

    def load(self, path=None):
        path = path or DEFAULT_SETTINGS_PATH
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)

            def update_obj(obj, values):
                for key, value in values.items():
                    if not hasattr(obj, key):
                        continue
                    attr = getattr(obj, key)
                    if isinstance(value, dict) and hasattr(attr, "__dataclass_fields__"):
                        update_obj(attr, value)
                    elif isinstance(value, list):
                        setattr(obj, key, tuple(value))
                    else:
                        setattr(obj, key, value)

            update_obj(self, data)
        except (OSError, ValueError, TypeError) as exc:
            log.error("Failed to load settings from %s: %s", path, exc)


def jitter(base: float, spread: float, minimum: float = 0.0) -> float:
    """Return base +/- spread, clamped to [minimum, ...]."""
    if spread <= 0.0:
        return base
    return max(minimum, base + _RNG.uniform(-spread, spread))


def sample_reaction(min_val: float, max_val: float, dist: str = "uniform") -> float:
    """Sample a reaction delay from the specified distribution."""
    if min_val >= max_val:
        return min_val
    if dist == "gaussian":
        mean = (min_val + max_val) / 2
        std = (max_val - min_val) / 6  # 99.7% within range
        return max(min_val, min(max_val, _RNG.gauss(mean, std)))
    if dist == "exponential":
        span = max_val - min_val
        # mean = span/3, so most values cluster toward the low end
        return min(max_val, min_val + _RNG.expovariate(3.0 / span))
    return _RNG.uniform(min_val, max_val)


def sample_noise(amplitude: float, dist: str = "gaussian") -> float:
    """Sample PID noise from the specified distribution."""
    if dist == "gaussian":
        return _RNG.gauss(0, amplitude / 2)
    return _RNG.uniform(-amplitude, amplitude)


CFG = AppConfig()
CFG.load()

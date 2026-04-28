"""
config.py — 所有可调参数的单一来源
规则：此文件绝不 import cv2 / numpy。调用方按需构造 np.array。

设计决策：所有需要从 GUI 动态修改的配置类不使用 frozen=True。
frozen=True 会导致 setattr 抛出 FrozenInstanceError，
这与 DearPyGui 滑块回调中的 setattr(CFG.pid, 'kp', val) 直接冲突。
"""
import json
import os
from dataclasses import dataclass, field, asdict
from typing import Tuple


# ---------------------------------------------------------------------------
# 颜色范围（HSV）：Tuple[H_min, S_min, V_min], Tuple[H_max, S_max, V_max]
# ---------------------------------------------------------------------------
@dataclass
class HsvRange:
    lower: Tuple[int, int, int]
    upper: Tuple[int, int, int]


@dataclass
class HsvConfig:
    # 按钮高亮蓝（咬钩提示）
    blue:      HsvRange = field(
        default_factory=lambda: HsvRange((100, 140, 140), (130, 255, 255)))
    # 进度条安全区（青绿色）
    safe_zone: HsvRange = field(
        default_factory=lambda: HsvRange((75, 100, 100), (100, 255, 255)))
    # 游标线（黄色）
    cursor:    HsvRange = field(
        default_factory=lambda: HsvRange((18,  80, 160), (40, 255, 255)))


# ---------------------------------------------------------------------------
# PID 参数（可变，GUI 滑块直接修改）
# ---------------------------------------------------------------------------
@dataclass
class PidConfig:
    kp: float = 0.45
    ki: float = 0.05
    kd: float = 0.0
    integral_limit: float = 150.0
    deadband: float = 5.0
    adaptive: bool = True


# ---------------------------------------------------------------------------
# ROI（mss 格式，默认基准：1920×1080）
# ---------------------------------------------------------------------------
@dataclass
class RoiConfig:
    button: dict = field(default_factory=lambda: {
        "top": 1760, "left": 3400, "width": 440, "height": 360
    })
    bar: dict = field(default_factory=lambda: {
        "top": 118, "left": 1209, "width": 1441, "height": 64
    })
    ignore_margin_ratio: float = 0.02


# ---------------------------------------------------------------------------
# 时序与阈值参数（可变，GUI 可调）
# ---------------------------------------------------------------------------
@dataclass
class TimingConfig:
    cast_animation_secs: float = 1.8
    bite_timeout_secs: float = 45.0
    lost_frames_threshold: int = 50
    result_wait_secs: float = 2.2
    key_press_duration: float = 0.05
    waiting_poll_interval: float = 0.05
    struggling_poll_interval: float = 0.01  # 防止 CPU 占用过高，并稳定 PID 采样率


# ---------------------------------------------------------------------------
# 多尺度模板匹配参数（不常改，但保持可变以保持一致性）
# ---------------------------------------------------------------------------
@dataclass
class CalibrationConfig:
    scale_min:  float = 0.5
    scale_max:  float = 2.0
    scale_steps: int = 30
    confidence_threshold: float = 0.72
    roi_padding: int = 25


# ---------------------------------------------------------------------------
# 按键绑定
# ---------------------------------------------------------------------------
@dataclass
class KeyConfig:
    cast: str = 'f'
    left: str = 'a'
    right: str = 'd'
    exit: str = 'esc'


@dataclass
class HotkeyConfig:
    toggle: str = 'f8'
    stop:   str = 'f12'


# ---------------------------------------------------------------------------
# 顶层配置对象（全局单例）
# ---------------------------------------------------------------------------
@dataclass
class AppConfig:
    hsv:         HsvConfig = field(default_factory=HsvConfig)
    pid:         PidConfig = field(default_factory=PidConfig)
    roi:         RoiConfig = field(default_factory=RoiConfig)
    timing:      TimingConfig = field(default_factory=TimingConfig)
    calibration: CalibrationConfig = field(default_factory=CalibrationConfig)
    keys:        KeyConfig = field(default_factory=KeyConfig)
    hotkeys:     HotkeyConfig = field(default_factory=HotkeyConfig)
    min_blue_pixels: int = 300
    result_close_method: str = 'click'
    debug_mode: bool = False
    always_on_top: bool = False

    def save(self, path="settings.json"):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=4)

    def load(self, path="settings.json"):
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            def update_obj(obj, d):
                for k, v in d.items():
                    if hasattr(obj, k):
                        attr = getattr(obj, k)
                        if isinstance(v, dict) and hasattr(attr, '__dataclass_fields__'):
                            update_obj(attr, v)
                        elif isinstance(v, list):
                            setattr(obj, k, tuple(v))
                        else:
                            setattr(obj, k, v)
            update_obj(self, data)
        except Exception as e:
            print(f"Failed to load settings: {e}")

CFG = AppConfig()
CFG.load()

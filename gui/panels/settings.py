from typing import Callable

import dearpygui.dearpygui as dpg

from config import CFG
from gui.bridge import BotBridge


_ACCENT = (112, 214, 186)
_MUTED = (140, 148, 157)
_RESULT_METHODS = {
    "Click center": "click",
    "Press exit key": "key",
}


def create_settings(
    bridge: BotBridge,
    on_hotkeys_changed: Callable[[], None] | None = None,
):
    with dpg.group():
        with dpg.group(horizontal=True):
            dpg.add_text("Settings", color=_ACCENT)
            dpg.add_spacer(width=18)
            dpg.add_button(label="Save", callback=lambda: _save(bridge), height=28)
            dpg.add_button(
                label="Reset",
                callback=lambda: _on_reset(bridge, on_hotkeys_changed),
                height=28,
            )
        dpg.add_separator()
        dpg.add_spacer(height=4)

        with dpg.collapsing_header(label="PID Tuning", default_open=True):
            with dpg.group(indent=18):
                dpg.add_slider_float(
                    label="Kp",
                    min_value=0.0,
                    max_value=2.0,
                    format="%.3f",
                    width=360,
                    tag="cfg_pid_kp",
                    default_value=CFG.pid.kp,
                    callback=lambda s, d: _set(CFG.pid, "kp", d),
                )
                dpg.add_slider_float(
                    label="Ki",
                    min_value=0.0,
                    max_value=0.5,
                    format="%.3f",
                    width=360,
                    tag="cfg_pid_ki",
                    default_value=CFG.pid.ki,
                    callback=lambda s, d: _set(CFG.pid, "ki", d),
                )
                dpg.add_slider_float(
                    label="Kd",
                    min_value=0.0,
                    max_value=1.0,
                    format="%.3f",
                    width=360,
                    tag="cfg_pid_kd",
                    default_value=CFG.pid.kd,
                    callback=lambda s, d: _set(CFG.pid, "kd", d),
                )
                dpg.add_slider_float(
                    label="Deadband",
                    min_value=0.0,
                    max_value=50.0,
                    format="%.1f",
                    width=360,
                    tag="cfg_pid_deadband",
                    default_value=CFG.pid.deadband,
                    callback=lambda s, d: _set(CFG.pid, "deadband", d),
                )
                dpg.add_slider_float(
                    label="Integral limit",
                    min_value=10.0,
                    max_value=500.0,
                    format="%.0f",
                    width=360,
                    tag="cfg_pid_integral_limit",
                    default_value=CFG.pid.integral_limit,
                    callback=lambda s, d: _set(CFG.pid, "integral_limit", d),
                )
                dpg.add_checkbox(
                    label="Adaptive damping",
                    tag="cfg_pid_adaptive",
                    default_value=CFG.pid.adaptive,
                    callback=lambda s, d: _set(CFG.pid, "adaptive", d),
                )

        with dpg.collapsing_header(label="Vision"):
            with dpg.group(indent=18):
                with dpg.tree_node(label="Safe zone HSV", default_open=True):
                    _hsv_inputs("cfg_hsv_sz", CFG.hsv.safe_zone)
                with dpg.tree_node(label="Cursor HSV", default_open=True):
                    _hsv_inputs("cfg_hsv_cur", CFG.hsv.cursor)
                with dpg.tree_node(label="Bite trigger HSV", default_open=False):
                    _hsv_inputs("cfg_hsv_bl", CFG.hsv.blue)

                dpg.add_spacer(height=4)
                dpg.add_slider_float(
                    label="Edge ignore ratio",
                    min_value=0.0,
                    max_value=0.12,
                    format="%.3f",
                    width=360,
                    tag="cfg_roi_ignore_margin",
                    default_value=CFG.roi.ignore_margin_ratio,
                    callback=lambda s, d: _set(CFG.roi, "ignore_margin_ratio", d),
                )
                dpg.add_input_int(
                    label="Blue pixel trigger",
                    width=160,
                    tag="cfg_min_blue",
                    default_value=CFG.min_blue_pixels,
                    callback=lambda s, d: _set_int(
                        CFG, "min_blue_pixels", d, "cfg_min_blue", 1
                    ),
                )

        with dpg.collapsing_header(label="Timing"):
            with dpg.group(indent=18):
                dpg.add_slider_float(
                    label="Cast animation (s)",
                    min_value=0.5,
                    max_value=5.0,
                    format="%.2f",
                    width=360,
                    tag="cfg_timing_cast",
                    default_value=CFG.timing.cast_animation_secs,
                    callback=lambda s, d: _set(CFG.timing, "cast_animation_secs", d),
                )
                dpg.add_slider_float(
                    label="Bite timeout (s)",
                    min_value=10.0,
                    max_value=120.0,
                    format="%.1f",
                    width=360,
                    tag="cfg_timing_bite",
                    default_value=CFG.timing.bite_timeout_secs,
                    callback=lambda s, d: _set(CFG.timing, "bite_timeout_secs", d),
                )
                dpg.add_input_int(
                    label="Lost frame limit",
                    width=160,
                    tag="cfg_timing_lost",
                    default_value=CFG.timing.lost_frames_threshold,
                    callback=lambda s, d: _set_int(
                        CFG.timing,
                        "lost_frames_threshold",
                        d,
                        "cfg_timing_lost",
                        1,
                    ),
                )
                dpg.add_slider_float(
                    label="Result wait (s)",
                    min_value=0.5,
                    max_value=5.0,
                    format="%.2f",
                    width=360,
                    tag="cfg_timing_result",
                    default_value=CFG.timing.result_wait_secs,
                    callback=lambda s, d: _set(CFG.timing, "result_wait_secs", d),
                )
                dpg.add_slider_float(
                    label="Waiting poll (s)",
                    min_value=0.02,
                    max_value=0.20,
                    format="%.3f",
                    width=360,
                    tag="cfg_timing_wait_poll",
                    default_value=CFG.timing.waiting_poll_interval,
                    callback=lambda s, d: _set(CFG.timing, "waiting_poll_interval", d),
                )
                dpg.add_slider_float(
                    label="Tracking poll (s)",
                    min_value=0.005,
                    max_value=0.050,
                    format="%.3f",
                    width=360,
                    tag="cfg_timing_track_poll",
                    default_value=CFG.timing.struggling_poll_interval,
                    callback=lambda s, d: _set(
                        CFG.timing, "struggling_poll_interval", d
                    ),
                )

        with dpg.collapsing_header(label="Input"):
            with dpg.group(indent=18):
                _key_input("Cast key", "cfg_key_cast", CFG.keys.cast, "cast")
                _key_input("Move left", "cfg_key_left", CFG.keys.left, "left")
                _key_input("Move right", "cfg_key_right", CFG.keys.right, "right")
                _key_input("Exit key", "cfg_key_exit", CFG.keys.exit, "exit")
                dpg.add_combo(
                    label="Result close",
                    items=list(_RESULT_METHODS.keys()),
                    default_value=_result_method_label(CFG.result_close_method),
                    width=180,
                    tag="cfg_result_close_method",
                    callback=lambda s, d: _set(
                        CFG, "result_close_method", _RESULT_METHODS[d]
                    ),
                )
                dpg.add_checkbox(
                    label="Always on top",
                    tag="cfg_always_on_top",
                    default_value=CFG.always_on_top,
                    callback=lambda s, d: _on_top_changed(d),
                )
                dpg.add_checkbox(
                    label="Debug logging",
                    tag="cfg_debug_mode",
                    default_value=CFG.debug_mode,
                    callback=lambda s, d: _set(CFG, "debug_mode", d),
                )

        with dpg.collapsing_header(label="Calibration"):
            with dpg.group(indent=18):
                dpg.add_slider_float(
                    label="Scale min",
                    min_value=0.2,
                    max_value=1.5,
                    format="%.2f",
                    width=360,
                    tag="cfg_cal_scale_min",
                    default_value=CFG.calibration.scale_min,
                    callback=lambda s, d: _set(CFG.calibration, "scale_min", d),
                )
                dpg.add_slider_float(
                    label="Scale max",
                    min_value=1.0,
                    max_value=3.0,
                    format="%.2f",
                    width=360,
                    tag="cfg_cal_scale_max",
                    default_value=CFG.calibration.scale_max,
                    callback=lambda s, d: _set(CFG.calibration, "scale_max", d),
                )
                dpg.add_input_int(
                    label="Scale steps",
                    width=160,
                    tag="cfg_cal_scale_steps",
                    default_value=CFG.calibration.scale_steps,
                    callback=lambda s, d: _set_int(
                        CFG.calibration, "scale_steps", d, "cfg_cal_scale_steps", 1
                    ),
                )
                dpg.add_slider_float(
                    label="Confidence",
                    min_value=0.3,
                    max_value=0.95,
                    format="%.2f",
                    width=360,
                    tag="cfg_cal_confidence",
                    default_value=CFG.calibration.confidence_threshold,
                    callback=lambda s, d: _set(
                        CFG.calibration, "confidence_threshold", d
                    ),
                )
                dpg.add_input_int(
                    label="ROI padding",
                    width=160,
                    tag="cfg_cal_roi_padding",
                    default_value=CFG.calibration.roi_padding,
                    callback=lambda s, d: _set_int(
                        CFG.calibration, "roi_padding", d, "cfg_cal_roi_padding", 0
                    ),
                )

        with dpg.collapsing_header(label="Global Hotkeys"):
            with dpg.group(indent=18):
                dpg.add_input_text(
                    label="Toggle",
                    tag="cfg_hotkey_toggle",
                    width=220,
                    default_value=CFG.hotkeys.toggle,
                    on_enter=True,
                    callback=lambda s, d: _set_hotkey(
                        "toggle", d, bridge, on_hotkeys_changed
                    ),
                )
                dpg.add_input_text(
                    label="Stop",
                    tag="cfg_hotkey_stop",
                    width=220,
                    default_value=CFG.hotkeys.stop,
                    on_enter=True,
                    callback=lambda s, d: _set_hotkey(
                        "stop", d, bridge, on_hotkeys_changed
                    ),
                )


def _hsv_inputs(prefix: str, hsv_range):
    dpg.add_slider_intx(
        label="Min",
        size=3,
        min_value=0,
        max_value=255,
        width=360,
        tag=f"{prefix}_lower",
        default_value=list(hsv_range.lower),
        callback=lambda s, d: _set(hsv_range, "lower", tuple(d[:3])),
    )
    dpg.add_slider_intx(
        label="Max",
        size=3,
        min_value=0,
        max_value=255,
        width=360,
        tag=f"{prefix}_upper",
        default_value=list(hsv_range.upper),
        callback=lambda s, d: _set(hsv_range, "upper", tuple(d[:3])),
    )


def _key_input(label: str, tag: str, default: str, attr: str):
    dpg.add_input_text(
        label=label,
        tag=tag,
        width=160,
        default_value=default,
        on_enter=True,
        callback=lambda s, d: _set_key(attr, d, tag),
    )


def _save(bridge: BotBridge):
    CFG.save()
    bridge.push_log("Settings saved.")


def _on_reset(
    bridge: BotBridge,
    on_hotkeys_changed: Callable[[], None] | None = None,
):
    CFG.reset()
    _refresh_values()
    if on_hotkeys_changed:
        on_hotkeys_changed()
    bridge.push_log("Settings reset to defaults.")


def _refresh_values():
    dpg.set_value("cfg_pid_kp", CFG.pid.kp)
    dpg.set_value("cfg_pid_ki", CFG.pid.ki)
    dpg.set_value("cfg_pid_kd", CFG.pid.kd)
    dpg.set_value("cfg_pid_deadband", CFG.pid.deadband)
    dpg.set_value("cfg_pid_integral_limit", CFG.pid.integral_limit)
    dpg.set_value("cfg_pid_adaptive", CFG.pid.adaptive)

    dpg.set_value("cfg_hsv_sz_lower", list(CFG.hsv.safe_zone.lower))
    dpg.set_value("cfg_hsv_sz_upper", list(CFG.hsv.safe_zone.upper))
    dpg.set_value("cfg_hsv_cur_lower", list(CFG.hsv.cursor.lower))
    dpg.set_value("cfg_hsv_cur_upper", list(CFG.hsv.cursor.upper))
    dpg.set_value("cfg_hsv_bl_lower", list(CFG.hsv.blue.lower))
    dpg.set_value("cfg_hsv_bl_upper", list(CFG.hsv.blue.upper))
    dpg.set_value("cfg_roi_ignore_margin", CFG.roi.ignore_margin_ratio)
    dpg.set_value("cfg_min_blue", CFG.min_blue_pixels)

    dpg.set_value("cfg_timing_cast", CFG.timing.cast_animation_secs)
    dpg.set_value("cfg_timing_bite", CFG.timing.bite_timeout_secs)
    dpg.set_value("cfg_timing_lost", CFG.timing.lost_frames_threshold)
    dpg.set_value("cfg_timing_result", CFG.timing.result_wait_secs)
    dpg.set_value("cfg_timing_wait_poll", CFG.timing.waiting_poll_interval)
    dpg.set_value("cfg_timing_track_poll", CFG.timing.struggling_poll_interval)

    dpg.set_value("cfg_key_cast", CFG.keys.cast)
    dpg.set_value("cfg_key_left", CFG.keys.left)
    dpg.set_value("cfg_key_right", CFG.keys.right)
    dpg.set_value("cfg_key_exit", CFG.keys.exit)
    dpg.set_value("cfg_result_close_method", _result_method_label(CFG.result_close_method))
    dpg.set_value("cfg_always_on_top", CFG.always_on_top)
    dpg.set_value("cfg_debug_mode", CFG.debug_mode)
    dpg.set_viewport_always_on_top(CFG.always_on_top)

    dpg.set_value("cfg_cal_scale_min", CFG.calibration.scale_min)
    dpg.set_value("cfg_cal_scale_max", CFG.calibration.scale_max)
    dpg.set_value("cfg_cal_scale_steps", CFG.calibration.scale_steps)
    dpg.set_value("cfg_cal_confidence", CFG.calibration.confidence_threshold)
    dpg.set_value("cfg_cal_roi_padding", CFG.calibration.roi_padding)

    dpg.set_value("cfg_hotkey_toggle", CFG.hotkeys.toggle)
    dpg.set_value("cfg_hotkey_stop", CFG.hotkeys.stop)


def _on_top_changed(val):
    CFG.always_on_top = val
    dpg.set_viewport_always_on_top(val)


def _set(obj, attr: str, val):
    setattr(obj, attr, val)


def _set_int(obj, attr: str, val, tag: str, minimum: int):
    next_value = max(minimum, int(val))
    setattr(obj, attr, next_value)
    if next_value != val:
        dpg.set_value(tag, next_value)


def _set_key(attr: str, val: str, tag: str):
    normalized = val.strip().lower()
    if normalized:
        setattr(CFG.keys, attr, normalized)
    else:
        dpg.set_value(tag, getattr(CFG.keys, attr))


def _set_hotkey(
    attr: str,
    val: str,
    bridge: BotBridge,
    on_hotkeys_changed: Callable[[], None] | None,
):
    normalized = val.strip().lower()
    setattr(CFG.hotkeys, attr, normalized)
    if on_hotkeys_changed:
        on_hotkeys_changed()
    bridge.push_log(f"Hotkey updated: {attr}={normalized or 'disabled'}")


def _result_method_label(value: str) -> str:
    for label, method in _RESULT_METHODS.items():
        if method == value:
            return label
    return "Click center"

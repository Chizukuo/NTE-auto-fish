"""Settings page — two-column category navigation with config panels."""
from __future__ import annotations

from typing import Callable

import dearpygui.dearpygui as dpg

from config import CFG
from gui.bridge import BotBridge
from gui.components import (
    apply_glass_card_theme,
    caption_text,
    hsv_editor,
    metric_row,
    section_header,
    styled_button,
    update_hsv_preview,
)
from gui.theme import (
    ACCENT,
    ACCENT_BLUE,
    BORDER_SUBTLE,
    CARD_GAP,
    GLASS_HIGHLIGHT,
    GLASS_HIGHLIGHT2,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_VERY_MUTED,
    build_settings_cat_theme,
)

# ---------------------------------------------------------------------------
# Category definitions
# ---------------------------------------------------------------------------

CATEGORIES = [
    ("pid",         "PID Tuning"),
    ("vision",      "Vision & Detection"),
    ("timing",      "Timing"),
    ("input",       "Input & Hotkeys"),
    ("calibration", "Calibration"),
]

_RESULT_METHODS = {
    "Click center": "click",
    "Press exit key": "key",
}

_TOOLTIPS = {
    "Kp": "Proportional gain. Higher = stronger correction for large errors.",
    "Ki": "Integral gain. Eliminates steady-state offset over time.",
    "Kd": "Derivative gain. Dampens oscillation from rapid changes.",
    "Deadband": "Error range (pixels) where no correction is applied. Prevents jitter.",
    "Integral limit": "Clamps the integral term to prevent windup.",
    "Adaptive damping": "Automatically reduces Kp when oscillation is detected.",
    "Edge ignore ratio": "Fraction of bar edges to ignore when detecting cursor/target.",
    "Blue pixel trigger": "Minimum blue pixels in button ROI to detect a fish bite.",
    "Cast animation (s)": "Wait time after pressing cast key before checking for bite.",
    "Bite timeout (s)": "Max seconds to wait for a bite before recasting.",
    "Lost frame limit": "Frames of lost tracking before ending the struggle phase.",
    "Result wait (s)": "Wait time after fish caught before closing the result dialog.",
    "Waiting poll (s)": "Interval between bite-detection checks.",
    "Tracking poll (s)": "Interval between cursor/target position updates.",
    "Toggle": "Hotkey to pause/resume the bot (e.g. f8).",
    "Stop": "Hotkey to stop the bot (e.g. f12).",
}

# ---------------------------------------------------------------------------
# Module state
# ---------------------------------------------------------------------------

_active_category: str = "pid"
_settings_built: bool = False
_cat_tags: dict[str, dict] = {}  # {key: {"btn": tag, "indicator": tag, "group": tag}}

# Cached themes
_cat_active_theme: int | None = None
_cat_inactive_theme: int | None = None


def _ensure_themes():
    global _cat_active_theme, _cat_inactive_theme
    if _cat_active_theme is None:
        _cat_active_theme = build_settings_cat_theme(active=True)
        _cat_inactive_theme = build_settings_cat_theme(active=False)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def create_settings(
    bridge: BotBridge,
    on_hotkeys_changed: Callable[[], None] | None = None,
):
    _ensure_themes()

    with dpg.group(horizontal=True):
        # ── Left column: category list ──────────────────────────────────
        with dpg.child_window(
            width=200, height=-1, tag="settings_cat_list",
            border=True, no_scrollbar=True,
        ):
            apply_glass_card_theme("settings_cat_list")
            dpg.add_spacer(height=8)
            section_header("Categories", color=TEXT_MUTED)

            for key, label in CATEGORIES:
                _create_category_item(key, label)

        dpg.add_spacer(width=CARD_GAP)

        # ── Right column: settings content ──────────────────────────────
        with dpg.child_window(
            width=-1, height=-1, tag="settings_content",
            border=True, no_scrollbar=False,
        ):
            apply_glass_card_theme("settings_content")

            _build_pid_settings()
            _build_vision_settings()
            _build_timing_settings()
            _build_input_settings(bridge, on_hotkeys_changed)
            _build_calibration_settings()

            dpg.add_spacer(height=20)

            # Save / Reset buttons
            with dpg.group(horizontal=True):
                styled_button(
                    "Save Settings", "btn_save",
                    callback=lambda: _save(bridge),
                    variant="primary", width=140, height=32,
                )
                dpg.add_spacer(width=12)
                styled_button(
                    "Reset to Defaults", "btn_reset",
                    callback=lambda: _on_reset(bridge, on_hotkeys_changed),
                    variant="neutral", width=160, height=32,
                )

    # Show only the active category
    _switch_category(_active_category)


# ---------------------------------------------------------------------------
# Category navigation
# ---------------------------------------------------------------------------


def _create_category_item(key: str, label: str):
    is_active = (key == _active_category)
    btn_tag = f"cat_btn_{key}"
    ind_tag = f"cat_ind_{key}"

    with dpg.group(horizontal=True):
        with dpg.drawlist(width=4, height=32, tag=f"cat_ind_dl_{key}"):
            if is_active:
                dpg.draw_rectangle(
                    (0, 0), (4, 32), color=ACCENT, fill=ACCENT, tag=ind_tag,
                )
            else:
                dpg.draw_rectangle(
                    (0, 0), (4, 32), color=(0, 0, 0, 0), fill=(0, 0, 0, 0), tag=ind_tag,
                )

        dpg.add_button(
            label=f"  {label}",
            tag=btn_tag,
            width=168,
            height=32,
            callback=lambda: _switch_category(key),
        )
        dpg.bind_item_theme(btn_tag, _cat_active_theme if is_active else _cat_inactive_theme)

    _cat_tags[key] = {"btn": btn_tag, "indicator": ind_tag}


def _switch_category(key: str):
    global _active_category, _settings_built
    if key == _active_category and _settings_built:
        return

    # Hide all groups, deactivate all items
    for cat_key, _ in CATEGORIES:
        group_tag = f"settings_group_{cat_key}"
        if dpg.does_item_exist(group_tag):
            dpg.configure_item(group_tag, show=(cat_key == key))

        if cat_key in _cat_tags:
            tags = _cat_tags[cat_key]
            is_active = (cat_key == key)
            dpg.bind_item_theme(tags["btn"], _cat_active_theme if is_active else _cat_inactive_theme)
            dpg.configure_item(
                tags["indicator"],
                color=ACCENT if is_active else (0, 0, 0, 0),
                fill=ACCENT if is_active else (0, 0, 0, 0),
            )

    _active_category = key
    _settings_built = True


# ---------------------------------------------------------------------------
# Settings panels
# ---------------------------------------------------------------------------


def _build_pid_settings():
    with dpg.group(tag="settings_group_pid"):
        section_header("PID Tuning", color=ACCENT)
        caption_text("Proportional-Integral-Derivative controller for fish bar tracking.")
        dpg.add_spacer(height=8)

        _slider_with_tooltip(
            "Kp", tag="cfg_pid_kp", min_val=0.0, max_val=2.0, fmt="%.3f",
            default=CFG.pid.kp, cb=lambda s, d: _set(CFG.pid, "kp", d),
        )
        _slider_with_tooltip(
            "Ki", tag="cfg_pid_ki", min_val=0.0, max_val=0.5, fmt="%.3f",
            default=CFG.pid.ki, cb=lambda s, d: _set(CFG.pid, "ki", d),
        )
        _slider_with_tooltip(
            "Kd", tag="cfg_pid_kd", min_val=0.0, max_val=1.0, fmt="%.3f",
            default=CFG.pid.kd, cb=lambda s, d: _set(CFG.pid, "kd", d),
        )
        _slider_with_tooltip(
            "Deadband", tag="cfg_pid_deadband", min_val=0.0, max_val=20.0, fmt="%.1f",
            default=CFG.pid.deadband, cb=lambda s, d: _set(CFG.pid, "deadband", d),
        )
        _slider_with_tooltip(
            "Integral limit", tag="cfg_pid_integral_limit", min_val=10.0, max_val=500.0, fmt="%.0f",
            default=CFG.pid.integral_limit, cb=lambda s, d: _set(CFG.pid, "integral_limit", d),
        )
        _checkbox_with_tooltip(
            "Adaptive damping", tag="cfg_pid_adaptive",
            default=CFG.pid.adaptive, cb=lambda s, d: _set(CFG.pid, "adaptive", d),
        )


def _build_vision_settings():
    with dpg.group(tag="settings_group_vision"):
        section_header("Vision & Detection", color=ACCENT)
        caption_text("HSV color ranges for detecting game elements on screen.")
        dpg.add_spacer(height=8)

        hsv_editor("cfg_hsv_sz", CFG.hsv.safe_zone, label="Safe Zone HSV", default_open=True)
        hsv_editor("cfg_hsv_cur", CFG.hsv.cursor, label="Cursor HSV", default_open=True)
        hsv_editor("cfg_hsv_bl", CFG.hsv.blue, label="Bite Trigger HSV", default_open=False)

        dpg.add_spacer(height=4)
        _slider_with_tooltip(
            "Edge ignore ratio", tag="cfg_roi_ignore_margin",
            min_val=0.0, max_val=0.12, fmt="%.3f",
            default=CFG.roi.ignore_margin_ratio,
            cb=lambda s, d: _set(CFG.roi, "ignore_margin_ratio", d),
        )
        _input_with_tooltip(
            "Blue pixel trigger", tag="cfg_min_blue", width=140,
            default=CFG.min_blue_pixels,
            cb=lambda s, d: _set_int(CFG, "min_blue_pixels", d, "cfg_min_blue", 1),
        )


def _build_timing_settings():
    with dpg.group(tag="settings_group_timing"):
        section_header("Timing", color=ACCENT)
        caption_text("Timing parameters for the fishing state machine.")
        dpg.add_spacer(height=8)

        _slider_with_tooltip(
            "Cast animation (s)", tag="cfg_timing_cast",
            min_val=0.5, max_val=5.0, fmt="%.2f",
            default=CFG.timing.cast_animation_secs,
            cb=lambda s, d: _set(CFG.timing, "cast_animation_secs", d),
        )
        _slider_with_tooltip(
            "Bite timeout (s)", tag="cfg_timing_bite",
            min_val=10.0, max_val=120.0, fmt="%.1f",
            default=CFG.timing.bite_timeout_secs,
            cb=lambda s, d: _set(CFG.timing, "bite_timeout_secs", d),
        )
        _input_with_tooltip(
            "Lost frame limit", tag="cfg_timing_lost", width=140,
            default=CFG.timing.lost_frames_threshold,
            cb=lambda s, d: _set_int(
                CFG.timing, "lost_frames_threshold", d, "cfg_timing_lost", 1,
            ),
        )
        _slider_with_tooltip(
            "Result wait (s)", tag="cfg_timing_result",
            min_val=0.5, max_val=5.0, fmt="%.2f",
            default=CFG.timing.result_wait_secs,
            cb=lambda s, d: _set(CFG.timing, "result_wait_secs", d),
        )
        _slider_with_tooltip(
            "Waiting poll (s)", tag="cfg_timing_wait_poll",
            min_val=0.02, max_val=0.20, fmt="%.3f",
            default=CFG.timing.waiting_poll_interval,
            cb=lambda s, d: _set(CFG.timing, "waiting_poll_interval", d),
        )
        _slider_with_tooltip(
            "Tracking poll (s)", tag="cfg_timing_track_poll",
            min_val=0.005, max_val=0.050, fmt="%.3f",
            default=CFG.timing.struggling_poll_interval,
            cb=lambda s, d: _set(CFG.timing, "struggling_poll_interval", d),
        )


def _build_input_settings(
    bridge: BotBridge,
    on_hotkeys_changed: Callable[[], None] | None = None,
):
    with dpg.group(tag="settings_group_input"):
        section_header("Input & Hotkeys", color=ACCENT)
        caption_text("Key bindings for in-game actions and global hotkeys.")
        dpg.add_spacer(height=8)

        dpg.add_text("Key Bindings", color=TEXT_MUTED)
        dpg.add_spacer(height=4)
        _key_input("Cast key", "cfg_key_cast", CFG.keys.cast, "cast")
        _key_input("Move left", "cfg_key_left", CFG.keys.left, "left")
        _key_input("Move right", "cfg_key_right", CFG.keys.right, "right")
        _key_input("Exit key", "cfg_key_exit", CFG.keys.exit, "exit")

        dpg.add_combo(
            label="Result close", items=list(_RESULT_METHODS.keys()),
            default_value=_result_method_label(CFG.result_close_method),
            width=160, tag="cfg_result_close_method",
            callback=lambda s, d: _set(CFG, "result_close_method", _RESULT_METHODS[d]),
        )
        dpg.add_checkbox(
            label="Always on top", tag="cfg_always_on_top",
            default_value=CFG.always_on_top,
            callback=lambda s, d: _on_top_changed(d),
        )
        dpg.add_checkbox(
            label="Debug logging", tag="cfg_debug_mode",
            default_value=CFG.debug_mode,
            callback=lambda s, d: _set(CFG, "debug_mode", d),
        )

        dpg.add_spacer(height=12)
        dpg.add_text("Global Hotkeys", color=TEXT_MUTED)
        dpg.add_spacer(height=4)
        _text_input_with_tooltip(
            "Toggle", tag="cfg_hotkey_toggle", width=200,
            default=CFG.hotkeys.toggle,
            cb=lambda s, d: _set_hotkey("toggle", d, bridge, on_hotkeys_changed),
        )
        _text_input_with_tooltip(
            "Stop", tag="cfg_hotkey_stop", width=200,
            default=CFG.hotkeys.stop,
            cb=lambda s, d: _set_hotkey("stop", d, bridge, on_hotkeys_changed),
        )


def _build_calibration_settings():
    with dpg.group(tag="settings_group_calibration"):
        section_header("Calibration", color=ACCENT)
        caption_text("Template matching parameters for automatic ROI detection.")
        dpg.add_spacer(height=8)

        _slider_with_tooltip(
            "Scale min", tag="cfg_cal_scale_min",
            min_val=0.2, max_val=1.5, fmt="%.2f",
            default=CFG.calibration.scale_min,
            cb=lambda s, d: _set(CFG.calibration, "scale_min", d),
        )
        _slider_with_tooltip(
            "Scale max", tag="cfg_cal_scale_max",
            min_val=1.0, max_val=3.0, fmt="%.2f",
            default=CFG.calibration.scale_max,
            cb=lambda s, d: _set(CFG.calibration, "scale_max", d),
        )
        _input_with_tooltip(
            "Scale steps", tag="cfg_cal_scale_steps", width=140,
            default=CFG.calibration.scale_steps,
            cb=lambda s, d: _set_int(
                CFG.calibration, "scale_steps", d, "cfg_cal_scale_steps", 1,
            ),
        )
        _slider_with_tooltip(
            "Confidence", tag="cfg_cal_confidence",
            min_val=0.3, max_val=0.95, fmt="%.2f",
            default=CFG.calibration.confidence_threshold,
            cb=lambda s, d: _set(CFG.calibration, "confidence_threshold", d),
        )
        _input_with_tooltip(
            "ROI padding", tag="cfg_cal_roi_padding", width=140,
            default=CFG.calibration.roi_padding,
            cb=lambda s, d: _set_int(
                CFG.calibration, "roi_padding", d, "cfg_cal_roi_padding", 0,
            ),
        )


# ---------------------------------------------------------------------------
# Helper widgets
# ---------------------------------------------------------------------------


def _slider_with_tooltip(
    label: str, tag: str, min_val: float, max_val: float,
    fmt: str, default: float, cb: Callable,
):
    dpg.add_slider_float(
        label=label, tag=tag, min_value=min_val, max_value=max_val,
        format=fmt, width=-1, default_value=default, callback=cb,
    )
    _add_tooltip(tag, label)
    tip = _TOOLTIPS.get(label)
    if tip:
        caption_text(tip)
        dpg.add_spacer(height=4)


def _checkbox_with_tooltip(label: str, tag: str, default: bool, cb: Callable):
    dpg.add_checkbox(label=label, tag=tag, default_value=default, callback=cb)
    _add_tooltip(tag, label)
    tip = _TOOLTIPS.get(label)
    if tip:
        caption_text(tip)
        dpg.add_spacer(height=4)


def _input_with_tooltip(
    label: str, tag: str, width: int, default, cb: Callable,
):
    dpg.add_input_int(label=label, tag=tag, width=width, default_value=default, callback=cb)
    _add_tooltip(tag, label)
    tip = _TOOLTIPS.get(label)
    if tip:
        caption_text(tip)
        dpg.add_spacer(height=4)


def _text_input_with_tooltip(
    label: str, tag: str, width: int, default: str, cb: Callable,
):
    dpg.add_input_text(
        label=label, tag=tag, width=width,
        default_value=default, on_enter=True, callback=cb,
    )
    _add_tooltip(tag, label)
    tip = _TOOLTIPS.get(label)
    if tip:
        caption_text(tip)
        dpg.add_spacer(height=4)


def _add_tooltip(tag: str, label: str):
    tip = _TOOLTIPS.get(label)
    if not tip:
        return
    with dpg.tooltip(tag):
        dpg.add_text(tip, color=(200, 200, 210))


def _key_input(label: str, tag: str, default: str, attr: str):
    dpg.add_input_text(
        label=label, tag=tag, width=140,
        default_value=default, on_enter=True,
        callback=lambda s, d: _set_key(attr, d, tag),
    )


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------


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
    update_hsv_preview("cfg_hsv_sz", CFG.hsv.safe_zone)
    update_hsv_preview("cfg_hsv_cur", CFG.hsv.cursor)
    update_hsv_preview("cfg_hsv_bl", CFG.hsv.blue)
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

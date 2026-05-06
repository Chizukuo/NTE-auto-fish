"""Dashboard page — status cards, controls, PID plot, telemetry, visual tracker."""
from __future__ import annotations

from collections import deque
from typing import Callable

import dearpygui.dearpygui as dpg

from gui.bridge import BotBridge, BotStatus
from gui.components import apply_glass_card_theme, metric_row, section_header, styled_button
from gui.theme import (
    ACCENT,
    ACCENT_BLUE,
    CARD_GAP,
    CARD_PADDING,
    SIDEBAR_WIDTH,
    STATE_RUNNING,
    STATE_RUNNING_HOVER,
    STATE_RUNNING_ACTIVE,
    STATE_PAUSED,
    STATE_PAUSED_HOVER,
    STATE_PAUSED_ACTIVE,
    STATE_STOPPED,
    STATE_STOPPED_HOVER,
    STATE_STOPPED_ACTIVE,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_VERY_MUTED,
    VIS_CURSOR,
    VIS_CURSOR_DOT,
    VIS_SAFE_ZONE,
    VIS_SAFE_ZONE_BD,
    VIS_TRACK,
    build_button_theme,
)
from modules.logic import FishingState

# ---------------------------------------------------------------------------
# Module state
# ---------------------------------------------------------------------------

_pid_history: deque[float] = deque([0.0] * 120, maxlen=120)
_vis_height = 72
_card_tags = ["state_card", "fish_card", "time_card", "fps_card"]
_cards_resized = False

# Cached themes
_theme_running: int | None = None
_theme_paused: int | None = None
_theme_stopped: int | None = None
_theme_start: int | None = None
_theme_pause: int | None = None
_theme_stop: int | None = None
_theme_calibrate: int | None = None


def _ensure_themes():
    global _theme_running, _theme_paused, _theme_stopped
    global _theme_start, _theme_pause, _theme_stop, _theme_calibrate
    if _theme_running is None:
        _theme_running = _state_button_theme(
            STATE_RUNNING, STATE_RUNNING_HOVER, STATE_RUNNING_ACTIVE,
        )
        _theme_paused = _state_button_theme(
            STATE_PAUSED, STATE_PAUSED_HOVER, STATE_PAUSED_ACTIVE,
        )
        _theme_stopped = _state_button_theme(
            STATE_STOPPED, STATE_STOPPED_HOVER, STATE_STOPPED_ACTIVE,
        )
        _theme_start = build_button_theme("primary")
        _theme_pause = build_button_theme("warning")
        _theme_stop = build_button_theme("danger")
        _theme_calibrate = build_button_theme("neutral")


def _state_button_theme(bg, hovered, active) -> int:
    with dpg.theme() as theme:
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, bg)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, hovered)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, active)
            dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255, 255))
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 6)
    return theme


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


def create_dashboard(
    bridge: BotBridge,
    on_start: Callable[[], None] | None = None,
    on_stop: Callable[[], None] | None = None,
    on_recalibrate: Callable[[], None] | None = None,
):
    global _cards_resized
    _ensure_themes()
    _cards_resized = False

    # ── Row 1: Status metric cards ──────────────────────────────────────
    # Initial width is a placeholder; update_dashboard_ui resizes on first frame.
    _init_w = 200
    with dpg.group(horizontal=True, tag="stat_cards_row"):
        _create_stat_card("state_card", "STATE", "Idle", width=_init_w)
        dpg.add_spacer(width=CARD_GAP)
        _create_stat_card("fish_card", "FISH CAUGHT", "0", width=_init_w)
        dpg.add_spacer(width=CARD_GAP)
        _create_stat_card("time_card", "SESSION TIME", "00:00:00", width=_init_w)
        dpg.add_spacer(width=CARD_GAP)
        _create_stat_card("fps_card", "FPS", "0.0", width=_init_w)

    dpg.add_spacer(height=CARD_GAP)

    # ── Row 2: Control bar ──────────────────────────────────────────────
    with dpg.child_window(
        height=72, tag="control_bar", border=True, no_scrollbar=True,
    ):
        apply_glass_card_theme("control_bar")
        with dpg.group(horizontal=True):
            styled_button(
                "Start", "btn_start_bot",
                callback=lambda s, a, u: _run_callback(on_start, bridge, "resume"),
                variant="primary", width=80, height=28,
            )
            dpg.add_spacer(width=8)
            styled_button(
                "Pause", "btn_pause_bot",
                callback=lambda s, a, u: bridge.send_cmd("pause"),
                variant="warning", width=80, height=28,
            )
            dpg.add_spacer(width=8)
            styled_button(
                "Stop", "btn_stop_bot",
                callback=lambda s, a, u: _run_callback(on_stop, bridge, "stop"),
                variant="danger", width=80, height=28,
            )
            dpg.add_spacer(width=8)
            styled_button(
                "Calibrate", "btn_recalibrate",
                callback=lambda s, a, u: _run_callback(on_recalibrate, bridge, "recalibrate"),
                variant="neutral", width=90, height=28,
            )
            dpg.add_spacer(width=24)
            dpg.add_text("Ready", tag="stat_status_message", color=TEXT_MUTED)

    dpg.add_spacer(height=CARD_GAP)

    # ── Row 3: PID plot + Telemetry + Vision tracker ────────────────────
    # Right column width; PID plot fills remaining space.
    _right_w = 380
    with dpg.group(horizontal=True):
        # Left: PID Plot
        with dpg.child_window(
            width=-(_right_w + CARD_GAP + 20), height=500,
            tag="pid_card", border=True, no_scrollbar=True,
        ):
            apply_glass_card_theme("pid_card")
            section_header("PID Output", color=ACCENT)
            with dpg.plot(
                no_title=True, no_menus=True, no_box_select=True,
                height=-1, width=-1, tag="pid_plot",
            ):
                dpg.add_plot_axis(dpg.mvXAxis, no_gridlines=True, no_tick_labels=True)
                with dpg.plot_axis(dpg.mvYAxis, tag="pid_y"):
                    dpg.add_line_series(
                        list(range(120)), list(_pid_history),
                        label="Output", tag="pid_series",
                    )
                dpg.set_axis_limits("pid_y", -110, 110)

        dpg.add_spacer(width=CARD_GAP)

        # Right column (transparent container)
        with dpg.child_window(
            width=_right_w, height=500,
            tag="right_col", border=False, no_scrollbar=True,
        ):
            # Telemetry card
            with dpg.child_window(
                height=320, tag="telemetry_card", border=True, no_scrollbar=True,
            ):
                apply_glass_card_theme("telemetry_card")
                section_header("Telemetry", color=ACCENT_BLUE)
                metric_row("Cursor X", "tele_cursor_x")
                metric_row("Target X", "tele_target_x")
                metric_row("PID output", "stat_pid_output", "0.000")
                metric_row("Lost frames", "stat_lost_frames", "0")
                metric_row("Cursor lost", "tele_lost_cursor")
                metric_row("Target lost", "tele_lost_target")
                metric_row("Button ROI", "tele_button_roi")
                metric_row("Bar ROI", "tele_bar_roi")

            dpg.add_spacer(height=CARD_GAP)

            # Vision tracker card
            with dpg.child_window(
                height=-1, tag="vision_card", border=True, no_scrollbar=True,
            ):
                apply_glass_card_theme("vision_card")
                section_header("Vision Tracker", color=ACCENT)
                _create_visualizer()


# ---------------------------------------------------------------------------
# Update (called every frame)
# ---------------------------------------------------------------------------


def update_dashboard_ui(bridge: BotBridge):
    global _cards_resized
    status = bridge.latest_status()

    # Resize stat cards to fill the row exactly once (or on viewport change).
    if not _cards_resized:
        _resize_stat_cards()
        _cards_resized = True

    # Stat cards
    dpg.set_value("state_card_value", _state_label(status.state))
    dpg.set_value("fish_card_value", str(status.fish_count))
    secs = int(status.session_secs)
    h, m, s = secs // 3600, (secs % 3600) // 60, secs % 3600 % 60
    dpg.set_value("time_card_value", f"{h:02d}:{m:02d}:{s:02d}")
    dpg.set_value("fps_card_value", f"{status.fps:.1f}")

    # Status message
    dpg.set_value("stat_status_message", _status_message(status))

    # Telemetry
    dpg.set_value("stat_pid_output", f"{status.pid_output:.3f}")
    dpg.set_value("stat_lost_frames", str(status.lost_frames))
    dpg.set_value("tele_cursor_x", _fmt_optional(status.cursor_x))
    dpg.set_value("tele_target_x", _fmt_optional(status.target_x))
    dpg.set_value("tele_lost_cursor", str(status.lost_cursor_frames))
    dpg.set_value("tele_lost_target", str(status.lost_target_frames))
    dpg.set_value("tele_button_roi", _fmt_roi(status.button_roi))
    dpg.set_value("tele_bar_roi", _fmt_roi(status.bar_roi))

    # Button states
    _set_enabled("btn_start_bot", not status.is_running)
    _set_enabled("btn_pause_bot", not status.is_stopped and status.is_running)
    _set_enabled("btn_stop_bot", not status.is_stopped)
    _set_enabled("btn_recalibrate", not status.is_stopped and not status.is_running)

    # PID plot
    _pid_history.append(status.pid_output)
    dpg.set_value("pid_series", [list(range(len(_pid_history))), list(_pid_history)])

    # Visualizer
    _update_visualizer(status)


def _resize_stat_cards():
    """Calculate card width from actual container size and apply."""
    try:
        container_w = dpg.get_item_rect_size("page_container")[0]
    except Exception:
        return
    if container_w <= 0:
        return
    # Available width minus 3 gaps between 4 cards, minus child_window padding
    usable = container_w - 3 * CARD_GAP - 2 * CARD_PADDING
    card_w = max(120, usable // 4)
    for tag in _card_tags:
        try:
            dpg.configure_item(tag, width=card_w)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Visualizer
# ---------------------------------------------------------------------------


def _create_visualizer():
    with dpg.drawlist(width=1, height=_vis_height, tag="visualizer"):
        dpg.draw_rectangle(
            (0, 0), (1, 1), color=(70, 75, 82),
            fill=VIS_TRACK, rounding=17, tag="vis_track",
        )
        dpg.draw_line(
            (0, 0), (0, 1), color=(88, 96, 105),
            thickness=2, tag="vis_center",
        )
        dpg.draw_rectangle(
            (0, 0), (1, 1), color=VIS_SAFE_ZONE_BD,
            fill=VIS_SAFE_ZONE, rounding=12, tag="vis_safe_zone",
        )
        dpg.draw_line(
            (0, 0), (0, 1), color=VIS_CURSOR,
            thickness=5, tag="vis_cursor",
        )
        dpg.draw_circle(
            (0, 0), 8, color=VIS_CURSOR_DOT,
            fill=VIS_CURSOR, tag="vis_cursor_dot",
        )


def _update_visualizer(status: BotStatus):
    try:
        panel_size = dpg.get_item_rect_size("vision_card")
        if not panel_size or panel_size[0] <= 80:
            return
        width = max(200, int(panel_size[0] - 40))
    except Exception:
        return

    dpg.configure_item("visualizer", width=width, height=_vis_height)
    track_left = 18
    track_right = width - 18
    track_top = 20
    track_bottom = 52
    track_mid = (track_left + track_right) / 2
    dpg.configure_item("vis_track", pmin=(track_left, track_top), pmax=(track_right, track_bottom))
    dpg.configure_item("vis_center", p1=(track_mid, 12), p2=(track_mid, 60))

    if status.bar_width <= 0:
        dpg.configure_item("vis_safe_zone", show=False)
        dpg.configure_item("vis_cursor", show=False)
        dpg.configure_item("vis_cursor_dot", show=False)
        return

    track_width = track_right - track_left
    scale = track_width / status.bar_width

    if status.target_x is not None:
        zone_half = max(24, min(64, track_width * 0.045))
        target_x = _scaled_x(status.target_x, status.bar_width, track_left, scale)
        dpg.configure_item(
            "vis_safe_zone", show=True,
            pmin=(max(track_left, target_x - zone_half), track_top),
            pmax=(min(track_right, target_x + zone_half), track_bottom),
        )
    else:
        dpg.configure_item("vis_safe_zone", show=False)

    if status.cursor_x is not None:
        cursor_x = _scaled_x(status.cursor_x, status.bar_width, track_left, scale)
        dpg.configure_item("vis_cursor", show=True, p1=(cursor_x, 10), p2=(cursor_x, 62))
        dpg.configure_item("vis_cursor_dot", show=True, center=(cursor_x, 36))
    else:
        dpg.configure_item("vis_cursor", show=False)
        dpg.configure_item("vis_cursor_dot", show=False)


def _scaled_x(value: int, bar_width: int, track_left: int, scale: float) -> float:
    value = max(0, min(bar_width, value))
    return track_left + value * scale


# ---------------------------------------------------------------------------
# Stat card
# ---------------------------------------------------------------------------


def _create_stat_card(tag: str, label: str, default: str, width: int = 200):
    with dpg.child_window(
        width=width, height=120, tag=tag, border=True, no_scrollbar=True,
    ):
        apply_glass_card_theme(tag)
        dpg.add_text(label, color=TEXT_VERY_MUTED)
        dpg.add_spacer(height=4)
        dpg.add_text(default, tag=f"{tag}_value", color=TEXT_PRIMARY)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_callback(
    callback: Callable[[], None] | None,
    bridge: BotBridge,
    fallback_cmd: str,
):
    if callback:
        callback()
    else:
        bridge.send_cmd(fallback_cmd)


def _set_enabled(tag: str, enabled: bool):
    if enabled:
        dpg.enable_item(tag)
    else:
        dpg.disable_item(tag)


def _state_label(state: FishingState) -> str:
    labels = {
        FishingState.IDLE: "Idle",
        FishingState.WAITING: "Waiting",
        FishingState.STRUGGLING: "Tracking",
        FishingState.RESULT: "Result",
    }
    return labels.get(state, state.value.title())


def _status_message(status: BotStatus) -> str:
    if status.is_stopped:
        return "Ready"
    if not status.is_running:
        return "Paused"
    if status.state is FishingState.WAITING:
        return "Waiting for bite"
    if status.state is FishingState.STRUGGLING:
        return "Tracking fish bar"
    if status.state is FishingState.RESULT:
        return "Closing result"
    return "Running"


def _fmt_optional(value: int | None) -> str:
    return str(value) if value is not None else "N/A"


def _fmt_roi(roi: tuple[int, int, int, int]) -> str:
    left, top, width, height = roi
    if width <= 0 or height <= 0:
        return "N/A"
    return f"{left},{top} {width}x{height}"

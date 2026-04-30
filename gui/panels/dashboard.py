from typing import Callable

import dearpygui.dearpygui as dpg

from gui.bridge import BotBridge, BotStatus
from modules.logic import FishingState


_pid_history: list[float] = [0.0] * 120
_theme_running = None
_theme_paused = None
_theme_stopped = None
_theme_start = None
_theme_pause = None
_theme_stop = None
_theme_neutral = None

_ACCENT = (112, 214, 186)
_ACCENT_BLUE = (126, 180, 255)
_WARNING = (229, 178, 98)
_DANGER = (224, 104, 108)
_TEXT = (232, 235, 239)
_MUTED = (140, 148, 157)
_TRACK = (38, 43, 49)
_DEFAULT_VIS_WIDTH = 900
_VIS_HEIGHT = 88


def create_dashboard(
    bridge: BotBridge,
    on_start: Callable[[], None] | None = None,
    on_stop: Callable[[], None] | None = None,
    on_recalibrate: Callable[[], None] | None = None,
):
    global _theme_running, _theme_paused, _theme_stopped
    global _theme_start, _theme_pause, _theme_stop, _theme_neutral

    _theme_running = _button_theme((42, 145, 108), (54, 174, 132), (64, 198, 151))
    _theme_paused = _button_theme((165, 116, 48), (192, 138, 58), (214, 157, 70))
    _theme_stopped = _button_theme((158, 70, 76), (190, 84, 92), (218, 103, 110))
    _theme_start = _button_theme((45, 124, 98), (57, 154, 122), (71, 186, 148))
    _theme_pause = _button_theme((139, 100, 45), (171, 124, 55), (202, 149, 71))
    _theme_stop = _button_theme((144, 63, 70), (179, 78, 86), (213, 94, 103))
    _theme_neutral = _button_theme((48, 56, 64), (63, 78, 84), (76, 97, 99))

    with dpg.group():
        with dpg.group(horizontal=True):
            with dpg.child_window(width=270, height=126, border=True):
                dpg.add_text("Status", color=_ACCENT)
                dpg.add_spacer(height=3)
                with dpg.group(horizontal=True):
                    dpg.add_button(
                        tag="stat_running_indicator",
                        label="Stopped",
                        width=112,
                        height=30,
                    )
                    dpg.bind_item_theme("stat_running_indicator", _theme_stopped)
                    dpg.add_spacer(width=8)
                    dpg.add_text("Idle", tag="stat_bot_state", color=_TEXT)
                dpg.add_spacer(height=8)
                dpg.add_text("Ready", tag="stat_status_message", color=_MUTED)

            with dpg.child_window(width=270, height=126, border=True):
                dpg.add_text("Session", color=_ACCENT_BLUE)
                dpg.add_spacer(height=3)
                _metric_row("Fish", "stat_fish_count", "0")
                _metric_row("Time", "stat_session_time", "00:00:00")
                _metric_row("Loop FPS", "stat_fps", "0.0")

            with dpg.child_window(width=270, height=126, border=True):
                dpg.add_text("Vision Health", color=_ACCENT)
                dpg.add_spacer(height=3)
                _metric_row("Tracking", "stat_tracking_state", "Offline")
                _metric_row("Lost frames", "stat_lost_frames", "0")
                _metric_row("PID output", "stat_pid_output", "0.000")

        dpg.add_spacer(height=10)
        with dpg.child_window(width=-1, height=76, border=True):
            with dpg.group(horizontal=True):
                dpg.add_text("Controls", color=_TEXT)
                dpg.add_spacer(width=12)
                dpg.add_button(
                    tag="btn_start_bot",
                    label="Start",
                    width=116,
                    height=36,
                    callback=lambda: _run_callback(on_start, bridge, "resume"),
                )
                dpg.bind_item_theme("btn_start_bot", _theme_start)
                dpg.add_button(
                    tag="btn_pause_bot",
                    label="Pause",
                    width=104,
                    height=36,
                    callback=lambda: bridge.send_cmd("pause"),
                )
                dpg.bind_item_theme("btn_pause_bot", _theme_pause)
                dpg.add_button(
                    tag="btn_stop_bot",
                    label="Stop",
                    width=104,
                    height=36,
                    callback=lambda: _run_callback(on_stop, bridge, "stop"),
                )
                dpg.bind_item_theme("btn_stop_bot", _theme_stop)
                dpg.add_button(
                    tag="btn_recalibrate",
                    label="Calibrate",
                    width=118,
                    height=36,
                    callback=lambda: _run_callback(
                        on_recalibrate, bridge, "recalibrate"
                    ),
                )
                dpg.bind_item_theme("btn_recalibrate", _theme_neutral)

        dpg.add_spacer(height=12)

        with dpg.group(horizontal=True):
            with dpg.child_window(width=450, height=238, border=True):
                dpg.add_text("PID Output", color=_ACCENT)
                dpg.add_spacer(height=4)
                with dpg.plot(
                    no_title=True,
                    no_menus=True,
                    no_box_select=True,
                    height=178,
                    width=-1,
                    tag="pid_plot",
                ):
                    dpg.add_plot_axis(
                        dpg.mvXAxis,
                        no_gridlines=True,
                        no_tick_labels=True,
                    )
                    with dpg.plot_axis(dpg.mvYAxis, tag="pid_y"):
                        dpg.add_line_series(
                            list(range(120)),
                            _pid_history,
                            label="Output",
                            tag="pid_series",
                        )
                    dpg.set_axis_limits("pid_y", -110, 110)

            with dpg.child_window(width=-1, height=238, border=True):
                dpg.add_text("Telemetry", color=_WARNING)
                dpg.add_separator()
                dpg.add_spacer(height=8)
                _metric_row("Cursor", "tele_cursor_x")
                _metric_row("Target", "tele_target_x")
                _metric_row("Button ROI", "tele_button_roi")
                _metric_row("Bar ROI", "tele_bar_roi")
                _metric_row("Cursor lost", "tele_lost_cursor")
                _metric_row("Target lost", "tele_lost_target")

        dpg.add_spacer(height=12)
        dpg.add_text("Vision Tracker", color=(218, 146, 194))
        with dpg.child_window(height=116, border=True, tag="visualizer_panel"):
            with dpg.drawlist(
                width=_DEFAULT_VIS_WIDTH,
                height=_VIS_HEIGHT,
                tag="visualizer",
            ):
                dpg.draw_rectangle(
                    (18, 24),
                    (_DEFAULT_VIS_WIDTH - 18, 58),
                    color=(70, 75, 82),
                    fill=_TRACK,
                    rounding=17,
                    tag="vis_track",
                )
                dpg.draw_line(
                    (_DEFAULT_VIS_WIDTH / 2, 16),
                    (_DEFAULT_VIS_WIDTH / 2, 66),
                    color=(88, 96, 105),
                    thickness=2,
                    tag="vis_center",
                )
                dpg.draw_rectangle(
                    (420, 24),
                    (480, 58),
                    color=(108, 222, 190, 220),
                    fill=(76, 184, 150, 95),
                    rounding=12,
                    tag="vis_safe_zone",
                )
                dpg.draw_line(
                    (450, 14),
                    (450, 68),
                    color=(232, 196, 86),
                    thickness=5,
                    tag="vis_cursor",
                )
                dpg.draw_circle(
                    (450, 41),
                    8,
                    color=(255, 235, 165),
                    fill=(232, 196, 86),
                    tag="vis_cursor_dot",
                )


def update_dashboard_ui(bridge: BotBridge):
    global _pid_history
    status = bridge.latest_status()

    dpg.set_value("stat_fish_count", str(status.fish_count))
    secs = int(status.session_secs)
    h, m, s = secs // 3600, (secs % 3600) // 60, secs % 60
    dpg.set_value("stat_session_time", f"{h:02d}:{m:02d}:{s:02d}")
    dpg.set_value("stat_bot_state", _state_label(status.state))
    dpg.set_value("stat_fps", f"{status.fps:.1f}")
    dpg.set_value("stat_pid_output", f"{status.pid_output:.3f}")

    if status.is_stopped:
        dpg.configure_item("stat_running_indicator", label="Stopped")
        dpg.bind_item_theme("stat_running_indicator", _theme_stopped)
    elif status.is_running:
        dpg.configure_item("stat_running_indicator", label="Running")
        dpg.bind_item_theme("stat_running_indicator", _theme_running)
    else:
        dpg.configure_item("stat_running_indicator", label="Paused")
        dpg.bind_item_theme("stat_running_indicator", _theme_paused)

    dpg.set_value("stat_status_message", _status_message(status))
    dpg.set_value("stat_tracking_state", _tracking_label(status))
    dpg.configure_item("stat_tracking_state", color=_tracking_color(status))
    dpg.set_value("stat_lost_frames", str(status.lost_frames))

    _set_enabled("btn_start_bot", not status.is_running)
    _set_enabled("btn_pause_bot", not status.is_stopped and status.is_running)
    _set_enabled("btn_stop_bot", not status.is_stopped)
    _set_enabled("btn_recalibrate", not status.is_stopped and not status.is_running)

    dpg.set_value("tele_cursor_x", _fmt_optional(status.cursor_x))
    dpg.set_value("tele_target_x", _fmt_optional(status.target_x))
    dpg.set_value("tele_button_roi", _fmt_roi(status.button_roi))
    dpg.set_value("tele_bar_roi", _fmt_roi(status.bar_roi))
    dpg.set_value("tele_lost_cursor", str(status.lost_cursor_frames))
    dpg.set_value("tele_lost_target", str(status.lost_target_frames))

    _pid_history.append(status.pid_output)
    if len(_pid_history) > 120:
        _pid_history = _pid_history[-120:]
    dpg.set_value("pid_series", [list(range(len(_pid_history))), _pid_history])

    _update_visualizer(status)


def _update_visualizer(status: BotStatus):
    width = _DEFAULT_VIS_WIDTH
    try:
        panel_size = dpg.get_item_rect_size("visualizer_panel")
        if panel_size and panel_size[0] > 80:
            width = max(360, int(panel_size[0] - 24))
    except Exception:
        pass

    dpg.configure_item("visualizer", width=width, height=_VIS_HEIGHT)
    track_left = 18
    track_right = width - 18
    track_top = 24
    track_bottom = 58
    track_mid = (track_left + track_right) / 2
    dpg.configure_item(
        "vis_track",
        pmin=(track_left, track_top),
        pmax=(track_right, track_bottom),
    )
    dpg.configure_item(
        "vis_center",
        p1=(track_mid, 16),
        p2=(track_mid, 66),
    )

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
            "vis_safe_zone",
            show=True,
            pmin=(max(track_left, target_x - zone_half), track_top),
            pmax=(min(track_right, target_x + zone_half), track_bottom),
        )
    else:
        dpg.configure_item("vis_safe_zone", show=False)

    if status.cursor_x is not None:
        cursor_x = _scaled_x(status.cursor_x, status.bar_width, track_left, scale)
        dpg.configure_item("vis_cursor", show=True, p1=(cursor_x, 14), p2=(cursor_x, 68))
        dpg.configure_item("vis_cursor_dot", show=True, center=(cursor_x, 41))
    else:
        dpg.configure_item("vis_cursor", show=False)
        dpg.configure_item("vis_cursor_dot", show=False)


def _scaled_x(value: int, bar_width: int, track_left: int, scale: float) -> float:
    value = max(0, min(bar_width, value))
    return track_left + value * scale


def _button_theme(
    color: tuple[int, int, int],
    hovered: tuple[int, int, int],
    active: tuple[int, int, int],
):
    with dpg.theme() as theme:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_Button, color)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, hovered)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, active)
            dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255))
    return theme


def _metric_row(label: str, tag: str, default: str = "N/A"):
    with dpg.group(horizontal=True):
        dpg.add_text(label, color=_MUTED)
        dpg.add_spacer(width=10)
        dpg.add_text(default, tag=tag, color=_TEXT)


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


def _tracking_label(status: BotStatus) -> str:
    if status.is_stopped:
        return "Offline"
    if status.cursor_x is not None and status.target_x is not None:
        return "Locked"
    if status.cursor_x is None and status.target_x is None:
        return "No signal"
    if status.cursor_x is None:
        return "Cursor lost"
    return "Target lost"


def _tracking_color(status: BotStatus) -> tuple[int, int, int]:
    if status.is_stopped:
        return _MUTED
    if status.cursor_x is not None and status.target_x is not None:
        return _ACCENT
    return _WARNING if status.lost_frames < 20 else _DANGER


def _fmt_optional(value: int | None) -> str:
    return str(value) if value is not None else "N/A"


def _fmt_roi(roi: tuple[int, int, int, int]) -> str:
    left, top, width, height = roi
    if width <= 0 or height <= 0:
        return "N/A"
    return f"{left},{top} {width}x{height}"

"""
gui/panels/dashboard.py
仪表盘面板：控制按钮、统计信息、PID 实时曲线、进度条可视化。
"""
import dearpygui.dearpygui as dpg

from gui.bridge import BotBridge

# 模块级状态（用于 update 闭包）
_bridge: BotBridge = None  # type: ignore
_pid_history: list[float] = [0.0] * 100


def create_dashboard(bridge: BotBridge):
    global _bridge
    _bridge = bridge

    with dpg.group():
        # --- Control Buttons ---
        with dpg.group(horizontal=True):
            dpg.add_button(label="▶ START", width=130, height=40,
                           callback=lambda: bridge.send_cmd("resume"))
            dpg.add_button(label="⏸ PAUSE", width=130, height=40,
                           callback=lambda: bridge.send_cmd("pause"))
            dpg.add_button(label="🔧 CALIBRATE", width=130, height=40,
                           callback=lambda: bridge.send_cmd("recalibrate"))

        dpg.add_spacer(height=10)
        dpg.add_separator()
        dpg.add_spacer(height=10)

        # --- Statistics + PID side by side ---
        with dpg.group(horizontal=True):
            # Left: Stats
            with dpg.child_window(width=280, height=130, border=True):
                dpg.add_text("STATISTICS", color=(150, 150, 255))
                dpg.add_separator()
                dpg.add_text("Fish Caught: 0", tag="stat_fish_count")
                dpg.add_text("Session: 00:00:00", tag="stat_session_time")
                dpg.add_text("State: IDLE", tag="stat_bot_state")
                dpg.add_text("Running: No", tag="stat_running")

            # Right: PID Plot
            with dpg.child_window(width=-1, height=130, border=True):
                dpg.add_text("PID OUTPUT", color=(150, 255, 150))
                with dpg.plot(no_title=True, no_menus=True, no_box_select=True,
                              height=90, width=-1, tag="pid_plot"):
                    dpg.add_plot_axis(dpg.mvXAxis, no_gridlines=True,
                                      no_tick_labels=True, tag="pid_x")
                    with dpg.plot_axis(dpg.mvYAxis, tag="pid_y"):
                        dpg.add_line_series(list(range(100)), _pid_history,
                                            label="output", tag="pid_series")
                    dpg.set_axis_limits("pid_y", -100, 100)

        dpg.add_spacer(height=15)

        # --- Progress Bar Visualizer ---
        dpg.add_text("PROGRESS BAR VISUALIZER", color=(255, 200, 100))
        with dpg.drawlist(width=900, height=80, tag="visualizer"):
            # Background
            dpg.draw_rectangle((0, 20), (900, 60),
                               color=(60, 60, 60), fill=(30, 30, 30))
            # Safe zone placeholder
            dpg.draw_rectangle((350, 20), (550, 60),
                               color=(0, 200, 180, 120), fill=(0, 200, 180, 60),
                               tag="vis_safe_zone")
            # Cursor placeholder
            dpg.draw_line((450, 10), (450, 70),
                          color=(255, 255, 0), thickness=3, tag="vis_cursor")


def update_dashboard_ui(bridge: BotBridge):
    global _pid_history
    status = bridge.latest_status()

    # Stats text
    dpg.set_value("stat_fish_count", f"Fish Caught: {status.fish_count}")
    secs = int(status.session_secs)
    h, m, s = secs // 3600, (secs % 3600) // 60, secs % 60
    dpg.set_value("stat_session_time", f"Session: {h:02d}:{m:02d}:{s:02d}")
    dpg.set_value("stat_bot_state", f"State: {status.state.value}")
    dpg.set_value("stat_running",
                  f"Running: {'Yes' if status.is_running else 'Paused'}")

    # PID plot
    _pid_history.append(status.pid_output)
    if len(_pid_history) > 100:
        _pid_history = _pid_history[-100:]
    dpg.set_value("pid_series", [list(range(len(_pid_history))), _pid_history])

    # Visualizer
    if status.bar_width > 0:
        scale = 900.0 / status.bar_width
        if status.target_x is not None:
            zone_half = 45  # approximate half-width of safe zone in vis pixels
            cx = status.target_x * scale
            dpg.configure_item("vis_safe_zone",
                               pmin=(max(0, cx - zone_half), 20),
                               pmax=(min(900, cx + zone_half), 60))
        if status.cursor_x is not None:
            cx = status.cursor_x * scale
            dpg.configure_item("vis_cursor",
                               p1=(cx, 10), p2=(cx, 70))

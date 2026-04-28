"""
gui/panels/dashboard.py
仪表盘面板：控制按钮、统计信息、PID 实时曲线、进度条可视化。
"""
import dearpygui.dearpygui as dpg

from gui.bridge import BotBridge

# 模块级状态（用于 update 闭包）
_bridge: BotBridge = None  # type: ignore
_pid_history: list[float] = [0.0] * 100

# Themes for Status Indicator
_theme_running = None
_theme_paused = None

def create_dashboard(bridge: BotBridge):
    global _bridge, _theme_running, _theme_paused
    _bridge = bridge

    # Create dynamic themes for status indicator
    with dpg.theme() as _theme_running:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (0, 180, 100))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (0, 180, 100))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (0, 180, 100))
            dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255))

    with dpg.theme() as _theme_paused:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (180, 60, 60))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (180, 60, 60))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (180, 60, 60))
            dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255))

    with dpg.group():
        # --- Top Summary Bar ---
        with dpg.child_window(height=80, border=False):
            with dpg.group(horizontal=True):
                # Status Indicator Card
                with dpg.group():
                    dpg.add_text("BOT STATUS", color=(100, 200, 255))
                    with dpg.group(horizontal=True):
                        dpg.add_button(tag="stat_running_indicator", label="PAUSED", width=120)
                        dpg.bind_item_theme("stat_running_indicator", _theme_paused)
                        dpg.add_text("State:", color=(150, 150, 150))
                        dpg.add_text("IDLE", tag="stat_bot_state", color=(255, 255, 255))
                
                dpg.add_spacer(width=40)
                
                # Stats Summary Card
                with dpg.group():
                    dpg.add_text("QUICK STATS", color=(100, 200, 255))
                    with dpg.group(horizontal=True):
                        dpg.add_text("Fish:", color=(150, 150, 150))
                        dpg.add_text("0", tag="stat_fish_count", color=(255, 255, 255))
                        dpg.add_spacer(width=20)
                        dpg.add_text("Time:", color=(150, 150, 150))
                        dpg.add_text("00:00:00", tag="stat_session_time", color=(255, 255, 255))

        dpg.add_separator()
        dpg.add_spacer(height=10)

        # --- Main Controls ---
        with dpg.group(horizontal=True):
            dpg.add_button(label="START", width=120, height=35,
                           callback=lambda: bridge.send_cmd("resume"))
            dpg.add_button(label="PAUSE", width=120, height=35,
                           callback=lambda: bridge.send_cmd("pause"))
            dpg.add_button(label="CALIBRATE", width=120, height=35,
                           callback=lambda: bridge.send_cmd("recalibrate"))

        dpg.add_spacer(height=15)

        # --- Visualizers Section ---
        with dpg.group(horizontal=True):
            # Left: PID Output Card
            with dpg.child_window(width=400, height=180, border=True):
                dpg.add_text("PID OUTPUT (REAL-TIME)", color=(100, 255, 200))
                with dpg.plot(no_title=True, no_menus=True, no_box_select=True,
                              height=130, width=-1, tag="pid_plot"):
                    dpg.add_plot_axis(dpg.mvXAxis, no_gridlines=True, no_tick_labels=True)
                    with dpg.plot_axis(dpg.mvYAxis, tag="pid_y"):
                        dpg.add_line_series(list(range(100)), _pid_history,
                                            label="Output", tag="pid_series")
                    dpg.set_axis_limits("pid_y", -100, 100)

            # Right: Vision/Analysis Card
            with dpg.child_window(width=-1, height=180, border=True):
                dpg.add_text("TELEMETRY", color=(255, 200, 100))
                dpg.add_separator()
                dpg.add_spacer(height=5)
                with dpg.group(horizontal=True):
                    dpg.add_text("Cursor X:", color=(150, 150, 150))
                    dpg.add_text("N/A", tag="tele_cursor_x")
                with dpg.group(horizontal=True):
                    dpg.add_text("Target X:", color=(150, 150, 150))
                    dpg.add_text("N/A", tag="tele_target_x")
                with dpg.group(horizontal=True):
                    dpg.add_text("Process FPS:", color=(150, 150, 150))
                    dpg.add_text("0.0", tag="tele_fps")

        dpg.add_spacer(height=20)

        # --- Bottom: Progress Bar Visualizer (Full Width) ---
        dpg.add_text("LIVE FISHING TRACKER", color=(255, 100, 255))
        with dpg.child_window(height=100, border=True):
            with dpg.drawlist(width=900, height=80, tag="visualizer"):
                dpg.draw_rectangle((0, 25), (900, 55),
                                   color=(60, 60, 70), fill=(30, 32, 45), rounding=15)
                dpg.draw_rectangle((350, 25), (550, 55),
                                   color=(0, 255, 220, 200), fill=(0, 255, 200, 80),
                                   rounding=10, tag="vis_safe_zone")
                dpg.draw_line((450, 15), (450, 65),
                              color=(255, 255, 0), thickness=4, tag="vis_cursor")
                dpg.draw_circle((450, 40), 6, color=(255, 255, 255), fill=(255, 255, 0), tag="vis_cursor_dot")


def update_dashboard_ui(bridge: BotBridge):
    global _pid_history
    status = bridge.latest_status()

    # Stats text
    dpg.set_value("stat_fish_count", str(status.fish_count))
    secs = int(status.session_secs)
    h, m, s = secs // 3600, (secs % 3600) // 60, secs % 60
    dpg.set_value("stat_session_time", f"{h:02d}:{m:02d}:{s:02d}")
    dpg.set_value("stat_bot_state", status.state.value)
    
    # Running Indicator Styling (Fixed color keyword issue)
    if status.is_running:
        dpg.configure_item("stat_running_indicator", label="RUNNING")
        dpg.bind_item_theme("stat_running_indicator", _theme_running)
    else:
        dpg.configure_item("stat_running_indicator", label="PAUSED")
        dpg.bind_item_theme("stat_running_indicator", _theme_paused)

    # Telemetry
    dpg.set_value("tele_cursor_x", f"{status.cursor_x if status.cursor_x else 'N/A'}")
    dpg.set_value("tele_target_x", f"{status.target_x if status.target_x else 'N/A'}")
    dpg.set_value("tele_fps", f"{status.fps:.1f}")

    # PID plot
    _pid_history.append(status.pid_output)
    if len(_pid_history) > 100:
        _pid_history = _pid_history[-100:]
    dpg.set_value("pid_series", [list(range(len(_pid_history))), _pid_history])

    # Visualizer
    if status.bar_width > 0:
        scale = 900.0 / status.bar_width
        if status.target_x is not None:
            zone_half = 45
            cx = status.target_x * scale
            dpg.configure_item("vis_safe_zone",
                               pmin=(max(0, cx - zone_half), 25),
                               pmax=(min(900, cx + zone_half), 55))
        if status.cursor_x is not None:
            cx = status.cursor_x * scale
            dpg.configure_item("vis_cursor",
                               p1=(cx, 15), p2=(cx, 65))
            dpg.configure_item("vis_cursor_dot", center=(cx, 40))



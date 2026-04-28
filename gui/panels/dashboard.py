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
        # --- Top Summary Bar (Glassmorphism inspired) ---
        with dpg.child_window(height=90, border=False):
            with dpg.group(horizontal=True):
                # Status Indicator Card
                with dpg.group():
                    dpg.add_text("  BOT STATUS", color=(120, 210, 255))
                    with dpg.group(horizontal=True):
                        dpg.add_spacer(width=10)
                        dpg.add_button(tag="stat_running_indicator", label="PAUSED", width=130, height=30)
                        dpg.bind_item_theme("stat_running_indicator", _theme_paused)
                        dpg.add_spacer(width=5)
                        dpg.add_text("Current State:", color=(140, 145, 160))
                        dpg.add_text("IDLE", tag="stat_bot_state", color=(255, 255, 255))
                
                dpg.add_spacer(width=60)
                
                # Stats Summary Card
                with dpg.group():
                    dpg.add_text("  QUICK STATS", color=(120, 210, 255))
                    with dpg.group(horizontal=True):
                        dpg.add_spacer(width=10)
                        dpg.add_text("Fish Caught:", color=(140, 145, 160))
                        dpg.add_text("0", tag="stat_fish_count", color=(255, 255, 255))
                        dpg.add_spacer(width=30)
                        dpg.add_text("Session Time:", color=(140, 145, 160))
                        dpg.add_text("00:00:00", tag="stat_session_time", color=(255, 255, 255))

        dpg.add_spacer(height=10)
        dpg.add_separator()
        dpg.add_spacer(height=15)

        # --- Main Controls ---
        with dpg.group(horizontal=True):
            dpg.add_button(label=" RESUME BOT (F8) ", width=180, height=40,
                           callback=lambda: bridge.send_cmd("resume"))
            dpg.add_button(label=" PAUSE BOT ", width=180, height=40,
                           callback=lambda: bridge.send_cmd("pause"))
            dpg.add_button(label=" RE-CALIBRATE ", width=180, height=40,
                           callback=lambda: bridge.send_cmd("recalibrate"))

        dpg.add_spacer(height=25)

        # --- Visualizers Section ---
        with dpg.group(horizontal=True):
            # Left: PID Output Card
            with dpg.child_window(width=450, height=220, border=True):
                dpg.add_text("  PID CONTROL LOOP OUTPUT", color=(100, 255, 200))
                dpg.add_spacer(height=5)
                with dpg.plot(no_title=True, no_menus=True, no_box_select=True,
                               height=160, width=-1, tag="pid_plot"):
                    dpg.add_plot_axis(dpg.mvXAxis, no_gridlines=True, no_tick_labels=True)
                    with dpg.plot_axis(dpg.mvYAxis, tag="pid_y"):
                        dpg.add_line_series(list(range(100)), _pid_history,
                                            label="Output", tag="pid_series")
                    dpg.set_axis_limits("pid_y", -110, 110)

            # Right: Vision/Analysis Card
            with dpg.child_window(width=-1, height=220, border=True):
                dpg.add_text("  REAL-TIME TELEMETRY", color=(255, 200, 100))
                dpg.add_separator()
                dpg.add_spacer(height=10)
                with dpg.group(horizontal=True):
                    dpg.add_text("    Cursor Position (Rel):", color=(140, 145, 160))
                    dpg.add_text("N/A", tag="tele_cursor_x", color=(255, 255, 255))
                with dpg.group(horizontal=True):
                    dpg.add_text("    Target Position (Rel):", color=(140, 145, 160))
                    dpg.add_text("N/A", tag="tele_target_x", color=(255, 255, 255))
                dpg.add_spacer(height=10)
                with dpg.group(horizontal=True):
                    dpg.add_text("    Processing Frequency:", color=(140, 145, 160))
                    dpg.add_text("0.0", tag="tele_fps", color=(100, 255, 150))
                    dpg.add_text("Hz", color=(100, 105, 120))

        dpg.add_spacer(height=25)

        # --- Bottom: Progress Bar Visualizer (Full Width) ---
        dpg.add_text("  LIVE VISION TRACKER", color=(255, 100, 255))
        with dpg.child_window(height=110, border=True):
            with dpg.drawlist(width=1200, height=80, tag="visualizer"):
                # Background Track
                dpg.draw_rectangle((0, 20), (1200, 60),
                                   color=(50, 52, 65), fill=(22, 24, 34), rounding=20)
                
                # Safe Zone (Target)
                dpg.draw_rectangle((450, 20), (750, 60),
                                   color=(0, 255, 220, 200), fill=(0, 255, 200, 60),
                                   rounding=15, tag="vis_safe_zone")
                
                # Cursor (Player)
                dpg.draw_line((600, 10), (600, 70),
                               color=(255, 255, 0), thickness=5, tag="vis_cursor")
                dpg.draw_circle((600, 40), 8, color=(255, 255, 255), fill=(255, 255, 0), tag="vis_cursor_dot")


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



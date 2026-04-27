"""
gui/app.py — DearPyGui 主窗口
启动方式：python start_gui.py
"""
import threading

import dearpygui.dearpygui as dpg

from gui.bridge import BotBridge
from gui.panels.dashboard import create_dashboard, update_dashboard_ui
from gui.panels.logs import create_logs, update_logs_ui
from gui.panels.settings import create_settings
from main import NTEFishingBot


class FishingGUI:
    def __init__(self):
        self.bridge = BotBridge()
        self.bot = NTEFishingBot(bridge=self.bridge)
        self.bot_thread: threading.Thread | None = None

        self._setup_dpg()
        self._create_windows()

    def _setup_dpg(self):
        dpg.create_context()
        dpg.create_viewport(title='NTE Auto-Fish Control Center',
                            width=1000, height=750)
        dpg.setup_dearpygui()

        with dpg.theme() as theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 12, 12)
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 6, 4)
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 8, 6)
                dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 5)
                dpg.add_theme_style(dpg.mvStyleVar_GrabRounding, 5)
                dpg.add_theme_style(dpg.mvStyleVar_TabRounding, 4)
                dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (22, 22, 28))
                dpg.add_theme_color(dpg.mvThemeCol_ChildBg, (30, 30, 38))
                dpg.add_theme_color(dpg.mvThemeCol_Header, (45, 45, 90))
                dpg.add_theme_color(
                    dpg.mvThemeCol_HeaderHovered, (60, 60, 120))
                dpg.add_theme_color(dpg.mvThemeCol_Button, (55, 55, 105))
                dpg.add_theme_color(
                    dpg.mvThemeCol_ButtonHovered, (75, 75, 145))
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (35, 35, 50))
                dpg.add_theme_color(dpg.mvThemeCol_SliderGrab, (100, 120, 220))
                dpg.add_theme_color(dpg.mvThemeCol_Tab, (40, 40, 70))
                dpg.add_theme_color(dpg.mvThemeCol_TabActive, (65, 65, 130))
        dpg.bind_theme(theme)

    def _create_windows(self):
        with dpg.window(tag="PrimaryWindow", no_close=True, no_move=True):
            with dpg.tab_bar():
                with dpg.tab(label="Dashboard"):
                    create_dashboard(self.bridge)
                with dpg.tab(label="Settings"):
                    create_settings(self.bridge)
                with dpg.tab(label="Logs"):
                    create_logs(self.bridge)

        dpg.set_primary_window("PrimaryWindow", True)
        self._start_bot()

    def _start_bot(self):
        if self.bot_thread and self.bot_thread.is_alive():
            return
        self.bot.calibrate()
        self.bot_thread = threading.Thread(target=self.bot.run, daemon=True)
        self.bot_thread.start()
        self.bridge.send_cmd("pause")

    def run(self):
        dpg.show_viewport()
        while dpg.is_dearpygui_running():
            update_dashboard_ui(self.bridge)
            update_logs_ui(self.bridge)
            dpg.render_dearpygui_frame()
        dpg.destroy_context()


if __name__ == "__main__":
    gui = FishingGUI()
    gui.run()

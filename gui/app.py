"""
gui/app.py — DearPyGui 主窗口
启动方式：python start_gui.py
"""
import threading
import keyboard

import dearpygui.dearpygui as dpg

from config import CFG
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
        self._setup_hotkeys()
        self._create_windows()

    def _setup_dpg(self):
        dpg.create_context()
        # Increased viewport size for 4K screens and added font scale
        dpg.create_viewport(title='NTE Auto-Fish Control Center',
                            width=1200, height=800,
                            always_on_top=CFG.always_on_top)
        dpg.setup_dearpygui()
        
        # Set global font scale for better visibility on High DPI (4K) screens
        dpg.set_global_font_scale(1.25)

        # Modern Dark Theme with Accent Colors
        with dpg.theme() as theme:
            with dpg.theme_component(dpg.mvAll):
                # Layout & Spacing
                dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 15, 15)
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 8, 6)
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 10, 10)
                dpg.add_theme_style(dpg.mvStyleVar_IndentSpacing, 25)
                dpg.add_theme_style(dpg.mvStyleVar_ScrollbarSize, 12)
                dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 8)
                dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 6)
                dpg.add_theme_style(dpg.mvStyleVar_GrabRounding, 6)
                dpg.add_theme_style(dpg.mvStyleVar_TabRounding, 6)
                dpg.add_theme_style(dpg.mvStyleVar_PopupRounding, 8)
                dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 8)

                # Color Palette (Midnight Blue & Cyan Accent)
                # Backgrounds
                dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (15, 16, 22))
                dpg.add_theme_color(dpg.mvThemeCol_ChildBg, (24, 25, 34))
                dpg.add_theme_color(dpg.mvThemeCol_PopupBg, (24, 25, 34))
                dpg.add_theme_color(dpg.mvThemeCol_Border, (40, 42, 54, 150))
                
                # Header & Tabs
                dpg.add_theme_color(dpg.mvThemeCol_Header, (45, 55, 90))
                dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, (65, 80, 140))
                dpg.add_theme_color(dpg.mvThemeCol_HeaderActive, (80, 100, 180))
                dpg.add_theme_color(dpg.mvThemeCol_Tab, (30, 32, 45))
                dpg.add_theme_color(dpg.mvThemeCol_TabHovered, (50, 60, 120))
                dpg.add_theme_color(dpg.mvThemeCol_TabActive, (70, 90, 200))
                dpg.add_theme_color(dpg.mvThemeCol_TabUnfocused, (25, 27, 38))
                dpg.add_theme_color(dpg.mvThemeCol_TabUnfocusedActive, (40, 42, 60))

                # Buttons
                dpg.add_theme_color(dpg.mvThemeCol_Button, (45, 50, 80))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (60, 80, 160))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (80, 110, 220))
                
                # Frame & Inputs
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (35, 38, 55))
                dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, (45, 50, 75))
                dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, (55, 65, 100))
                
                # Sliders & Grabs
                dpg.add_theme_color(dpg.mvThemeCol_SliderGrab, (0, 180, 255))
                dpg.add_theme_color(dpg.mvThemeCol_SliderGrabActive, (100, 220, 255))
                
                # Text
                dpg.add_theme_color(dpg.mvThemeCol_Text, (220, 225, 240))
                dpg.add_theme_color(dpg.mvThemeCol_TextDisabled, (100, 105, 130))

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

    def _setup_hotkeys(self):
        try:
            keyboard.add_hotkey(CFG.hotkeys.toggle, self._toggle_bot_hotkey)
            keyboard.add_hotkey(CFG.hotkeys.stop, self._stop_bot_hotkey)
        except Exception as e:
            self.bridge.push_log(f"Failed to register hotkeys: {e}")

    def _toggle_bot_hotkey(self):
        status = self.bridge.latest_status()
        if status.is_running:
            self.bridge.send_cmd("pause")
        else:
            self.bridge.send_cmd("resume")

    def _stop_bot_hotkey(self):
        self.bridge.send_cmd("stop")

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

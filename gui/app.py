"""
gui/app.py — DearPyGui 主窗口
启动方式：python start_gui.py
"""
import threading
import keyboard
import ctypes
import os

import dearpygui.dearpygui as dpg

from config import CFG
from gui.bridge import BotBridge
from gui.panels.dashboard import create_dashboard, update_dashboard_ui
from gui.panels.logs import create_logs, update_logs_ui
from gui.panels.settings import create_settings
from main import NTEFishingBot


class FishingGUI:
    def __init__(self):
        self._enable_hidpi()
        self.bridge = BotBridge()
        self.bot = NTEFishingBot(bridge=self.bridge)
        self.bot_thread: threading.Thread | None = None

        self._setup_dpg()
        self._setup_hotkeys()
        self._create_windows()

    def _enable_hidpi(self):
        """Enable High DPI awareness on Windows."""
        try:
            # SetProcessDpiAwareness(1) -> Process_System_DPI_Aware
            # SetProcessDpiAwareness(2) -> Process_Per_Monitor_DPI_Aware
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

    def _setup_dpg(self):
        dpg.create_context()
        
        # Enhanced viewport configuration
        dpg.create_viewport(title='NTE Auto-Fish Control Center',
                            width=1280, height=850,
                            always_on_top=CFG.always_on_top)
        dpg.setup_dearpygui()
        
        # Responsive global font scale
        dpg.set_global_font_scale(1.0) # Base scale, we will rely on DPI awareness
        
        # Premium Modern Dark Theme
        with dpg.theme() as theme:
            with dpg.theme_component(dpg.mvAll):
                # Layout & Spacing
                dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 16, 16)
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 10, 8)
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 12, 12)
                dpg.add_theme_style(dpg.mvStyleVar_IndentSpacing, 25)
                dpg.add_theme_style(dpg.mvStyleVar_ScrollbarSize, 14)
                dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 12)
                dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 8)
                dpg.add_theme_style(dpg.mvStyleVar_GrabRounding, 8)
                dpg.add_theme_style(dpg.mvStyleVar_TabRounding, 8)
                dpg.add_theme_style(dpg.mvStyleVar_PopupRounding, 12)
                dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 12)

                # Color Palette (Deep Indigo & Electric Cyan)
                # Backgrounds
                dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (10, 11, 16))
                dpg.add_theme_color(dpg.mvThemeCol_ChildBg, (18, 20, 28, 200)) # Slight transparency
                dpg.add_theme_color(dpg.mvThemeCol_PopupBg, (24, 26, 36))
                dpg.add_theme_color(dpg.mvThemeCol_Border, (45, 48, 65, 180))
                
                # Header & Tabs
                dpg.add_theme_color(dpg.mvThemeCol_Header, (40, 50, 85))
                dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, (60, 75, 130))
                dpg.add_theme_color(dpg.mvThemeCol_HeaderActive, (70, 95, 180))
                dpg.add_theme_color(dpg.mvThemeCol_Tab, (20, 22, 32))
                dpg.add_theme_color(dpg.mvThemeCol_TabHovered, (55, 65, 120))
                dpg.add_theme_color(dpg.mvThemeCol_TabActive, (75, 100, 220))
                dpg.add_theme_color(dpg.mvThemeCol_TabUnfocused, (15, 16, 24))
                dpg.add_theme_color(dpg.mvThemeCol_TabUnfocusedActive, (35, 40, 65))

                # Buttons
                dpg.add_theme_color(dpg.mvThemeCol_Button, (40, 45, 75))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (65, 85, 180))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (85, 110, 240))
                
                # Frame & Inputs
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (28, 30, 45))
                dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, (40, 45, 65))
                dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, (50, 60, 95))
                
                # Sliders & Grabs
                dpg.add_theme_color(dpg.mvThemeCol_SliderGrab, (0, 195, 255))
                dpg.add_theme_color(dpg.mvThemeCol_SliderGrabActive, (80, 225, 255))
                
                dpg.add_theme_color(dpg.mvThemeCol_Text, (225, 230, 250))
                dpg.add_theme_color(dpg.mvThemeCol_TextDisabled, (110, 115, 145))

        dpg.bind_theme(theme)

    def _create_windows(self):
        with dpg.window(tag="PrimaryWindow", no_close=True, no_move=True):
            with dpg.tab_bar():
                with dpg.tab(label=" DASHBOARD "):
                    create_dashboard(self.bridge)
                with dpg.tab(label=" SETTINGS "):
                    create_settings(self.bridge)
                with dpg.tab(label=" ACTIVITY LOGS "):
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

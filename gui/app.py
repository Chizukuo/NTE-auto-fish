"""DearPyGui application shell for NTE Auto-Fish."""
import ctypes
import threading

import dearpygui.dearpygui as dpg
import keyboard

from config import CFG
from gui.bridge import BotBridge
from gui.panels.dashboard import create_dashboard, update_dashboard_ui
from gui.panels.logs import create_logs, update_logs_ui
from gui.panels.settings import create_settings
from main import NTEFishingBot


APP_TITLE = "NTE Auto-Fish"


class FishingGUI:
    def __init__(self):
        self._enable_hidpi()
        self.bridge = BotBridge()
        self.bot = NTEFishingBot(bridge=self.bridge)
        self.bot_thread: threading.Thread | None = None
        self._hotkey_handles: list = []

        self._setup_dpg()
        self._setup_hotkeys()
        self._create_windows()

    def _enable_hidpi(self):
        """Enable High DPI awareness on Windows."""
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

    def _setup_dpg(self):
        dpg.create_context()
        dpg.create_viewport(
            title=f"{APP_TITLE} Control Center",
            width=1180,
            height=780,
            min_width=980,
            min_height=680,
            always_on_top=CFG.always_on_top,
        )
        dpg.setup_dearpygui()
        dpg.set_global_font_scale(1.0)
        dpg.bind_theme(_build_theme())

    def _create_windows(self):
        with dpg.window(tag="PrimaryWindow", no_close=True, no_move=True):
            with dpg.tab_bar():
                with dpg.tab(label="Dashboard"):
                    create_dashboard(
                        self.bridge,
                        on_start=self._start_bot,
                        on_stop=self._stop_bot,
                        on_recalibrate=lambda: self.bridge.send_cmd("recalibrate"),
                    )
                with dpg.tab(label="Settings"):
                    create_settings(
                        self.bridge,
                        on_hotkeys_changed=self._register_hotkeys,
                    )
                with dpg.tab(label="Activity"):
                    create_logs(self.bridge)

        dpg.set_primary_window("PrimaryWindow", True)
        self._start_bot()

    def _setup_hotkeys(self):
        self._register_hotkeys()

    def _register_hotkeys(self):
        self._clear_hotkeys()
        try:
            toggle = CFG.hotkeys.toggle.strip()
            stop = CFG.hotkeys.stop.strip()
            if toggle:
                self._hotkey_handles.append(
                    keyboard.add_hotkey(toggle, self._toggle_bot_hotkey)
                )
            if stop:
                self._hotkey_handles.append(
                    keyboard.add_hotkey(stop, self._stop_bot_hotkey)
                )
            self.bridge.push_log(
                "Hotkeys active: "
                f"toggle={toggle.upper() if toggle else 'disabled'}, "
                f"stop={stop.upper() if stop else 'disabled'}"
            )
        except Exception as exc:
            self.bridge.push_log(f"Hotkey registration failed: {exc}")

    def _clear_hotkeys(self):
        for handle in self._hotkey_handles:
            try:
                keyboard.remove_hotkey(handle)
            except Exception:
                pass
        self._hotkey_handles.clear()

    def _toggle_bot_hotkey(self):
        status = self.bridge.latest_status()
        if status.is_running:
            self.bridge.send_cmd("pause")
        elif status.is_stopped or not (self.bot_thread and self.bot_thread.is_alive()):
            self._start_bot()
        else:
            self.bridge.send_cmd("resume")

    def _stop_bot_hotkey(self):
        self._stop_bot()

    def _start_bot(self):
        if self.bot_thread and self.bot_thread.is_alive():
            if self.bot.is_stopped:
                self.bridge.push_log(
                    "Bot is still stopping. Wait a moment before starting again."
                )
                return
            self.bridge.send_cmd("resume")
            return

        self.bot.prepare_for_run(paused=True)
        self.bot.publish_status()
        self.bot_thread = threading.Thread(target=self._run_bot_thread, daemon=False)
        self.bot_thread.start()
        self.bridge.push_log("Bot started paused.")

    def _run_bot_thread(self):
        try:
            self.bot.calibrate()
            if self.bot.is_stopped:
                self.bot.capture.close()
                self.bot.publish_status()
                return
            self.bot.run()
        except Exception as exc:
            self.bot.request_stop()
            self.bot.capture.close()
            self.bot.publish_status()
            self.bridge.push_log(f"Bot crashed: {exc}")

    def _stop_bot(self, join: bool = False):
        self.bot.request_stop()
        self.bot.publish_status()
        self.bridge.send_cmd("stop")
        self.bridge.push_log("Stop requested.")
        if join and self.bot_thread and self.bot_thread.is_alive():
            self.bot_thread.join(timeout=5.0)
            if self.bot_thread.is_alive():
                self.bridge.push_log("Bot thread did not stop within 5 seconds.")

    def _shutdown(self):
        self._stop_bot(join=True)
        self._clear_hotkeys()

    def run(self):
        try:
            dpg.show_viewport()
            while dpg.is_dearpygui_running():
                update_dashboard_ui(self.bridge)
                update_logs_ui(self.bridge)
                dpg.render_dearpygui_frame()
        finally:
            self._shutdown()
            dpg.destroy_context()


def _build_theme():
    with dpg.theme() as theme:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 16, 16)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 10, 7)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 10, 10)
            dpg.add_theme_style(dpg.mvStyleVar_ItemInnerSpacing, 8, 6)
            dpg.add_theme_style(dpg.mvStyleVar_IndentSpacing, 22)
            dpg.add_theme_style(dpg.mvStyleVar_ScrollbarSize, 14)
            dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 8)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_GrabRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_TabRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_PopupRounding, 8)
            dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_WindowBorderSize, 1)
            dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 1)

            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (15, 16, 19))
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, (24, 26, 30, 245))
            dpg.add_theme_color(dpg.mvThemeCol_PopupBg, (28, 31, 35))
            dpg.add_theme_color(dpg.mvThemeCol_Border, (58, 63, 70, 180))
            dpg.add_theme_color(dpg.mvThemeCol_BorderShadow, (0, 0, 0, 0))

            dpg.add_theme_color(dpg.mvThemeCol_Header, (36, 66, 70))
            dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, (49, 91, 95))
            dpg.add_theme_color(dpg.mvThemeCol_HeaderActive, (58, 115, 107))
            dpg.add_theme_color(dpg.mvThemeCol_Tab, (27, 30, 34))
            dpg.add_theme_color(dpg.mvThemeCol_TabHovered, (47, 78, 82))
            dpg.add_theme_color(dpg.mvThemeCol_TabActive, (54, 104, 96))
            dpg.add_theme_color(dpg.mvThemeCol_TabUnfocused, (22, 24, 28))
            dpg.add_theme_color(dpg.mvThemeCol_TabUnfocusedActive, (38, 55, 58))

            dpg.add_theme_color(dpg.mvThemeCol_Button, (42, 48, 54))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (58, 84, 85))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (70, 126, 112))
            dpg.add_theme_color(dpg.mvThemeCol_CheckMark, (102, 204, 176))

            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (31, 34, 39))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, (42, 49, 55))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, (47, 72, 70))
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrab, (102, 196, 171))
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrabActive, (135, 220, 195))

            dpg.add_theme_color(dpg.mvThemeCol_Text, (232, 235, 239))
            dpg.add_theme_color(dpg.mvThemeCol_TextDisabled, (137, 144, 152))
            dpg.add_theme_color(dpg.mvThemeCol_PlotLines, (109, 207, 178))
            dpg.add_theme_color(dpg.mvThemeCol_PlotLinesHovered, (151, 226, 204))
    return theme


if __name__ == "__main__":
    gui = FishingGUI()
    gui.run()

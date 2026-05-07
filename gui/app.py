"""DearPyGui application shell for NTE Auto-Fish — glassmorphism rewrite."""
from __future__ import annotations

import ctypes
import threading

import dearpygui.dearpygui as dpg
import keyboard

from config import CFG
from gui.bridge import BotBridge
from gui.pages.dashboard import create_dashboard, update_dashboard_ui
from gui.pages.logs import create_logs, update_logs_ui
from gui.pages.settings import create_settings
from gui.sidebar import create_sidebar, set_active_page
from gui.theme import _FONT_PATH, FONT_SIZES, build_global_theme, set_ui_scale
from main import NTEFishingBot
from screeninfo import get_monitors


def _get_primary_monitor_size() -> tuple[int, int]:
    """Return (width, height) of the primary monitor via Win32."""
    user32 = ctypes.windll.user32
    w = user32.GetSystemMetrics(0)
    h = user32.GetSystemMetrics(1)
    return w, h

APP_TITLE = "NTE Auto-Fish"


class FishingGUI:
    def __init__(self):
        self._enable_hidpi()
        self.bridge = BotBridge()
        self.bot = NTEFishingBot(bridge=self.bridge)
        self.bot_thread: threading.Thread | None = None
        self._bot_lock = threading.Lock()
        self._hotkey_handles: list = []

        self._setup_dpg()
        self._setup_hotkeys()
        self._build_ui()

    def _enable_hidpi(self):
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

    def _setup_dpg(self):
        dpg.create_context()

        # Use pure 1.0 scale to keep base fonts crisp. OS DPI handles display size.
        self._ui_scale = 1.0

        # Font registry — load Segoe UI at scaled sizes
        self._fonts: dict[str, int | None] = {}
        with dpg.font_registry():
            for name, size in FONT_SIZES.items():
                try:
                    # Scale font size at rasterization for crisp text and correct widget layout
                    scaled_size = max(8, int(size * self._ui_scale))
                    self._fonts[name] = dpg.add_font(_FONT_PATH, scaled_size)
                except Exception:
                    self._fonts[name] = None

        dpg.create_viewport(
            title=f"{APP_TITLE} Control Center",
            width=int(960 * self._ui_scale),
            height=int(700 * self._ui_scale),
            min_width=int(800 * self._ui_scale),
            min_height=int(560 * self._ui_scale),
            always_on_top=CFG.always_on_top,
        )
        dpg.setup_dearpygui()

        # Bind global theme (scaled) and body font
        set_ui_scale(self._ui_scale)
        dpg.bind_theme(build_global_theme(self._ui_scale))
        if self._fonts.get("body"):
            dpg.bind_font(self._fonts["body"])

    def _build_ui(self):
        with dpg.window(tag="PrimaryWindow", no_close=True, no_move=True):
            with dpg.group(horizontal=True):
                # Sidebar
                create_sidebar(on_navigate=self._switch_page)

                # Content area
                with dpg.child_window(
                    tag="page_container", width=-1, height=-1,
                    border=False, no_scrollbar=True,
                ):
                    # Dashboard page
                    with dpg.child_window(
                        tag="page_dashboard", width=-1, height=-1,
                        border=False, no_scrollbar=True,
                    ):
                        create_dashboard(
                            self.bridge,
                            on_start=self._start_bot,
                            on_stop=self._stop_bot,
                            on_recalibrate=lambda: self.bridge.send_cmd("recalibrate"),
                        )

                    # Settings page
                    with dpg.child_window(
                        tag="page_settings", width=-1, height=-1,
                        border=False, no_scrollbar=False,
                    ):
                        create_settings(
                            self.bridge,
                            on_hotkeys_changed=self._register_hotkeys,
                        )

                    # Activity page
                    with dpg.child_window(
                        tag="page_logs", width=-1, height=-1,
                        border=False, no_scrollbar=False,
                    ):
                        create_logs(self.bridge)

        dpg.set_primary_window("PrimaryWindow", True)

        # Apply fonts to specific elements
        self._apply_fonts()

        # Start on dashboard
        self._switch_page("dashboard")

    def _apply_fonts(self):
        """Apply sized fonts to specific widgets for typographic hierarchy."""
        font_map = {
            "metric": [
                "state_card_value", "fish_card_value",
                "time_card_value", "fps_card_value",
            ],
            "section": [],
            "caption": [],
        }
        for font_name, tags in font_map.items():
            font = self._fonts.get(font_name)
            if font:
                for tag in tags:
                    if dpg.does_item_exist(tag):
                        dpg.bind_item_font(tag, font)

    def _switch_page(self, page_name: str):
        pages = {
            "dashboard": "page_dashboard",
            "settings": "page_settings",
            "logs": "page_logs",
        }
        for key, tag in pages.items():
            dpg.configure_item(tag, show=(key == page_name))
        set_active_page(page_name)

    # ── Hotkeys ─────────────────────────────────────────────────────────

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

    # ── Bot lifecycle ───────────────────────────────────────────────────

    def _start_bot(self):
        with self._bot_lock:
            if self.bot_thread and self.bot_thread.is_alive():
                if self.bot._stop_flag:
                    self.bridge.push_log(
                        "Bot is still stopping. Wait a moment before starting again."
                    )
                    return
                self.bridge.send_cmd("resume")
                return

            self.bot.prepare_for_run(paused=True)
            self.bot.publish_status()
            self.bot_thread = threading.Thread(target=self._run_bot_thread, daemon=True)
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
            try:
                self.bot.capture.close()
            except Exception:
                pass
            self.bot.publish_status()
            self.bridge.push_log(f"Bot crashed: {exc}")

    def _stop_bot(self, join: bool = False):
        with self._bot_lock:
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

    # ── Viewport positioning ─────────────────────────────────────────

    def _position_viewport_away_from_roi(self):
        """Move the GUI window to the bottom-left corner to avoid overlapping
        the game's ROI regions (button at bottom-right, bar at top-center)."""
        try:
            mon = get_monitors()[CFG.monitor_index]
            vp_w = int(960 * self._ui_scale)
            vp_h = int(700 * self._ui_scale)
            margin = int(50 * self._ui_scale)
            x = mon.x + margin
            y = mon.y + mon.height - vp_h - margin
            dpg.set_viewport_pos([x, y])
        except Exception:
            pass

    # ── Main loop ───────────────────────────────────────────────────────

    def run(self):
        try:
            dpg.show_viewport()
            self._position_viewport_away_from_roi()
            self._start_bot()
            while dpg.is_dearpygui_running():
                update_dashboard_ui(self.bridge)
                update_logs_ui(self.bridge)
                dpg.render_dearpygui_frame()
        finally:
            self._shutdown()
            dpg.destroy_context()


if __name__ == "__main__":
    gui = FishingGUI()
    gui.run()

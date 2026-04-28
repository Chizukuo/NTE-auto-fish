"""
gui/panels/settings.py
设置面板：PID 参数、HSV 颜色阈值、时序参数的实时调节。
所有回调直接修改 CFG 单例。Bot 在下一帧读取时自动生效。
"""
import dearpygui.dearpygui as dpg

from config import CFG
from gui.bridge import BotBridge


def create_settings(bridge: BotBridge):
    with dpg.group():
        with dpg.group(horizontal=True):
            dpg.add_text("Tuning & Configuration", color=(200, 200, 255))
            dpg.add_button(label="Save Settings", callback=lambda: CFG.save(), height=25)
        dpg.add_spacer(height=5)

        # ---- PID ----
        with dpg.collapsing_header(label="PID Controller", default_open=True):
            dpg.add_slider_float(label="Kp", min_value=0.0, max_value=2.0,
                                 default_value=CFG.pid.kp,
                                 callback=lambda s, d: _set(CFG.pid, 'kp', d))
            dpg.add_slider_float(label="Ki", min_value=0.0, max_value=0.5,
                                 default_value=CFG.pid.ki,
                                 callback=lambda s, d: _set(CFG.pid, 'ki', d))
            dpg.add_slider_float(label="Kd", min_value=0.0, max_value=1.0,
                                 default_value=CFG.pid.kd,
                                 callback=lambda s, d: _set(CFG.pid, 'kd', d))
            dpg.add_slider_float(label="Deadband", min_value=0.0, max_value=50.0,
                                 default_value=CFG.pid.deadband,
                                 callback=lambda s, d: _set(CFG.pid, 'deadband', d))
            dpg.add_slider_float(label="Integral Limit", min_value=10.0, max_value=500.0,
                                 default_value=CFG.pid.integral_limit,
                                 callback=lambda s, d: _set(CFG.pid, 'integral_limit', d))

        # ---- HSV ----
        with dpg.collapsing_header(label="HSV Color Thresholds"):
            dpg.add_text("Safe Zone (Cyan/Green)", color=(0, 255, 200))
            dpg.add_slider_intx(label="Lower##sz", size=3, min_value=0, max_value=255,
                                default_value=list(CFG.hsv.safe_zone.lower),
                                callback=lambda s, d: _set(CFG.hsv.safe_zone, 'lower', tuple(d[:3])))
            dpg.add_slider_intx(label="Upper##sz", size=3, min_value=0, max_value=255,
                                default_value=list(CFG.hsv.safe_zone.upper),
                                callback=lambda s, d: _set(CFG.hsv.safe_zone, 'upper', tuple(d[:3])))

            dpg.add_spacer(height=8)
            dpg.add_text("Cursor (Yellow)", color=(255, 255, 0))
            dpg.add_slider_intx(label="Lower##cur", size=3, min_value=0, max_value=255,
                                default_value=list(CFG.hsv.cursor.lower),
                                callback=lambda s, d: _set(CFG.hsv.cursor, 'lower', tuple(d[:3])))
            dpg.add_slider_intx(label="Upper##cur", size=3, min_value=0, max_value=255,
                                default_value=list(CFG.hsv.cursor.upper),
                                callback=lambda s, d: _set(CFG.hsv.cursor, 'upper', tuple(d[:3])))

            dpg.add_spacer(height=8)
            dpg.add_text("Blue Trigger", color=(100, 140, 255))
            dpg.add_slider_intx(label="Lower##bl", size=3, min_value=0, max_value=255,
                                default_value=list(CFG.hsv.blue.lower),
                                callback=lambda s, d: _set(CFG.hsv.blue, 'lower', tuple(d[:3])))
            dpg.add_slider_intx(label="Upper##bl", size=3, min_value=0, max_value=255,
                                default_value=list(CFG.hsv.blue.upper),
                                callback=lambda s, d: _set(CFG.hsv.blue, 'upper', tuple(d[:3])))

        # ---- Timing ----
        with dpg.collapsing_header(label="Timing"):
            dpg.add_slider_float(label="Cast Anim (s)", min_value=0.5, max_value=5.0,
                                 default_value=CFG.timing.cast_animation_secs,
                                 callback=lambda s, d: _set(CFG.timing, 'cast_animation_secs', d))
            dpg.add_slider_float(label="Bite Timeout (s)", min_value=10.0, max_value=120.0,
                                 default_value=CFG.timing.bite_timeout_secs,
                                 callback=lambda s, d: _set(CFG.timing, 'bite_timeout_secs', d))
            dpg.add_input_int(label="Lost Frames", default_value=CFG.timing.lost_frames_threshold,
                              callback=lambda s, d: _set(CFG.timing, 'lost_frames_threshold', d))
            dpg.add_slider_float(label="Result Wait (s)", min_value=0.5, max_value=5.0,
                                 default_value=CFG.timing.result_wait_secs,
                                 callback=lambda s, d: _set(CFG.timing, 'result_wait_secs', d))
            dpg.add_input_int(label="Min Blue Pixels", default_value=CFG.min_blue_pixels,
                              callback=lambda s, d: _set(CFG, 'min_blue_pixels', d))
            dpg.add_checkbox(label="Always on Top", default_value=CFG.always_on_top,
                             callback=lambda s, d: _on_top_changed(d))
            dpg.add_checkbox(label="Debug Mode (Verbose Log & CSV)", default_value=CFG.debug_mode,
                             callback=lambda s, d: _set(CFG, 'debug_mode', d))

        # ---- Hotkeys ----
        with dpg.collapsing_header(label="Global Hotkeys"):
            dpg.add_text("Restart/Pause: Toggle bot running state", color=(200, 200, 200))
            dpg.add_input_text(label="Toggle Bot (e.g. f8)", default_value=CFG.hotkeys.toggle,
                               callback=lambda s, d: _set(CFG.hotkeys, 'toggle', d))
            dpg.add_input_text(label="Stop Bot (e.g. f12)", default_value=CFG.hotkeys.stop,
                               callback=lambda s, d: _set(CFG.hotkeys, 'stop', d))


def _on_top_changed(val):
    CFG.always_on_top = val
    dpg.set_viewport_always_on_top(val)


def _set(obj, attr: str, val):
    """安全地设置属性。统一入口便于后续加日志/验证。"""
    setattr(obj, attr, val)

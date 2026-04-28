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
            dpg.add_text("[ CONFIGURATION HUB ]", color=(100, 200, 255))
            dpg.add_spacer(width=20)
            dpg.add_button(label="SAVE TO DISK", callback=lambda: CFG.save(), height=25)
            dpg.add_button(label="RESET DEFAULTS", callback=lambda: _on_reset(), height=25)
        dpg.add_spacer(height=5)
        dpg.add_separator()
        dpg.add_spacer(height=5)

        # ---- PID ----
        with dpg.collapsing_header(label="PID CONTROLLER TUNING", default_open=True):
            with dpg.group(indent=20):
                dpg.add_text("Fine-tune the movement logic of the fishing cursor.", color=(150, 150, 150))
                dpg.add_slider_float(label="Kp (Proportional)", min_value=0.0, max_value=2.0,
                                     tag="cfg_pid_kp",
                                     default_value=CFG.pid.kp,
                                     callback=lambda s, d: _set(CFG.pid, 'kp', d))
                dpg.add_slider_float(label="Ki (Integral)", min_value=0.0, max_value=0.5,
                                     tag="cfg_pid_ki",
                                     default_value=CFG.pid.ki,
                                     callback=lambda s, d: _set(CFG.pid, 'ki', d))
                dpg.add_slider_float(label="Kd (Derivative)", min_value=0.0, max_value=1.0,
                                     tag="cfg_pid_kd",
                                     default_value=CFG.pid.kd,
                                     callback=lambda s, d: _set(CFG.pid, 'kd', d))
                dpg.add_spacer(height=5)
                dpg.add_slider_float(label="Deadband", min_value=0.0, max_value=50.0,
                                     tag="cfg_pid_deadband",
                                     default_value=CFG.pid.deadband,
                                     callback=lambda s, d: _set(CFG.pid, 'deadband', d))
                dpg.add_checkbox(label="Adaptive PID (Auto-Dampening)",
                                 tag="cfg_pid_adaptive",
                                 default_value=CFG.pid.adaptive,
                                 callback=lambda s, d: _set(CFG.pid, 'adaptive', d))
                dpg.add_slider_float(label="Integral Limit", min_value=10.0, max_value=500.0,
                                     tag="cfg_pid_integral_limit",
                                     default_value=CFG.pid.integral_limit,
                                     callback=lambda s, d: _set(CFG.pid, 'integral_limit', d))

        # ---- HSV ----
        with dpg.collapsing_header(label="VISION & COLOR THRESHOLDS"):
            with dpg.group(indent=20):
                dpg.add_text("Adjust colors for object detection.", color=(150, 150, 150))
                
                with dpg.tree_node(label="Safe Zone (Cyan/Green)", default_open=True):
                    dpg.add_slider_intx(label="Min HSV##sz", size=3, min_value=0, max_value=255,
                                        tag="cfg_hsv_sz_lower",
                                        default_value=list(CFG.hsv.safe_zone.lower),
                                        callback=lambda s, d: _set(CFG.hsv.safe_zone, 'lower', tuple(d[:3])))
                    dpg.add_slider_intx(label="Max HSV##sz", size=3, min_value=0, max_value=255,
                                        tag="cfg_hsv_sz_upper",
                                        default_value=list(CFG.hsv.safe_zone.upper),
                                        callback=lambda s, d: _set(CFG.hsv.safe_zone, 'upper', tuple(d[:3])))

                with dpg.tree_node(label="Cursor (Yellow)", default_open=True):
                    dpg.add_slider_intx(label="Min HSV##cur", size=3, min_value=0, max_value=255,
                                        tag="cfg_hsv_cur_lower",
                                        default_value=list(CFG.hsv.cursor.lower),
                                        callback=lambda s, d: _set(CFG.hsv.cursor, 'lower', tuple(d[:3])))
                    dpg.add_slider_intx(label="Max HSV##cur", size=3, min_value=0, max_value=255,
                                        tag="cfg_hsv_cur_upper",
                                        default_value=list(CFG.hsv.cursor.upper),
                                        callback=lambda s, d: _set(CFG.hsv.cursor, 'upper', tuple(d[:3])))

                with dpg.tree_node(label="Blue Trigger", default_open=False):
                    dpg.add_slider_intx(label="Min HSV##bl", size=3, min_value=0, max_value=255,
                                        tag="cfg_hsv_bl_lower",
                                        default_value=list(CFG.hsv.blue.lower),
                                        callback=lambda s, d: _set(CFG.hsv.blue, 'lower', tuple(d[:3])))
                    dpg.add_slider_intx(label="Max HSV##bl", size=3, min_value=0, max_value=255,
                                        tag="cfg_hsv_bl_upper",
                                        default_value=list(CFG.hsv.blue.upper),
                                        callback=lambda s, d: _set(CFG.hsv.blue, 'upper', tuple(d[:3])))

        # ---- Timing ----
        with dpg.collapsing_header(label="TIMING & AUTOMATION"):
            with dpg.group(indent=20):
                dpg.add_slider_float(label="Cast Animation (s)", min_value=0.5, max_value=5.0,
                                     tag="cfg_timing_cast",
                                     default_value=CFG.timing.cast_animation_secs,
                                     callback=lambda s, d: _set(CFG.timing, 'cast_animation_secs', d))
                dpg.add_slider_float(label="Bite Timeout (s)", min_value=10.0, max_value=120.0,
                                     tag="cfg_timing_bite",
                                     default_value=CFG.timing.bite_timeout_secs,
                                     callback=lambda s, d: _set(CFG.timing, 'bite_timeout_secs', d))
                dpg.add_input_int(label="Lost Frames Threshold", 
                                  tag="cfg_timing_lost",
                                  default_value=CFG.timing.lost_frames_threshold,
                                  callback=lambda s, d: _set(CFG.timing, 'lost_frames_threshold', d))
                dpg.add_slider_float(label="Result Screen Wait (s)", min_value=0.5, max_value=5.0,
                                     tag="cfg_timing_result",
                                     default_value=CFG.timing.result_wait_secs,
                                     callback=lambda s, d: _set(CFG.timing, 'result_wait_secs', d))
                dpg.add_input_int(label="Min Blue Pixels", 
                                  tag="cfg_min_blue",
                                  default_value=CFG.min_blue_pixels,
                                  callback=lambda s, d: _set(CFG, 'min_blue_pixels', d))
                
                dpg.add_spacer(height=5)
                dpg.add_checkbox(label="Keep Window Always on Top", 
                                 tag="cfg_always_on_top",
                                 default_value=CFG.always_on_top,
                                 callback=lambda s, d: _on_top_changed(d))
                dpg.add_checkbox(label="Enable Debug Mode", 
                                 tag="cfg_debug_mode",
                                 default_value=CFG.debug_mode,
                                 callback=lambda s, d: _set(CFG, 'debug_mode', d))

        # ---- Hotkeys ----
        with dpg.collapsing_header(label="GLOBAL HOTKEYS"):
            with dpg.group(indent=20):
                dpg.add_text("Assign system-wide shortcuts to control the bot.", color=(150, 150, 150))
                dpg.add_input_text(label="Toggle Running (Start/Pause)", 
                                   tag="cfg_hotkey_toggle",
                                   default_value=CFG.hotkeys.toggle,
                                   callback=lambda s, d: _set(CFG.hotkeys, 'toggle', d))
                dpg.add_input_text(label="Emergency Stop", 
                                   tag="cfg_hotkey_stop",
                                   default_value=CFG.hotkeys.stop,
                                   callback=lambda s, d: _set(CFG.hotkeys, 'stop', d))


def _on_reset():
    CFG.reset()
    # 刷新所有 GUI 元素的值
    dpg.set_value("cfg_pid_kp", CFG.pid.kp)
    dpg.set_value("cfg_pid_ki", CFG.pid.ki)
    dpg.set_value("cfg_pid_kd", CFG.pid.kd)
    dpg.set_value("cfg_pid_deadband", CFG.pid.deadband)
    dpg.set_value("cfg_pid_adaptive", CFG.pid.adaptive)
    dpg.set_value("cfg_pid_integral_limit", CFG.pid.integral_limit)
    
    dpg.set_value("cfg_hsv_sz_lower", list(CFG.hsv.safe_zone.lower))
    dpg.set_value("cfg_hsv_sz_upper", list(CFG.hsv.safe_zone.upper))
    dpg.set_value("cfg_hsv_cur_lower", list(CFG.hsv.cursor.lower))
    dpg.set_value("cfg_hsv_cur_upper", list(CFG.hsv.cursor.upper))
    dpg.set_value("cfg_hsv_bl_lower", list(CFG.hsv.blue.lower))
    dpg.set_value("cfg_hsv_bl_upper", list(CFG.hsv.blue.upper))
    
    dpg.set_value("cfg_timing_cast", CFG.timing.cast_animation_secs)
    dpg.set_value("cfg_timing_bite", CFG.timing.bite_timeout_secs)
    dpg.set_value("cfg_timing_lost", CFG.timing.lost_frames_threshold)
    dpg.set_value("cfg_timing_result", CFG.timing.result_wait_secs)
    dpg.set_value("cfg_min_blue", CFG.min_blue_pixels)
    
    dpg.set_value("cfg_always_on_top", CFG.always_on_top)
    dpg.set_value("cfg_debug_mode", CFG.debug_mode)
    dpg.set_viewport_always_on_top(CFG.always_on_top)
    
    dpg.set_value("cfg_hotkey_toggle", CFG.hotkeys.toggle)
    dpg.set_value("cfg_hotkey_stop", CFG.hotkeys.stop)


def _on_top_changed(val):
    CFG.always_on_top = val
    dpg.set_viewport_always_on_top(val)


def _set(obj, attr: str, val):
    """安全地设置属性。统一入口便于后续加日志/验证。"""
    setattr(obj, attr, val)

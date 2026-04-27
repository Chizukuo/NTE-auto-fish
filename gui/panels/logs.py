"""
gui/panels/logs.py
日志面板：滚动显示 Bot 推送的日志消息。
"""
import dearpygui.dearpygui as dpg

from gui.bridge import BotBridge

_log_items: list[str] = []


def create_logs(bridge: BotBridge):
    with dpg.group():
        with dpg.group(horizontal=True):
            dpg.add_button(label="Clear", callback=_clear_logs)
            dpg.add_text("", tag="log_count")
        dpg.add_spacer(height=5)
        # 使用 child_window + 动态 add_text 代替 listbox
        # 因为 DPG listbox 的 get_value 返回选中值而非全部 items
        dpg.add_child_window(height=-1, width=-1, tag="log_container",
                             horizontal_scrollbar=True)


def _clear_logs():
    _log_items.clear()
    dpg.delete_item("log_container", children_only=True)
    dpg.set_value("log_count", "")


def update_logs_ui(bridge: BotBridge):
    global _log_items
    new_logs = bridge.drain_logs()
    if not new_logs:
        return

    _log_items.extend(new_logs)

    # 只保留最近 200 条
    if len(_log_items) > 200:
        overflow = len(_log_items) - 200
        _log_items = _log_items[overflow:]
        # 重建整个容器内容（不频繁，只在溢出时）
        dpg.delete_item("log_container", children_only=True)
        for line in _log_items:
            dpg.add_text(line, parent="log_container")
    else:
        # 增量追加
        for line in new_logs:
            dpg.add_text(line, parent="log_container")

    dpg.set_value("log_count", f"({len(_log_items)} entries)")

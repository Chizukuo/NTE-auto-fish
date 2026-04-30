import dearpygui.dearpygui as dpg

from gui.bridge import BotBridge


_log_items: list[str] = []
_MAX_LOG_ITEMS = 300
_MUTED = (140, 148, 157)
_TEXT = (226, 231, 236)
_WARNING = (229, 178, 98)
_DANGER = (224, 104, 108)
_SUCCESS = (112, 214, 186)


def create_logs(bridge: BotBridge):
    with dpg.group():
        with dpg.group(horizontal=True):
            dpg.add_button(label="Clear Logs", width=116, callback=_clear_logs)
            dpg.add_text("0 entries", tag="log_count", color=_MUTED)
        dpg.add_spacer(height=5)
        dpg.add_child_window(
            height=-1,
            width=-1,
            tag="log_container",
            horizontal_scrollbar=True,
        )
        _show_empty_state()


def _clear_logs():
    _log_items.clear()
    dpg.delete_item("log_container", children_only=True)
    dpg.set_value("log_count", "0 entries")
    _show_empty_state()


def update_logs_ui(bridge: BotBridge):
    global _log_items
    new_logs = bridge.drain_logs()
    if not new_logs:
        return

    if dpg.does_item_exist("log_empty"):
        dpg.delete_item("log_empty")

    _log_items.extend(new_logs)
    if len(_log_items) > _MAX_LOG_ITEMS:
        _log_items = _log_items[-_MAX_LOG_ITEMS:]
        dpg.delete_item("log_container", children_only=True)
        for line in _log_items:
            _append_line(line)
    else:
        for line in new_logs:
            _append_line(line)

    dpg.set_value("log_count", f"{len(_log_items)} entries")
    _scroll_to_bottom()


def _append_line(line: str):
    dpg.add_text(line, parent="log_container", color=_line_color(line))


def _show_empty_state():
    dpg.add_text(
        "No activity yet.",
        tag="log_empty",
        parent="log_container",
        color=_MUTED,
    )


def _scroll_to_bottom():
    try:
        dpg.set_y_scroll("log_container", dpg.get_y_scroll_max("log_container"))
    except Exception:
        pass


def _line_color(line: str) -> tuple[int, int, int]:
    text = line.lower()
    if any(word in text for word in ("crashed", "failed", "error")):
        return _DANGER
    if any(word in text for word in ("warning", "timeout", "lost", "missing")):
        return _WARNING
    if any(word in text for word in ("started", "resumed", "hooked", "saved")):
        return _SUCCESS
    return _TEXT

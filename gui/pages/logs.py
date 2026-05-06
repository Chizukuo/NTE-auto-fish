"""Activity page — filter/search toolbar and color-coded log viewer."""
from __future__ import annotations

from collections import deque

import dearpygui.dearpygui as dpg

from gui.bridge import BotBridge
from gui.components import apply_glass_card_theme
from gui.theme import (
    CARD_GAP,
    DANGER,
    SUCCESS,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_VERY_MUTED,
    WARNING,
)

# ---------------------------------------------------------------------------
# Module state
# ---------------------------------------------------------------------------

_log_items: deque[str] = deque(maxlen=300)
_MAX_LOG_ITEMS = 300
_MAX_LINE_LEN = 180

_FILTER_ALL = "All"
_FILTER_ERROR = "Error"
_FILTER_WARNING = "Warning"
_FILTER_SUCCESS = "Success"
_FILTERS = [_FILTER_ALL, _FILTER_ERROR, _FILTER_WARNING, _FILTER_SUCCESS]

_active_filter: str = _FILTER_ALL
_search_query: str = ""
_auto_scroll: bool = True


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def create_logs(bridge: BotBridge):
    global _active_filter, _search_query, _auto_scroll
    _active_filter = _FILTER_ALL
    _search_query = ""
    _auto_scroll = True

    # ── Toolbar ─────────────────────────────────────────────────────────
    with dpg.child_window(
        height=52, tag="log_toolbar", border=True, no_scrollbar=True,
    ):
        apply_glass_card_theme("log_toolbar")
        with dpg.group(horizontal=True):
            dpg.add_combo(
                items=_FILTERS, default_value=_FILTER_ALL, width=120,
                tag="log_filter", callback=_on_filter_changed,
            )
            dpg.add_spacer(width=12)
            dpg.add_input_text(
                hint="Search logs...", width=200,
                tag="log_search", callback=_on_search_changed,
            )
            dpg.add_spacer(width=12)
            dpg.add_text("0 entries", tag="log_count", color=TEXT_MUTED)
            dpg.add_spacer(width=-1)
            dpg.add_checkbox(
                label="Auto-scroll", tag="log_auto_scroll",
                default_value=True, callback=_on_auto_scroll_changed,
            )
            dpg.add_spacer(width=12)
            dpg.add_button(label="Clear", width=80, callback=lambda s, a, u: _clear_logs())

    dpg.add_spacer(height=CARD_GAP)

    # ── Log area ────────────────────────────────────────────────────────
    with dpg.child_window(
        height=-1, width=-1, tag="log_container", border=True,
    ):
        apply_glass_card_theme("log_container")
        _show_empty_state()


def update_logs_ui(bridge: BotBridge):
    new_logs = bridge.drain_logs()
    if not new_logs:
        return

    if dpg.does_item_exist("log_empty"):
        dpg.delete_item("log_empty")

    overflow = len(_log_items) + len(new_logs) - _MAX_LOG_ITEMS
    _log_items.extend(new_logs)
    if overflow > 0:
        _rebuild_log_display()
        return

    for raw in new_logs:
        if _matches_filter(raw) and _matches_search(raw):
            _append_line(raw)

    dpg.set_value("log_count", f"{len(_log_items)} entries")
    if _auto_scroll:
        _scroll_to_bottom()


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------


def _on_filter_changed(sender, value):
    global _active_filter
    _active_filter = value
    _rebuild_log_display()


def _on_search_changed(sender, value):
    global _search_query
    _search_query = value.strip().lower()
    _rebuild_log_display()


def _on_auto_scroll_changed(sender, value):
    global _auto_scroll
    _auto_scroll = value


def _matches_filter(line: str) -> bool:
    if _active_filter == _FILTER_ALL:
        return True
    text = line.lower()
    if _active_filter == _FILTER_ERROR:
        return any(w in text for w in ("crashed", "failed", "error"))
    if _active_filter == _FILTER_WARNING:
        return any(w in text for w in ("warning", "timeout", "lost", "missing"))
    if _active_filter == _FILTER_SUCCESS:
        return any(w in text for w in ("started", "resumed", "hooked", "saved"))
    return True


def _matches_search(line: str) -> bool:
    if not _search_query:
        return True
    return _search_query in line.lower()


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------


def _rebuild_log_display():
    dpg.delete_item("log_container", children_only=True)
    if not _log_items:
        _show_empty_state()
        return
    count = 0
    for raw in _log_items:
        if _matches_filter(raw) and _matches_search(raw):
            _append_line(raw)
            count += 1
    if count == 0:
        _show_empty_state()
    dpg.set_value("log_count", f"{len(_log_items)} entries")
    if _auto_scroll:
        _scroll_to_bottom()


def _append_line(raw: str):
    display = raw if len(raw) <= _MAX_LINE_LEN else raw[:_MAX_LINE_LEN] + "..."
    color = _line_color(raw)
    dpg.add_text(display, parent="log_container", color=color)


def _clear_logs():
    _log_items.clear()
    dpg.delete_item("log_container", children_only=True)
    dpg.set_value("log_count", "0 entries")
    _show_empty_state()


def _show_empty_state():
    dpg.add_text(
        "No activity yet.",
        tag="log_empty",
        parent="log_container",
        color=TEXT_VERY_MUTED,
    )


def _scroll_to_bottom():
    try:
        dpg.set_y_scroll("log_container", dpg.get_y_scroll_max("log_container"))
    except Exception:
        pass


def _line_color(line: str) -> tuple[int, int, int]:
    text = line.lower()
    if any(word in text for word in ("crashed", "failed", "error")):
        return DANGER
    if any(word in text for word in ("warning", "timeout", "lost", "missing")):
        return WARNING
    if any(word in text for word in ("started", "resumed", "hooked", "saved")):
        return SUCCESS
    return TEXT_PRIMARY

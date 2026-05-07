"""Left sidebar navigation panel."""
from __future__ import annotations

from typing import Callable

import dearpygui.dearpygui as dpg

from gui.theme import (
    ACCENT,
    GLASS_HIGHLIGHT,
    GLASS_HIGHLIGHT2,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_VERY_MUTED,
    _ui_scale as _s,
    build_nav_item_theme,
    build_sidebar_theme,
    get_sidebar_width,
)

# ---------------------------------------------------------------------------
# Navigation definition
# ---------------------------------------------------------------------------

NAV_PAGES = [
    ("dashboard", "Dashboard"),
    ("settings",  "Settings"),
    ("logs",      "Activity"),
]

_active_page: str = "dashboard"
_nav_tags: dict[str, dict] = {}

# Cached themes
_sidebar_theme: int | None = None
_nav_active_theme: int | None = None
_nav_inactive_theme: int | None = None


def _ensure_themes():
    global _sidebar_theme, _nav_active_theme, _nav_inactive_theme
    if _sidebar_theme is None:
        _sidebar_theme = build_sidebar_theme()
        _nav_active_theme = build_nav_item_theme(active=True)
        _nav_inactive_theme = build_nav_item_theme(active=False)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def create_sidebar(on_navigate: Callable[[str], None]):
    """Build the sidebar inside the current parent group."""
    _ensure_themes()

    s = _s
    sidebar_w = get_sidebar_width()
    margin = int(18 * s)
    with dpg.child_window(
        width=sidebar_w, height=-1, tag="sidebar",
        border=False, no_scrollbar=True,
    ):
        dpg.bind_item_theme("sidebar", _sidebar_theme)

        # App title area
        dpg.add_spacer(height=int(20 * s))
        with dpg.group(horizontal=True):
            dpg.add_spacer(width=margin)
            dpg.add_text("NTE Auto-Fish", color=TEXT_PRIMARY)
        with dpg.group(horizontal=True):
            dpg.add_spacer(width=margin)
            dpg.add_text("Control Center", color=TEXT_VERY_MUTED)

        dpg.add_spacer(height=int(8 * s))
        with dpg.group(horizontal=True):
            dpg.add_spacer(width=margin)
            dpg.add_separator()
        dpg.add_spacer(height=int(16 * s))

        # Navigation items
        for name, label in NAV_PAGES:
            _create_nav_item(name, label, on_navigate)

        # Bottom area — push to bottom
        dpg.add_spacer(height=-1)

        # Hotkey hints at bottom
        with dpg.group(horizontal=True):
            dpg.add_spacer(width=margin)
            dpg.add_text("F8 Toggle  |  F12 Stop", color=TEXT_VERY_MUTED)
        dpg.add_spacer(height=int(16 * s))


def set_active_page(page_name: str):
    """Update sidebar visual state to reflect the active page."""
    global _active_page
    if page_name == _active_page:
        return

    # Deactivate old
    if _active_page in _nav_tags:
        tags = _nav_tags[_active_page]
        dpg.bind_item_theme(tags["btn"], _nav_inactive_theme)
        dpg.configure_item(tags["indicator"], color=(0, 0, 0, 0), fill=(0, 0, 0, 0))

    # Activate new
    if page_name in _nav_tags:
        tags = _nav_tags[page_name]
        dpg.bind_item_theme(tags["btn"], _nav_active_theme)
        dpg.configure_item(tags["indicator"], color=ACCENT, fill=ACCENT)

    _active_page = page_name


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------


def _create_nav_item(name: str, label: str, on_navigate: Callable[[str], None]):
    """Create a single sidebar nav item with accent indicator bar."""
    is_active = (name == _active_page)
    btn_tag = f"nav_btn_{name}"
    ind_tag = f"nav_ind_{name}"

    nav_h = int(40 * _s)
    bar_w = max(3, int(4 * _s))
    sidebar_w = get_sidebar_width()
    with dpg.group(horizontal=True):
        # Accent indicator bar
        with dpg.drawlist(width=bar_w, height=nav_h, tag=f"nav_ind_dl_{name}"):
            if is_active:
                dpg.draw_rectangle(
                    (0, 0), (bar_w, nav_h), color=ACCENT, fill=ACCENT, tag=ind_tag,
                )
            else:
                dpg.draw_rectangle(
                    (0, 0), (bar_w, nav_h), color=(0, 0, 0, 0), fill=(0, 0, 0, 0), tag=ind_tag,
                )

        # Nav button
        dpg.add_button(
            label=f"  {label}",
            tag=btn_tag,
            width=sidebar_w - int(24 * _s),
            height=nav_h,
            callback=lambda s, a, u: _navigate(name, on_navigate),
        )
        dpg.bind_item_theme(btn_tag, _nav_active_theme if is_active else _nav_inactive_theme)

    _nav_tags[name] = {"btn": btn_tag, "indicator": ind_tag}


def _navigate(page_name: str, on_navigate: Callable[[str], None]):
    set_active_page(page_name)
    on_navigate(page_name)

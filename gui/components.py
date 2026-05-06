"""Reusable widget factories for the glassmorphism UI."""
from __future__ import annotations

from typing import Callable

import dearpygui.dearpygui as dpg

from gui.theme import (
    ACCENT,
    ACCENT_BLUE,
    BORDER_SUBTLE,
    BUTTON_ROUNDING,
    CARD_BG,
    CARD_ROUNDING,
    GLASS_HIGHLIGHT,
    GLASS_HIGHLIGHT2,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_VERY_MUTED,
    build_button_theme,
    build_glass_card_theme,
)

# ---------------------------------------------------------------------------
# Cached themes (lazy-init)
# ---------------------------------------------------------------------------

_glass_card_theme: int | None = None
_button_themes: dict[str, int] = {}


def _ensure_themes():
    global _glass_card_theme
    if _glass_card_theme is None:
        _glass_card_theme = build_glass_card_theme()


def _get_button_theme(variant: str) -> int:
    if variant not in _button_themes:
        _button_themes[variant] = build_button_theme(variant)
    return _button_themes[variant]


# ---------------------------------------------------------------------------
# Glass card helpers
# ---------------------------------------------------------------------------


def apply_glass_card_theme(tag: str | int):
    """Bind the glass card theme to an existing child_window."""
    _ensure_themes()
    dpg.bind_item_theme(tag, _glass_card_theme)


def styled_button(
    label: str,
    tag: str,
    callback: Callable | None = None,
    variant: str = "neutral",
    width: int = 90,
    height: int = 34,
):
    """Create a button with the appropriate variant theme."""
    dpg.add_button(
        label=label, tag=tag, width=width, height=height, callback=callback,
    )
    dpg.bind_item_theme(tag, _get_button_theme(variant))


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------


def section_header(text: str, color: tuple = ACCENT):
    """Accent-colored section title."""
    dpg.add_text(text, color=color)
    dpg.add_spacer(height=8)


def caption_text(text: str):
    """Muted caption text."""
    dpg.add_text(text, color=TEXT_VERY_MUTED)


def metric_row(label: str, value_tag: str, default: str = "N/A"):
    """Horizontal label + value for telemetry-style readouts."""
    with dpg.group(horizontal=True):
        dpg.add_text(label, color=TEXT_MUTED)
        dpg.add_spacer(width=8)
        dpg.add_text(default, tag=value_tag, color=TEXT_PRIMARY)


# ---------------------------------------------------------------------------
# HSV editor
# ---------------------------------------------------------------------------


def hsv_editor(prefix: str, hsv_range, label: str | None = None, default_open: bool = True):
    """HSV range editor with Min/Max sliders and a live color preview swatch."""
    if label is None:
        label = f"{prefix.split('_')[-1].upper()} HSV"
    with dpg.tree_node(label=label, default_open=default_open):
        with dpg.group(horizontal=True):
            with dpg.group():
                dpg.add_slider_intx(
                    label="Min", size=3, min_value=0, max_value=255,
                    width=-1, tag=f"{prefix}_lower",
                    default_value=list(hsv_range.lower),
                    callback=lambda s, d: _on_hsv_changed(prefix, hsv_range, "lower", d),
                )
                dpg.add_slider_intx(
                    label="Max", size=3, min_value=0, max_value=255,
                    width=-1, tag=f"{prefix}_upper",
                    default_value=list(hsv_range.upper),
                    callback=lambda s, d: _on_hsv_changed(prefix, hsv_range, "upper", d),
                )
            dpg.add_spacer(width=12)
            _hsv_preview(prefix, hsv_range)


def _hsv_preview(prefix: str, hsv_range):
    center = tuple((a + b) // 2 for a, b in zip(hsv_range.lower, hsv_range.upper))
    rgb = _hsv_to_rgb(*center)
    with dpg.drawlist(width=48, height=48, tag=f"{prefix}_preview"):
        dpg.draw_rectangle(
            (2, 2), (46, 46), color=rgb, fill=rgb,
            rounding=6, tag=f"{prefix}_swatch",
        )


def _on_hsv_changed(prefix: str, hsv_range, attr: str, value):
    setattr(hsv_range, attr, tuple(value[:3]))
    _update_hsv_preview(prefix, hsv_range)


def _update_hsv_preview(prefix: str, hsv_range):
    center = tuple((a + b) // 2 for a, b in zip(hsv_range.lower, hsv_range.upper))
    rgb = _hsv_to_rgb(*center)
    try:
        dpg.configure_item(f"{prefix}_swatch", color=rgb, fill=rgb)
    except Exception:
        pass


def _hsv_to_rgb(h: int, s: int, v: int) -> tuple[int, int, int]:
    """Convert OpenCV HSV (H:0-179, S:0-255, V:0-255) to RGB (0-255)."""
    h_i = h * 6 // 180
    f = (h * 6 / 180.0) - h_i
    p = round(v * (255 - s) / 255)
    q = round(v * (255 - f * s) / 255)
    t = round(v * (255 - (1 - f) * s) / 255)
    if h_i == 0:
        return (v, t, p)
    if h_i == 1:
        return (q, v, p)
    if h_i == 2:
        return (p, v, t)
    if h_i == 3:
        return (p, q, v)
    if h_i == 4:
        return (t, p, v)
    return (v, p, q)


# Public alias for settings page refresh
def update_hsv_preview(prefix: str, hsv_range):
    _update_hsv_preview(prefix, hsv_range)

"""Design system for the NTE Auto-Fish glassmorphism UI."""
import dearpygui.dearpygui as dpg

# ---------------------------------------------------------------------------
# Color palette — Glassmorphism Dark
# ---------------------------------------------------------------------------

# Backgrounds
WINDOW_BG = (15, 17, 26, 255)
CARD_BG = (22, 24, 34, 210)
CARD_BG_ALT = (26, 28, 40, 200)
SIDEBAR_BG = (15, 17, 26, 245)
INPUT_BG = (30, 32, 44, 255)
INPUT_BG_HOVER = (42, 46, 60, 255)
INPUT_BG_ACTIVE = (50, 56, 75, 255)
POPUP_BG = (28, 30, 44, 250)

# Glass highlights
GLASS_HIGHLIGHT = (255, 255, 255, 12)
GLASS_HIGHLIGHT2 = (255, 255, 255, 20)

# Borders
BORDER_SUBTLE = (255, 255, 255, 15)
BORDER_LIGHT = (255, 255, 255, 25)

# Accent
ACCENT = (14, 165, 233, 255)       # Sky blue
ACCENT_HOVER = (56, 189, 248, 255) # Lighter sky blue
ACCENT_ACTIVE = (2, 132, 199, 255) # Deeper sky blue
ACCENT_BLUE = (139, 92, 246, 255)  # Violet

# Text
TEXT_PRIMARY = (248, 250, 252, 255)   # Slate 50
TEXT_MUTED = (148, 163, 184, 255)     # Slate 400
TEXT_VERY_MUTED = (100, 116, 139, 255)# Slate 500

# Semantic
SUCCESS = (16, 185, 129, 255)
WARNING = (245, 158, 11, 255)
DANGER = (239, 68, 68, 255)

# Button variants
BTN_PRIMARY = (14, 165, 233, 255)
BTN_PRIMARY_HOVER = (56, 189, 248, 255)
BTN_PRIMARY_ACTIVE = (2, 132, 199, 255)
BTN_DANGER = (239, 68, 68, 255)
BTN_DANGER_HOVER = (248, 113, 113, 255)
BTN_DANGER_ACTIVE = (220, 38, 38, 255)
BTN_WARNING = (245, 158, 11, 255)
BTN_WARNING_HOVER = (251, 191, 36, 255)
BTN_WARNING_ACTIVE = (217, 119, 6, 255)
BTN_NEUTRAL = (51, 65, 85, 255)
BTN_NEUTRAL_HOVER = (71, 85, 105, 255)
BTN_NEUTRAL_ACTIVE = (30, 41, 59, 255)

# Plot
PLOT_BG = (15, 17, 26, 255)
PLOT_GRID = (30, 34, 48, 255)
PLOT_LINE = (14, 165, 233, 255)

# Visualizer
VIS_TRACK = (22, 24, 34, 255)
VIS_SAFE_ZONE = (16, 185, 129, 60)
VIS_SAFE_ZONE_BD = (16, 185, 129, 180)
VIS_CURSOR = (245, 158, 11, 255)
VIS_CURSOR_DOT = (253, 230, 138, 255)

# State indicator colors
STATE_RUNNING = (16, 185, 129)
STATE_RUNNING_HOVER = (52, 211, 153)
STATE_RUNNING_ACTIVE = (5, 150, 105)
STATE_PAUSED = (245, 158, 11)
STATE_PAUSED_HOVER = (251, 191, 36)
STATE_PAUSED_ACTIVE = (217, 119, 6)
STATE_STOPPED = (239, 68, 68)
STATE_STOPPED_HOVER = (248, 113, 113)
STATE_STOPPED_ACTIVE = (220, 38, 38)

# ---------------------------------------------------------------------------
# Spacing tokens (design-time values; scaled at runtime via _ui_scale)
# ---------------------------------------------------------------------------

CARD_PADDING = 16
CARD_GAP = 12
SECTION_GAP = 16
CARD_ROUNDING = 12
INPUT_ROUNDING = 8
BUTTON_ROUNDING = 6
SIDEBAR_WIDTH = 180

import ctypes

def _compute_initial_scale() -> float:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    # We maintain 1.0 scale to keep crisp 16px fonts and a stable layout.
    # OS DPI scaling will handle high-DPI sizing correctly.
    return 1.0

_ui_scale: float = _compute_initial_scale()

def set_ui_scale(scale: float) -> None:
    """Set the runtime UI scale factor (called once during app startup)."""
    global _ui_scale
    _ui_scale = max(0.5, min(scale, 1.0))


def get_sidebar_width() -> int:
    """Return sidebar width scaled for the current screen resolution."""
    return int(SIDEBAR_WIDTH * _ui_scale)

# ---------------------------------------------------------------------------
# Font paths & sizes
# ---------------------------------------------------------------------------

_FONT_PATH = "C:/Windows/Fonts/segoeui.ttf"
FONT_SIZES = {
    "caption": 12,
    "body": 14,
    "section": 16,
    "title": 20,
    "metric": 24,
}

# ---------------------------------------------------------------------------
# Theme builders
# ---------------------------------------------------------------------------


def build_global_theme(scale: float = 1.0) -> int:
    """Create the app-wide glassmorphism dark theme."""
    with dpg.theme() as theme:
        with dpg.theme_component(dpg.mvAll):
            # Spacing (scaled for different screen resolutions)
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, CARD_PADDING * scale, CARD_PADDING * scale)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 10 * scale, 6 * scale)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 12 * scale, 10 * scale)
            dpg.add_theme_style(dpg.mvStyleVar_ItemInnerSpacing, 8 * scale, 6 * scale)
            dpg.add_theme_style(dpg.mvStyleVar_IndentSpacing, 22 * scale)
            dpg.add_theme_style(dpg.mvStyleVar_ScrollbarSize, max(6, 10 * scale))
            dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, CARD_ROUNDING * scale)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, INPUT_ROUNDING * scale)
            dpg.add_theme_style(dpg.mvStyleVar_GrabRounding, INPUT_ROUNDING * scale)
            dpg.add_theme_style(dpg.mvStyleVar_PopupRounding, CARD_ROUNDING * scale)
            dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, CARD_ROUNDING * scale)
            dpg.add_theme_style(dpg.mvStyleVar_WindowBorderSize, 0)
            dpg.add_theme_style(dpg.mvStyleVar_ChildBorderSize, 1)
            dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 0)

            # Window / child / popup
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, WINDOW_BG)
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, CARD_BG)
            dpg.add_theme_color(dpg.mvThemeCol_PopupBg, POPUP_BG)
            dpg.add_theme_color(dpg.mvThemeCol_Border, BORDER_SUBTLE)
            dpg.add_theme_color(dpg.mvThemeCol_BorderShadow, (0, 0, 0, 0))

            # Header / tab (not used in sidebar design, but set for completeness)
            dpg.add_theme_color(dpg.mvThemeCol_Header, (40, 44, 52, 200))
            dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, (50, 60, 70, 220))
            dpg.add_theme_color(dpg.mvThemeCol_HeaderActive, (60, 75, 85, 240))
            dpg.add_theme_color(dpg.mvThemeCol_Tab, (28, 30, 36, 200))
            dpg.add_theme_color(dpg.mvThemeCol_TabHovered, (40, 48, 56, 220))
            dpg.add_theme_color(dpg.mvThemeCol_TabActive, ACCENT)

            # Buttons
            dpg.add_theme_color(dpg.mvThemeCol_Button, BTN_NEUTRAL)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, BTN_NEUTRAL_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, BTN_NEUTRAL_ACTIVE)
            dpg.add_theme_color(dpg.mvThemeCol_CheckMark, ACCENT)

            # Inputs
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, INPUT_BG)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, INPUT_BG_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, INPUT_BG_ACTIVE)
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrab, ACCENT)
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrabActive, ACCENT_HOVER)

            # Text
            dpg.add_theme_color(dpg.mvThemeCol_Text, TEXT_PRIMARY)
            dpg.add_theme_color(dpg.mvThemeCol_TextDisabled, TEXT_VERY_MUTED)

            # Scrollbar
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarBg, (18, 18, 22, 0))
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrab, (60, 64, 72, 160))
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabHovered, (80, 86, 96, 200))
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabActive, (100, 108, 120, 240))

            # Plot
            dpg.add_theme_color(dpg.mvThemeCol_PlotLines, PLOT_LINE)
            dpg.add_theme_color(dpg.mvThemeCol_PlotLinesHovered, ACCENT_HOVER)

            # Separator
            dpg.add_theme_color(dpg.mvThemeCol_Separator, BORDER_SUBTLE)
            dpg.add_theme_color(dpg.mvThemeCol_SeparatorHovered, BORDER_LIGHT)
    return theme


def build_glass_card_theme(
    bg_color: tuple = CARD_BG,
    border_color: tuple = BORDER_SUBTLE,
) -> int:
    """Per-item theme for child_window glass cards."""
    s = _ui_scale
    with dpg.theme() as theme:
        with dpg.theme_component(dpg.mvChildWindow):
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, bg_color)
            dpg.add_theme_color(dpg.mvThemeCol_Border, border_color)
            dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, CARD_ROUNDING * s)
            dpg.add_theme_style(dpg.mvStyleVar_ChildBorderSize, 1)
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, CARD_PADDING * s, CARD_PADDING * s)
    return theme


def build_sidebar_theme() -> int:
    """Theme for the sidebar child_window."""
    with dpg.theme() as theme:
        with dpg.theme_component(dpg.mvChildWindow):
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, SIDEBAR_BG)
            dpg.add_theme_color(dpg.mvThemeCol_Border, BORDER_SUBTLE)
            dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 0)
            dpg.add_theme_style(dpg.mvStyleVar_ChildBorderSize, 0)
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 0, 0)
    return theme


def build_nav_item_theme(active: bool = False) -> int:
    """Theme for sidebar navigation buttons."""
    with dpg.theme() as theme:
        with dpg.theme_component(dpg.mvButton):
            if active:
                dpg.add_theme_color(dpg.mvThemeCol_Button, GLASS_HIGHLIGHT2)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, GLASS_HIGHLIGHT2)
            else:
                dpg.add_theme_color(dpg.mvThemeCol_Button, (0, 0, 0, 0))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, GLASS_HIGHLIGHT)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, GLASS_HIGHLIGHT2)
            dpg.add_theme_color(dpg.mvThemeCol_Text, TEXT_PRIMARY if active else TEXT_MUTED)
            dpg.add_theme_style(dpg.mvStyleVar_ButtonTextAlign, 0, 0.5)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 0)
    return theme


def build_settings_cat_theme(active: bool = False) -> int:
    """Theme for settings category buttons."""
    s = _ui_scale
    with dpg.theme() as theme:
        with dpg.theme_component(dpg.mvButton):
            if active:
                dpg.add_theme_color(dpg.mvThemeCol_Button, GLASS_HIGHLIGHT2)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, GLASS_HIGHLIGHT2)
            else:
                dpg.add_theme_color(dpg.mvThemeCol_Button, (0, 0, 0, 0))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, GLASS_HIGHLIGHT)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, GLASS_HIGHLIGHT2)
            dpg.add_theme_color(dpg.mvThemeCol_Text, TEXT_PRIMARY if active else TEXT_MUTED)
            dpg.add_theme_style(dpg.mvStyleVar_ButtonTextAlign, 0, 0.5)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 6 * s)
    return theme


def build_button_theme(variant: str) -> int:
    """Create a button theme for the given variant: primary/danger/warning/neutral."""
    s = _ui_scale
    colors = {
        "primary": (BTN_PRIMARY, BTN_PRIMARY_HOVER, BTN_PRIMARY_ACTIVE),
        "danger": (BTN_DANGER, BTN_DANGER_HOVER, BTN_DANGER_ACTIVE),
        "warning": (BTN_WARNING, BTN_WARNING_HOVER, BTN_WARNING_ACTIVE),
        "neutral": (BTN_NEUTRAL, BTN_NEUTRAL_HOVER, BTN_NEUTRAL_ACTIVE),
    }
    bg, hovered, active = colors.get(variant, colors["neutral"])
    with dpg.theme() as theme:
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, bg)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, hovered)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, active)
            dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255, 255))
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, BUTTON_ROUNDING * s)
    return theme


def build_card_no_border_theme() -> int:
    """Transparent container card with no border — used as a layout wrapper."""
    with dpg.theme() as theme:
        with dpg.theme_component(dpg.mvChildWindow):
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, (0, 0, 0, 0))
            dpg.add_theme_color(dpg.mvThemeCol_Border, (0, 0, 0, 0))
            dpg.add_theme_style(dpg.mvStyleVar_ChildBorderSize, 0)
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 0, 0)
    return theme

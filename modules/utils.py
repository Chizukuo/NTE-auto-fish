"""Shared utilities for NTE Auto-Fish."""
import ctypes
import logging
import os
import sys


def app_dir() -> str:
    """Return the application root directory."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def bundled_path(*parts: str) -> str:
    """Return path to a bundled resource (works with PyInstaller --onefile)."""
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


APP_DIR = app_dir()
log = logging.getLogger("NTEFish")


def get_version() -> str:
    """Read version from version.txt bundled with the application."""
    v_path = bundled_path("version.txt")
    if os.path.exists(v_path):
        try:
            with open(v_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except OSError:
            log.debug("Failed to read version file: %s", v_path, exc_info=True)
    return "0.0.0"


VERSION = get_version()

# Shown when the bot lacks the admin rights many games require for input.
ELEVATION_WARNING = (
    "Not running as administrator. If the game runs elevated (NTE and many "
    "games do), key inputs (Pull Left/Right) will NOT register even though the "
    "on-screen tracker works. Re-launch with run.bat / start_gui.bat (these "
    "auto-elevate) or right-click the launcher and choose 'Run as administrator'."
)


def is_elevated() -> bool:
    """Return True if the process has administrator privileges.

    Windows blocks synthetic input (SendInput) from a lower integrity level to
    an elevated window, so a non-elevated bot can see the screen but cannot
    control an elevated game. Non-Windows platforms report True (not applicable).
    """
    if os.name != "nt":
        return True
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        log.debug("IsUserAnAdmin check failed; assuming not elevated.", exc_info=True)
        return False

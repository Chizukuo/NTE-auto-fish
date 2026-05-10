"""Shared utilities for NTE Auto-Fish."""
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


def get_version() -> str:
    """Read version from version.txt bundled with the application."""
    v_path = bundled_path("version.txt")
    if os.path.exists(v_path):
        try:
            with open(v_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            pass
    return "0.0.0"


VERSION = get_version()

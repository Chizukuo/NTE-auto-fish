"""Shared utilities for NTE Auto-Fish."""
import os
import sys


def app_dir() -> str:
    """Return the application root directory."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


APP_DIR = app_dir()

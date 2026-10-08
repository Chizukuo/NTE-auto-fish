"""Locate the game window and return its client area in screen coordinates."""
import ctypes
import logging
import os
from ctypes import wintypes
from typing import NamedTuple, Optional, Sequence

log = logging.getLogger("NTEFish")

_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


class WindowRect(NamedTuple):
    hwnd: int
    left: int
    top: int
    width: int
    height: int


def _process_name(pid: int) -> str:
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(1024)
        size = wintypes.DWORD(len(buf))
        if kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            return os.path.basename(buf.value)
        return ""
    finally:
        kernel32.CloseHandle(handle)


def _client_rect(hwnd: int) -> Optional[WindowRect]:
    user32 = ctypes.windll.user32
    rect = wintypes.RECT()
    if not user32.GetClientRect(hwnd, ctypes.byref(rect)):
        return None
    origin = wintypes.POINT(0, 0)
    if not user32.ClientToScreen(hwnd, ctypes.byref(origin)):
        return None
    width, height = rect.right - rect.left, rect.bottom - rect.top
    if width <= 0 or height <= 0:
        return None
    return WindowRect(hwnd, origin.x, origin.y, width, height)


def find_game_window(process_names: Sequence[str]) -> Optional[WindowRect]:
    """Return the largest visible window owned by one of *process_names*."""
    if os.name != "nt":
        return None
    user32 = ctypes.windll.user32
    wanted = {name.lower() for name in process_names}
    found: list[WindowRect] = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def _enum(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd):
            return True
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if _process_name(pid.value).lower() in wanted:
            rect = _client_rect(hwnd)
            if rect:
                found.append(rect)
        return True

    try:
        user32.EnumWindows(_enum, 0)
    except Exception:
        log.debug("EnumWindows failed.", exc_info=True)
        return None
    if not found:
        return None
    return max(found, key=lambda r: r.width * r.height)


def focus_window(hwnd: int) -> None:
    try:
        ctypes.windll.user32.SetForegroundWindow(hwnd)
    except Exception:
        log.debug("SetForegroundWindow failed.", exc_info=True)

"""
Screen capture and input helpers.

CaptureModule uses mss to grab BGR frames from screen regions. InputModule
wraps pydirectinput and tracks held keys so state changes can release them.
"""
import time

import mss
import numpy as np
import pydirectinput

# pydirectinput's default pause is too slow for the control loop.
pydirectinput.PAUSE = 0.0


class CaptureModule:
    """
    Lazily creates the mss instance on the thread that first captures frames.
    """

    def __init__(self) -> None:
        self._sct = None

    def _get_sct(self):
        if self._sct is None:
            self._sct = mss.mss()
        return self._sct

    def grab_bgr(self, roi: dict) -> np.ndarray:
        """
        Capture an ROI and return a contiguous BGR uint8 array.

        mss returns BGRA. Keeping alpha would break HSV conversion, so the
        alpha channel is removed here.
        """
        raw = self._get_sct().grab(roi)
        return np.ascontiguousarray(np.array(raw)[..., :3])

    def grab_full_screen(self) -> np.ndarray:
        """Capture the primary monitor for cold-start calibration."""
        sct = self._get_sct()
        return self.grab_bgr(sct.monitors[1])

    def get_screen_size(self) -> tuple[int, int]:
        """Return the primary monitor size as (width, height)."""
        sct = self._get_sct()
        m = sct.monitors[1]
        return m["width"], m["height"]

    def close(self) -> None:
        if self._sct is None:
            return
        try:
            self._sct.close()
        finally:
            self._sct = None


class InputModule:
    """
    Lightweight pydirectinput wrapper that tracks held keys.
    """

    def __init__(self) -> None:
        self._held: set[str] = set()

    def press(self, key: str, duration: float = 0.05) -> None:
        """Press and release a key without changing the held-key set."""
        pydirectinput.keyDown(key)
        time.sleep(duration)
        pydirectinput.keyUp(key)

    def hold(self, key: str) -> None:
        """Keep a key held down."""
        pydirectinput.keyDown(key)
        self._held.add(key)

    def release(self, key: str) -> None:
        """Release a key if this wrapper currently tracks it as held."""
        if key in self._held:
            pydirectinput.keyUp(key)
            self._held.discard(key)

    def release_all(self) -> None:
        """Release all tracked held keys."""
        for key in list(self._held):
            pydirectinput.keyUp(key)
        self._held.clear()

    def click(self, x: int, y: int) -> None:
        """Click a screen coordinate."""
        pydirectinput.click(x, y)

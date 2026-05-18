"""
Screen capture and input helpers.

CaptureModule uses mss to grab BGR frames from screen regions. InputModule
wraps pydirectinput and tracks held keys so state changes can release them.
"""
import logging
import threading
import time
from random import SystemRandom
from typing import Optional

import mss
import numpy as np
import pydirectinput

# pydirectinput's default pause is too slow for the control loop.
pydirectinput.PAUSE = 0.0
log = logging.getLogger("NTEFish")
_RNG = SystemRandom()


class CaptureModule:
    """
    Lazily creates the mss instance on the thread that first captures frames.
    """

    def __init__(self) -> None:
        self._sct = None
        self._sct_lock = threading.Lock()

    def _get_sct(self):
        if self._sct is None:
            with self._sct_lock:
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
    Thread-safe: all held-key mutations are guarded by a lock.
    """

    def __init__(self) -> None:
        self._held: set[str] = set()
        self._lock = threading.Lock()

    def press(self, key: str, duration: float = 0.05) -> None:
        """Press and release a key without changing the held-key set."""
        pydirectinput.keyDown(key)
        try:
            time.sleep(duration)
        finally:
            pydirectinput.keyUp(key)

    def hold(self, key: str) -> None:
        """Keep a key held down."""
        with self._lock:
            self._held.add(key)
        try:
            pydirectinput.keyDown(key)
        except Exception:
            with self._lock:
                self._held.discard(key)
            raise

    def release(self, key: str) -> None:
        """Release a key if this wrapper currently tracks it as held."""
        with self._lock:
            if key in self._held:
                pydirectinput.keyUp(key)
                self._held.discard(key)

    def pulse_hold(
        self, key: str, hold_secs: float, release_secs: float,
        stop_event: Optional[threading.Event] = None,
    ) -> None:
        """Hold a key for hold_secs, then release for release_secs.

        Used for humanized pulsing during STRUGGLING state. The key is
        tracked in _held during the hold phase so release_all() can
        clean it up if the bot stops mid-pulse.  Pass *stop_event* to
        make the sleeps interruptible.
        """
        wait = stop_event.wait if stop_event else time.sleep
        with self._lock:
            self._held.add(key)
        try:
            pydirectinput.keyDown(key)
            wait(timeout=hold_secs)
        finally:
            pydirectinput.keyUp(key)
            with self._lock:
                self._held.discard(key)
        if release_secs > 0 and (stop_event is None or not stop_event.is_set()):
            wait(timeout=release_secs)

    def release_all(self) -> None:
        """Release all tracked held keys."""
        with self._lock:
            keys = list(self._held)
            self._held.clear()
        for key in keys:
            try:
                pydirectinput.keyUp(key)
            except Exception:
                log.debug("Failed to release key '%s' in release_all.", key, exc_info=True)

    def click(self, x: int, y: int) -> None:
        """Click a screen coordinate."""
        pydirectinput.click(x, y)

    def humanized_move(self, x: int, y: int, amp: int = 150, d_min: float = 0.15, d_max: float = 0.3) -> None:
        """Move the mouse to (x,y) with a human-like trajectory."""
        try:
            curr_x, curr_y = pydirectinput.position()
            mid_x = int((curr_x + x) / 2) + _RNG.randint(-amp, amp)
            mid_y = int((curr_y + y) / 2) + _RNG.randint(-amp, amp)
            dur1 = _RNG.uniform(d_min, d_max)
            dur2 = _RNG.uniform(d_min, d_max)
            pydirectinput.moveTo(mid_x, mid_y, duration=dur1)
            pydirectinput.moveTo(x, y, duration=dur2)
        except Exception:
            log.debug("Humanized move failed; falling back to direct move.", exc_info=True)
            pydirectinput.moveTo(x, y, duration=_RNG.uniform(d_min * 2, d_max * 2))

    def humanized_click(self, x: int, y: int, amp: int = 150, d_min: float = 0.15, d_max: float = 0.3) -> None:
        """Move the mouse to (x,y) with a human-like trajectory and click."""
        self.humanized_move(x, y, amp, d_min, d_max)
        time.sleep(_RNG.uniform(0.05, 0.15))
        pydirectinput.click()

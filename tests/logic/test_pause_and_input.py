import time
import unittest
from unittest.mock import MagicMock, patch

from main import NTEFishingBot
from modules.io_module import InputModule


class TestInterruptibleWait(unittest.TestCase):
    """`_interruptible_wait` must wake promptly on stop or pause."""

    def _make_bot(self) -> NTEFishingBot:
        bot = NTEFishingBot()
        bot.input = MagicMock()
        return bot

    def test_returns_true_immediately_when_paused(self):
        bot = self._make_bot()
        bot._is_paused = True
        start = time.monotonic()
        self.assertTrue(bot._interruptible_wait(10.0))
        self.assertLess(time.monotonic() - start, 0.2)

    def test_returns_true_immediately_when_stopped(self):
        bot = self._make_bot()
        bot._stop_flag = True
        bot._stop_event.set()
        start = time.monotonic()
        self.assertTrue(bot._interruptible_wait(10.0))
        self.assertLess(time.monotonic() - start, 0.2)

    def test_returns_false_after_full_timeout(self):
        bot = self._make_bot()
        bot._is_paused = False
        bot._stop_flag = False
        start = time.monotonic()
        self.assertFalse(bot._interruptible_wait(0.1))
        self.assertGreaterEqual(time.monotonic() - start, 0.09)

    def test_zero_timeout_reports_current_state(self):
        bot = self._make_bot()
        bot._is_paused = False
        bot._stop_flag = False
        self.assertFalse(bot._interruptible_wait(0.0))
        bot._is_paused = True
        self.assertTrue(bot._interruptible_wait(0.0))

    def test_pause_set_mid_wait_wakes_within_poll_interval(self):
        bot = self._make_bot()
        bot._is_paused = False
        bot._stop_flag = False

        def pause_soon():
            time.sleep(0.05)
            bot._is_paused = True

        import threading
        threading.Thread(target=pause_soon, daemon=True).start()
        start = time.monotonic()
        # Would otherwise block ~5s; must return shortly after pause is set.
        self.assertTrue(bot._interruptible_wait(5.0))
        self.assertLess(time.monotonic() - start, 0.5)


class TestPressKeyTracking(unittest.TestCase):
    """press() must track the key as held so a concurrent release_all() frees it."""

    @patch("modules.io_module.pydirectinput")
    def test_press_tracks_key_during_hold_and_clears_after(self, mock_pdi):
        inp = InputModule()
        observed = {}

        def fake_sleep(_secs):
            # Mid-press the key must be tracked, so a concurrent stop can release it.
            observed["held_during_press"] = "f" in inp._held
            inp.release_all()  # simulate a stop from another thread

        with patch("modules.io_module.time.sleep", side_effect=fake_sleep):
            inp.press("f", 0.05)

        self.assertTrue(observed["held_during_press"])
        self.assertNotIn("f", inp._held)
        self.assertTrue(mock_pdi.keyUp.called)


if __name__ == "__main__":
    unittest.main()

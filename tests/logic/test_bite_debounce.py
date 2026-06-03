import unittest
from unittest.mock import MagicMock

from main import NTEFishingBot


class TestBiteDebounce(unittest.TestCase):
    """The WAITING bite trigger must not fire on residual cast-UI blue.

    Real bites occur seconds after WAITING begins; the cast animation can leave
    blue in the button ROI at the very start of WAITING, which previously fired
    an instant false 'bite'. The trigger must arm (blue cleared, or a fallback
    delay elapsed) before a blue reading counts as a bite.
    """

    def _make_bot(self) -> NTEFishingBot:
        bot = NTEFishingBot()
        bot.input = MagicMock()
        bot.cfg.timing.bite_arm_delay_secs = 2.0
        bot._bite_armed = False  # state on fresh WAITING entry
        return bot

    def test_residual_blue_at_entry_is_ignored(self):
        bot = self._make_bot()
        # Blue already present on the first WAITING frame -> not a bite yet.
        self.assertFalse(bot._accept_bite(blue_present=True, time_in_waiting=0.0))
        self.assertFalse(bot._accept_bite(blue_present=True, time_in_waiting=0.3))

    def test_arms_after_blue_clears_then_accepts(self):
        bot = self._make_bot()
        bot._accept_bite(blue_present=True, time_in_waiting=0.0)   # residual, ignored
        self.assertFalse(bot._accept_bite(blue_present=False, time_in_waiting=0.5))  # clears -> arm
        self.assertTrue(bot._accept_bite(blue_present=True, time_in_waiting=3.5))    # real bite

    def test_fallback_delay_arms_when_blue_never_clears(self):
        bot = self._make_bot()
        # Blue persists the whole time; must still fire once past the fallback delay.
        self.assertFalse(bot._accept_bite(blue_present=True, time_in_waiting=1.0))
        self.assertTrue(bot._accept_bite(blue_present=True, time_in_waiting=2.0))

    def test_clear_reading_alone_does_not_fire(self):
        bot = self._make_bot()
        # A no-blue reading arms but never reports a bite on its own.
        self.assertFalse(bot._accept_bite(blue_present=False, time_in_waiting=5.0))


if __name__ == "__main__":
    unittest.main()

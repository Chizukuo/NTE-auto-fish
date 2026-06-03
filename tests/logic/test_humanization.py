import unittest
from unittest.mock import MagicMock

from main import NTEFishingBot
from modules.logic import FishingState

# Sentinel value that must never survive a reset.
_STALE = 12345.0


class TestHumanizationReset(unittest.TestCase):
    """The humanized pulse/reaction state must not leak across struggles or runs.

    The GUI reuses a single NTEFishingBot instance across every start, so stale
    `_hum_*` state from a previous fish/run would corrupt the start of the next
    struggle (mis-sequenced pulse, skipped reaction delay). Each entry point that
    begins fresh work must reset it.
    """

    def _make_bot(self) -> NTEFishingBot:
        bot = NTEFishingBot()
        # Avoid real key presses and reaction-latency sleeps in _enter_struggling.
        bot.input = MagicMock()
        bot.cfg.humanization.enabled = False
        return bot

    def _seed_stale_state(self, bot: NTEFishingBot) -> None:
        bot._hum_reaction_end = _STALE
        bot._hum_pulse_end = _STALE
        bot._hum_pulse_state = "HOLD"
        bot._hum_target_action = "RIGHT"
        bot._last_action = "RIGHT"

    def _assert_fresh(self, bot: NTEFishingBot) -> None:
        self.assertEqual(bot._hum_reaction_end, 0.0)
        self.assertEqual(bot._hum_pulse_end, 0.0)
        self.assertEqual(bot._hum_pulse_state, "IDLE")
        self.assertEqual(bot._hum_target_action, "NONE")
        self.assertEqual(bot._last_action, "NONE")

    def test_init_initializes_humanization_state(self):
        # Headless `start` never calls prepare_for_run, so __init__ must set these.
        bot = self._make_bot()
        self._assert_fresh(bot)

    def test_enter_struggling_clears_stale_state(self):
        bot = self._make_bot()
        self._seed_stale_state(bot)

        bot._enter_struggling()

        self.assertIs(bot.sm.state, FishingState.STRUGGLING)
        self._assert_fresh(bot)

    def test_prepare_for_run_clears_stale_state(self):
        bot = self._make_bot()
        self._seed_stale_state(bot)

        bot.prepare_for_run()

        self._assert_fresh(bot)


if __name__ == "__main__":
    unittest.main()

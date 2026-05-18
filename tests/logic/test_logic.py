import unittest

from modules.logic import FishingState, FishingStateMachine, PIDController


class TestPIDController(unittest.TestCase):
    def test_pid_output_direction_matches_error_direction(self):
        pid = PIDController(kp=0.5, ki=0.0, kd=0.0, adaptive=False)

        right_output = pid.update(current=20.0, target=50.0, bar_half_width=100.0)
        left_output = pid.update(current=50.0, target=20.0, bar_half_width=100.0)

        self.assertGreater(right_output, 0.0)
        self.assertLess(left_output, 0.0)

    def test_reset_clears_internal_state(self):
        pid = PIDController(kp=0.5, ki=0.2, kd=0.1, adaptive=True)
        pid.update(current=10.0, target=40.0, bar_half_width=100.0)
        pid.update(current=15.0, target=40.0, bar_half_width=100.0)

        pid.reset()

        self.assertEqual(pid._integral, 0.0)  # internal state contract
        self.assertTrue(pid._first_call)
        self.assertEqual(pid._adaptive_kp_scale, 1.0)


class TestFishingStateMachine(unittest.TestCase):
    def test_transition_changes_state(self):
        sm = FishingStateMachine()
        self.assertEqual(sm.state, FishingState.IDLE)

        sm.transition(FishingState.WAITING)
        self.assertEqual(sm.state, FishingState.WAITING)

        sm.transition(FishingState.STRUGGLING)
        self.assertEqual(sm.state, FishingState.STRUGGLING)


if __name__ == "__main__":
    unittest.main()

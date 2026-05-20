import unittest
from unittest.mock import patch, MagicMock
from modules.io_module import InputModule
from config import HsvRange

class TestGuiAndIo(unittest.TestCase):
    @patch('modules.io_module.pydirectinput')
    def test_pulse_hold_with_none_stop_event(self, mock_pydirectinput):
        input_mod = InputModule()
        # Should not raise TypeError when stop_event is None
        input_mod.pulse_hold("a", 0.01, 0.01, stop_event=None)
        self.assertTrue(mock_pydirectinput.keyDown.called)
        self.assertTrue(mock_pydirectinput.keyUp.called)

    @patch('modules.io_module.pydirectinput')
    def test_pulse_hold_with_stop_event(self, mock_pydirectinput):
        import threading
        input_mod = InputModule()
        stop_event = threading.Event()
        input_mod.pulse_hold("a", 0.01, 0.01, stop_event=stop_event)
        self.assertTrue(mock_pydirectinput.keyDown.called)
        self.assertTrue(mock_pydirectinput.keyUp.called)

    @patch('gui.components.dpg')
    def test_on_hsv_changed_clamps_hue(self, mock_dpg):
        from gui.components import _on_hsv_changed
        hsv_range = HsvRange(lower=(10, 50, 50), upper=(100, 200, 200))
        
        # Test lower Hue above 179
        _on_hsv_changed("prefix", hsv_range, "lower", [185, 60, 70])
        self.assertEqual(hsv_range.lower, (179, 60, 70))
        mock_dpg.set_value.assert_called_with("prefix_lower", [179, 60, 70])

        # Test upper Hue within bounds
        _on_hsv_changed("prefix", hsv_range, "upper", [150, 80, 90])
        self.assertEqual(hsv_range.upper, (150, 80, 90))
        mock_dpg.set_value.assert_called_with("prefix_upper", [150, 80, 90])

if __name__ == "__main__":
    unittest.main()

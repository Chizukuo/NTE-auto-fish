import unittest

from modules.utils import ELEVATION_WARNING, is_elevated


class TestElevation(unittest.TestCase):
    def test_is_elevated_returns_bool_without_raising(self):
        self.assertIsInstance(is_elevated(), bool)

    def test_elevation_warning_is_actionable(self):
        text = ELEVATION_WARNING.lower()
        self.assertIn("administrator", text)
        self.assertIn("register", text)


if __name__ == "__main__":
    unittest.main()

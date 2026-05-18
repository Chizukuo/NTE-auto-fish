import json
import tempfile
import unittest
from pathlib import Path

from config import AppConfig


class TestAppConfig(unittest.TestCase):
    def test_save_and_load_roundtrip(self):
        cfg = AppConfig()
        cfg.pid.kp = 0.73
        cfg.hotkeys.toggle = "f9"

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            cfg.save(str(path))

            loaded = AppConfig()
            loaded.load(str(path))

        self.assertEqual(loaded.pid.kp, 0.73)
        self.assertEqual(loaded.hotkeys.toggle, "f9")

    def test_load_invalid_json_keeps_existing_values(self):
        cfg = AppConfig()
        cfg.pid.kp = 0.91

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            path.write_text("{invalid json", encoding="utf-8")
            cfg.load(str(path))

        self.assertEqual(cfg.pid.kp, 0.91)

    def test_save_outputs_valid_json(self):
        cfg = AppConfig()

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            cfg.save(str(path))
            payload = json.loads(path.read_text(encoding="utf-8"))

        self.assertIn("pid", payload)
        self.assertIn("hsv", payload)


if __name__ == "__main__":
    unittest.main()

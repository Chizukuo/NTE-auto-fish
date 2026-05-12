import unittest
from pathlib import Path

import cv2
import numpy as np

from config import AppConfig
from modules.vision import VisionModule


class TestCheckBlueTrigger(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data_dir = Path(__file__).parent / "data"

        cls.blue_positive_images = sorted(
            (cls.data_dir / "blue/positive").rglob("*.png")
        )

        cls.blue_negative_images = sorted(
            (cls.data_dir / "blue/negative").rglob("*.png")
        )

    def load_image(self, image_path: Path) -> np.ndarray:
        img = cv2.imdecode(
            np.fromfile(image_path, dtype=np.uint8),
            cv2.IMREAD_COLOR,
        )

        if img is None:
            raise Exception(f"Failed to load image: {image_path}")

        return img

    def _get_min_pixels(self, filename: str) -> int:
        base_pixels = AppConfig().min_blue_pixels
        thresholds = {
            "4k": base_pixels,
            "2k": base_pixels // 2,
            "1080p": base_pixels // 4
        }
        parts = filename.lower().split("_")
        res = next((p for p in parts if p in thresholds), "4k")
        return thresholds[res]

    def test_blue_trigger_positive_cases(self):
        """Images expected to contain enough blue trigger pixels."""
        for image_path in self.blue_positive_images:
            with self.subTest(image=image_path.name):
                img = self.load_image(image_path)
                min_pixels = self._get_min_pixels(image_path.stem)

                result = VisionModule.check_blue_trigger(img, min_pixels=min_pixels)

                self.assertTrue(
                    result,
                    f"Expected trigger for image: {image_path.name} with min_pixels={min_pixels}",
                )

    def test_blue_trigger_negative_cases(self):
        """Images expected to NOT contain enough blue trigger pixels."""
        for image_path in self.blue_negative_images:
            with self.subTest(image=image_path.name):
                img = self.load_image(image_path)
                min_pixels = self._get_min_pixels(image_path.stem)

                result = VisionModule.check_blue_trigger(img, min_pixels=min_pixels)

                self.assertFalse(
                    result,
                    f"Did not expect trigger for image: {image_path.name} with min_pixels={min_pixels}",
                )


if __name__ == "__main__":
    unittest.main()

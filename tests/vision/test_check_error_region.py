import unittest
from pathlib import Path

import cv2
import numpy as np

from modules.vision import VisionModule, _ERROR_BRIGHTNESS_THRESHOLD, _ERROR_WHITE_PIXEL_MIN


class TestCheckErrorRegion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data_dir = Path(__file__).parent / "data"

        cls.error_positive_images = sorted(
            (cls.data_dir / "error/positive").rglob("*.png")
        )

        cls.error_negative_images = sorted(
            (cls.data_dir / "error/negative").rglob("*.png")
        )

    def load_image(self, image_path: Path) -> np.ndarray:
        img = cv2.imdecode(
            np.fromfile(image_path, dtype=np.uint8),
            cv2.IMREAD_COLOR,
        )

        if img is None:
            raise Exception(f"Failed to load image: {image_path}")

        return img

    def _get_thresholds(self, filename: str) -> dict:
        base_brightness = _ERROR_BRIGHTNESS_THRESHOLD
        base_white = _ERROR_WHITE_PIXEL_MIN
        thresholds = {
            "4k": {"brightness": base_brightness, "white_pixel_min": base_white},
            "2k": {"brightness": base_brightness, "white_pixel_min": base_white // 2},
            "1080p": {"brightness": base_brightness, "white_pixel_min": base_white // 4}
        }
        parts = filename.lower().split("_")
        res = next((p for p in parts if p in thresholds), "4k")
        return thresholds[res]

    def test_error_region_positive_cases(self):
        """Images expected to be detected as error dialogs."""
        for image_path in self.error_positive_images:
            with self.subTest(image=image_path.name):
                img = self.load_image(image_path)
                kwargs = self._get_thresholds(image_path.stem)

                result = VisionModule.check_error_region(
                    img,
                    brightness_threshold=kwargs["brightness"],
                    white_pixel_min=kwargs["white_pixel_min"]
                )

                self.assertTrue(
                    result,
                    f"Expected error detection for image: {image_path.name} with params={kwargs}",
                )

    def test_error_region_negative_cases(self):
        """Images expected to NOT be detected as error dialogs (e.g. nighttime scenes)."""
        for image_path in self.error_negative_images:
            with self.subTest(image=image_path.name):
                img = self.load_image(image_path)
                kwargs = self._get_thresholds(image_path.stem)

                result = VisionModule.check_error_region(
                    img,
                    brightness_threshold=kwargs["brightness"],
                    white_pixel_min=kwargs["white_pixel_min"]
                )

                self.assertFalse(
                    result,
                    f"Did not expect error detection for image: {image_path.name} with params={kwargs}",
                )


if __name__ == "__main__":
    unittest.main()

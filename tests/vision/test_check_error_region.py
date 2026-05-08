import unittest
from pathlib import Path

import cv2
import numpy as np

from modules.vision import VisionModule


class TestCheckErrorRegion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data_dir = Path(__file__).parent / "data"

        cls.error_positive_images = sorted(
            (cls.data_dir / "error_positive").glob("*.png")
        )

        cls.error_negative_images = sorted(
            (cls.data_dir / "error_negative").glob("*.png")
        )

    def load_image(self, image_path: Path) -> np.ndarray:
        img = cv2.imdecode(
            np.fromfile(image_path, dtype=np.uint8),
            cv2.IMREAD_COLOR,
        )

        if img is None:
            raise Exception(f"Failed to load image: {image_path}")

        return img

    def test_error_region_positive_cases(self):
        """Images expected to be detected as error dialogs."""
        for image_path in self.error_positive_images:
            with self.subTest(image=image_path.name):
                img = self.load_image(image_path)

                result = VisionModule.check_error_region(img)

                self.assertTrue(
                    result,
                    f"Expected error detection for image: {image_path.name}",
                )

    def test_error_region_negative_cases(self):
        """Images expected to NOT be detected as error dialogs (e.g. nighttime scenes)."""
        for image_path in self.error_negative_images:
            with self.subTest(image=image_path.name):
                img = self.load_image(image_path)

                result = VisionModule.check_error_region(img)

                self.assertFalse(
                    result,
                    f"Did not expect error detection for image: {image_path.name}",
                )


if __name__ == "__main__":
    unittest.main()

import unittest
from pathlib import Path

import cv2
import numpy as np

from modules.vision import VisionModule


class TestCheckBlueTrigger(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data_dir = Path(__file__).parent / "data"

        cls.blue_positive_images = sorted(
            (cls.data_dir / "blue_positive").glob("*.png")
        )

        cls.blue_negative_images = sorted(
            (cls.data_dir / "blue_negative").glob("*.png")
        )

    def load_image(self, image_path: Path) -> np.ndarray:
        img = cv2.imdecode(
            np.fromfile(image_path, dtype=np.uint8),
            cv2.IMREAD_COLOR,
        )

        if img is None:
            raise Exception(f"Failed to load image: {image_path}")

        return img

    def test_blue_trigger_positive_cases(self):
        """Images expected to contain enough blue trigger pixels."""
        for image_path in self.blue_positive_images:
            with self.subTest(image=image_path.name):
                img = self.load_image(image_path)

                result = VisionModule.check_blue_trigger(img)

                self.assertTrue(
                    result,
                    f"Expected trigger for image: {image_path.name}",
                )

    def test_blue_trigger_negative_cases(self):
        """Images expected to NOT contain enough blue trigger pixels."""
        for image_path in self.blue_negative_images:
            with self.subTest(image=image_path.name):
                img = self.load_image(image_path)

                result = VisionModule.check_blue_trigger(img)

                self.assertFalse(
                    result,
                    f"Did not expect trigger for image: {image_path.name}",
                )


if __name__ == "__main__":
    unittest.main()

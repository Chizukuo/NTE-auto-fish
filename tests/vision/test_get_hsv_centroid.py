import unittest
from pathlib import Path

import cv2
import numpy as np

from config import HsvConfig
from modules.vision import VisionModule


class TestHSVCentroid(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data_dir = Path(__file__).parent / "data"

        cls.hsv_centroid_bar_positive_images = sorted(
            (cls.data_dir / "hsv_centroid_bar_positive").glob("*.png")
        )

        cls.hsv_centroid_bar_negative_images = sorted(
            (cls.data_dir / "hsv_centroid_bar_negative").glob("*.png")
        )
        
        cls.hsv_centroid_cursor_positive_images = sorted(
            (cls.data_dir / "hsv_centroid_cursor_positive").glob("*.png")
        )

        cls.hsv_centroid_cursor_negative_images = sorted(
            (cls.data_dir / "hsv_centroid_cursor_negative").glob("*.png")
        )


    def load_image(self, image_path: Path) -> np.ndarray:
        img = cv2.imdecode(
            np.fromfile(image_path, dtype=np.uint8),
            cv2.IMREAD_COLOR,
        )

        if img is None:
            raise Exception(f"Failed to load image: {image_path}")

        return img

    def test_get_bar_positive_cases(self):
        for image_path in self.hsv_centroid_bar_positive_images:
            with self.subTest(image=image_path.name):
                img = self.load_image(image_path)

                result = VisionModule.get_hsv_centroid_x(
                    img,
                    HsvConfig().safe_zone.lower,
                    HsvConfig().safe_zone.upper,
                )

                self.assertIsNotNone(result[0])

    def test_get_bar_negative_cases(self):
        for image_path in self.hsv_centroid_bar_negative_images:
            with self.subTest(image=image_path.name):
                img = self.load_image(image_path)

                result = VisionModule.get_hsv_centroid_x(
                    img,
                    HsvConfig().safe_zone.lower,
                    HsvConfig().safe_zone.upper,
                )

                self.assertIsNone(result[0])


    def test_get_cursor_positive_cases(self):
        for image_path in self.hsv_centroid_cursor_positive_images:
            with self.subTest(image=image_path.name):
                img = self.load_image(image_path)

                result = VisionModule.get_hsv_centroid_x(
                    img,
                    HsvConfig().cursor.lower,
                    HsvConfig().cursor.upper,
                )

                self.assertIsNotNone(result[0])

    def test_get_cursor_negative_cases(self):
        for image_path in self.hsv_centroid_cursor_negative_images:
            with self.subTest(image=image_path.name):
                img = self.load_image(image_path)

                result = VisionModule.get_hsv_centroid_x(
                    img,
                    HsvConfig().cursor.lower,
                    HsvConfig().cursor.upper,
                )

                self.assertIsNone(result[0])



if __name__ == "__main__":
    unittest.main()

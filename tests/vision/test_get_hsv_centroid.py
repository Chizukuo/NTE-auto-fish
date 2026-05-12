import unittest
from pathlib import Path

import cv2
import numpy as np

from config import HsvConfig
from modules.vision import VisionModule, _DEFAULT_MIN_AREA


class TestHSVCentroid(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data_dir = Path(__file__).parent / "data"

        cls.hsv_centroid_bar_positive_images = sorted(
            (cls.data_dir / "bar/positive").rglob("*.png")
        )

        cls.hsv_centroid_bar_negative_images = sorted(
            (cls.data_dir / "bar/negative").rglob("*.png")
        )

        cls.hsv_centroid_cursor_positive_images = sorted(
            (cls.data_dir / "cursor/positive").rglob("*.png")
        )

        cls.hsv_centroid_cursor_negative_images = sorted(
            (cls.data_dir / "cursor/negative").rglob("*.png")
        )


    def load_image(self, image_path: Path) -> np.ndarray:
        img = cv2.imdecode(
            np.fromfile(image_path, dtype=np.uint8),
            cv2.IMREAD_COLOR,
        )

        if img is None:
            raise Exception(f"Failed to load image: {image_path}")

        return img

    def _get_min_area(self, filename: str) -> float:
        base_area = _DEFAULT_MIN_AREA
        thresholds = {
            "4k": base_area,
            "2k": base_area / 2.0,
            "1080p": base_area / 4.0
        }
        parts = filename.lower().split("_")
        res = next((p for p in parts if p in thresholds), "4k")
        return thresholds[res]

    def test_get_bar_positive_cases(self):
        for image_path in self.hsv_centroid_bar_positive_images:
            with self.subTest(image=image_path.name):
                img = self.load_image(image_path)
                min_area = self._get_min_area(image_path.stem)

                result = VisionModule.get_hsv_centroid_x(
                    img,
                    HsvConfig().safe_zone.lower,
                    HsvConfig().safe_zone.upper,
                    min_area=min_area
                )

                self.assertIsNotNone(result[0])

    def test_get_bar_negative_cases(self):
        for image_path in self.hsv_centroid_bar_negative_images:
            with self.subTest(image=image_path.name):
                img = self.load_image(image_path)
                min_area = self._get_min_area(image_path.stem)

                result = VisionModule.get_hsv_centroid_x(
                    img,
                    HsvConfig().safe_zone.lower,
                    HsvConfig().safe_zone.upper,
                    min_area=min_area
                )

                self.assertIsNone(result[0])


    def test_get_cursor_positive_cases(self):
        for image_path in self.hsv_centroid_cursor_positive_images:
            with self.subTest(image=image_path.name):
                img = self.load_image(image_path)
                min_area = self._get_min_area(image_path.stem)

                result = VisionModule.get_hsv_centroid_x(
                    img,
                    HsvConfig().cursor.lower,
                    HsvConfig().cursor.upper,
                    min_area=min_area
                )

                self.assertIsNotNone(result[0])

    def test_get_cursor_negative_cases(self):
        for image_path in self.hsv_centroid_cursor_negative_images:
            with self.subTest(image=image_path.name):
                img = self.load_image(image_path)
                min_area = self._get_min_area(image_path.stem)

                result = VisionModule.get_hsv_centroid_x(
                    img,
                    HsvConfig().cursor.lower,
                    HsvConfig().cursor.upper,
                    min_area=min_area
                )

                self.assertIsNone(result[0])



if __name__ == "__main__":
    unittest.main()

"""Computer vision helpers for template matching and HSV detection."""
import cv2
import numpy as np

from config import CFG, CalibrationConfig, HsvRange

_ERROR_BRIGHTNESS_THRESHOLD = 25
_ERROR_WHITE_PIXEL_MIN = 800


_KERNEL_3x3 = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))


class VisionModule:
    """Stateless image processing utilities."""

    @staticmethod
    def find_template_multi_scale(
        scene_bgr: np.ndarray,
        template_bgr: np.ndarray,
        calibration: CalibrationConfig | None = None,
    ):
        """Find a template in a scene while allowing scale differences."""
        cfg = calibration or CFG.calibration
        scales = np.linspace(cfg.scale_min, cfg.scale_max, cfg.scale_steps)

        scene_gray = cv2.cvtColor(scene_bgr, cv2.COLOR_BGR2GRAY)
        tmpl_gray = cv2.cvtColor(template_bgr, cv2.COLOR_BGR2GRAY)
        t_h, t_w = tmpl_gray.shape[:2]

        best_val = -np.inf
        best_loc = None
        best_scale = 1.0

        for scale in scales:
            new_w = max(1, int(t_w * scale))
            new_h = max(1, int(t_h * scale))

            if new_h >= scene_gray.shape[0] or new_w >= scene_gray.shape[1]:
                continue
            if new_w < 8 or new_h < 8:
                continue

            interp = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_LINEAR
            resized = cv2.resize(tmpl_gray, (new_w, new_h), interpolation=interp)
            result = cv2.matchTemplate(scene_gray, resized, cv2.TM_CCOEFF_NORMED)
            _, val, _, loc = cv2.minMaxLoc(result)

            if val > best_val:
                best_val = val
                best_loc = loc
                best_scale = scale

        if best_val < cfg.confidence_threshold or best_loc is None:
            return None

        x1 = best_loc[0]
        y1 = best_loc[1]
        x2 = int(x1 + t_w * best_scale)
        y2 = int(y1 + t_h * best_scale)
        return (x1, y1, x2, y2)

    @staticmethod
    def get_hsv_centroid_x(
        bgr_img: np.ndarray,
        lower: tuple,
        upper: tuple,
        min_area: float = 50.0,
        ignore_margin_ratio: float = 0.0,
        last_known_x: float | None = None,
    ):
        """Return the horizontal centroid for pixels inside an HSV range."""
        hsv = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(
            hsv,
            np.array(lower, dtype=np.uint8),
            np.array(upper, dtype=np.uint8),
        )
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, _KERNEL_3x3)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return None, 0.0

        valid_contours = []
        img_width = bgr_img.shape[1]

        for contour in contours:
            x, _, w, h = cv2.boundingRect(contour)
            bbox_area = w * h

            if bbox_area < min_area:
                continue

            if ignore_margin_ratio > 0.0:
                left_limit = img_width * ignore_margin_ratio
                right_limit = img_width * (1.0 - ignore_margin_ratio)
                if x < left_limit or (x + w) > right_limit:
                    continue

            valid_contours.append(contour)

        if not valid_contours:
            return None, 0.0

        if last_known_x is None:
            last_known_x = img_width / 2.0

        def distance_to_last(contour) -> float:
            x, _, w, _ = cv2.boundingRect(contour)
            return abs((x + w / 2.0) - last_known_x)

        valid_contours.sort(key=distance_to_last)

        main_contour = valid_contours[0]
        main_x, _, main_w, main_h = cv2.boundingRect(main_contour)
        group_min_x = main_x
        group_max_x = main_x + main_w
        total_area = main_w * main_h
        gap_threshold = img_width * 0.05

        for contour in valid_contours[1:]:
            x, _, w, h = cv2.boundingRect(contour)
            gap = max(0, max(group_min_x - (x + w), x - group_max_x))
            if gap <= gap_threshold:
                group_min_x = min(group_min_x, x)
                group_max_x = max(group_max_x, x + w)
                total_area += w * h

        cx = int((group_min_x + group_max_x) / 2.0)
        return cx, float(total_area)

    @staticmethod
    def check_error_region(bgr_img: np.ndarray) -> bool:
        """Return True when the region shows a dark background with white text (error dialog)."""
        gray = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2GRAY)
        mean_brightness = float(np.mean(gray))
        if mean_brightness > _ERROR_BRIGHTNESS_THRESHOLD:
            return False
        white_pixels = int(cv2.countNonZero(cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)[1]))
        return white_pixels >= _ERROR_WHITE_PIXEL_MIN

    @staticmethod
    def check_blue_trigger(
        bgr_img: np.ndarray,
        hsv_range: HsvRange | None = None,
        min_pixels: int | None = None,
    ) -> bool:
        """Return true when enough bite-trigger pixels are present."""
        hsv = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2HSV)
        blue = hsv_range or CFG.hsv.blue
        threshold = CFG.min_blue_pixels if min_pixels is None else min_pixels
        lower = np.array(blue.lower, dtype=np.uint8)
        upper = np.array(blue.upper, dtype=np.uint8)
        mask = cv2.inRange(hsv, lower, upper)
        return cv2.countNonZero(mask) >= threshold

"""
modules/vision.py
职责：
  VisionModule  — 颜色识别（安全区、游标、蓝色触发）与多尺度模板匹配
所有方法输入均为 BGR ndarray（由 CaptureModule.grab_bgr 保证）。
"""
import cv2
import numpy as np

from config import CFG

# ---------------------------------------------------------------------------
# 预构建的形态学 kernel——避免热路径中每帧重新分配
# ---------------------------------------------------------------------------
_KERNEL_3x3 = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))


class VisionModule:
    """无状态视觉处理工具集。"""

    # ------------------------------------------------------------------
    # 多尺度模板匹配（仅冷启动校准时调用，非热路径）
    # ------------------------------------------------------------------

    @staticmethod
    def find_template_multi_scale(
        scene_bgr: np.ndarray,
        template_bgr: np.ndarray,
    ):
        """
        在 scene 中搜索 template，允许 template 有缩放偏差。
        对 template 进行多尺度缩放并逐一匹配，保留最高置信度结果。
        返回 (x1, y1, x2, y2) 或 None。
        """
        cfg = CFG.calibration
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

            # 缩放后的模板不能超过 scene 尺寸
            if new_h >= scene_gray.shape[0] or new_w >= scene_gray.shape[1]:
                continue
            # 太小的模板匹配噪声极大
            if new_w < 8 or new_h < 8:
                continue

            # INTER_AREA 用于缩小，INTER_LINEAR 用于放大
            interp = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_LINEAR
            resized = cv2.resize(tmpl_gray, (new_w, new_h),
                                 interpolation=interp)
            result = cv2.matchTemplate(
                scene_gray, resized, cv2.TM_CCOEFF_NORMED)
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

    # ------------------------------------------------------------------
    # 热路径：颜色质心提取（STRUGGLING 状态每帧调用）
    # ------------------------------------------------------------------

    @staticmethod
    def get_hsv_centroid_x(
        bgr_img: np.ndarray,
        lower: tuple,
        upper: tuple,
        min_area: float = 50.0,
        ignore_margin_ratio: float = 0.0,
        last_known_x: float | None = None,
    ):
        """
        在图像中提取满足 HSV 范围的像素，计算其水平质心坐标。
        返回 (cx: int, area: float) 或 (None, 0.0)。
        """
        hsv = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv,
                           np.array(lower, dtype=np.uint8),
                           np.array(upper, dtype=np.uint8))

        # 3×3 开运算去小噪点
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, _KERNEL_3x3)

        # 寻找所有轮廓
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return None, 0.0
            
        valid_contours = []
        img_width = bgr_img.shape[1]
        
        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            bbox_area = w * h
            
            # 1. 过滤面积过小的纯噪点
            if bbox_area < min_area:
                continue
            
            # 2. 边缘死区过滤（保留作为双重保险，过滤掉两端的干扰图标）
            if ignore_margin_ratio > 0.0:
                if x < img_width * ignore_margin_ratio or (x + w) > img_width * (1.0 - ignore_margin_ratio):
                    continue
                    
            valid_contours.append(c)
            
        if not valid_contours:
            return None, 0.0

        if last_known_x is None:
            last_known_x = img_width / 2.0

        # 时空连贯性算法：按照距离“上一帧已知位置（或画面中心）”的远近进行排序
        # 游标绝不可能在 0.01 秒内瞬间位移半个屏幕，所以离上一帧最近的绝对是真目标！
        valid_contours.sort(key=lambda c: abs((cv2.boundingRect(c)[0] + cv2.boundingRect(c)[2] / 2.0) - last_known_x))
        
        # 选取距离最近的主轮廓
        main_c = valid_contours[0]
        mx, my, mw, mh = cv2.boundingRect(main_c)
        
        # 我们只合并与主轮廓“距离很近”的碎片（解决被游标切断的问题）
        # 游标宽度通常几十像素，设定一个合理的间隙阈值（比如画面宽度的 5%）
        gap_threshold = img_width * 0.05
        
        group_min_x = mx
        group_max_xw = mx + mw
        total_area = mw * mh
        
        for c in valid_contours[1:]:
            x, y, w, h = cv2.boundingRect(c)
            # 检查水平方向上的间隙
            # 主轮廓在左，碎片在右，或者碎片在左，主轮廓在右
            gap = max(0, max(group_min_x - (x + w), x - group_max_xw))
            
            if gap <= gap_threshold:
                # 认为是同一整体被切断的，进行缝合
                group_min_x = min(group_min_x, x)
                group_max_xw = max(group_max_xw, x + w)
                total_area += (w * h)
                
        # 超级矩形的中心就是真正目标的物理中心
        cx = int((group_min_x + group_max_xw) / 2.0)
        return cx, float(total_area)

    # ------------------------------------------------------------------
    # 热路径：蓝色按钮触发检测（WAITING 状态每帧调用）
    # ------------------------------------------------------------------

    @staticmethod
    def check_blue_trigger(bgr_img: np.ndarray) -> bool:
        """
        检测 ROI 中是否存在足量蓝色像素（按钮高亮 = 鱼上钩）。
        使用 cv2.countNonZero 而非 np.sum，在小图上更快。
        """
        hsv = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2HSV)
        lower = np.array(CFG.hsv.blue.lower, dtype=np.uint8)
        upper = np.array(CFG.hsv.blue.upper, dtype=np.uint8)
        mask = cv2.inRange(hsv, lower, upper)
        return cv2.countNonZero(mask) >= CFG.min_blue_pixels

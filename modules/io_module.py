"""
modules/io_module.py
职责：
  CaptureModule  — 使用 mss 高速截取指定 ROI，统一转换为 BGR（3通道）
  InputModule    — 对 pydirectinput 的轻量封装，支持按键持续时间控制
"""
import time

import mss
import numpy as np
import pydirectinput

# pydirectinput 默认在每次调用之间插入 0.1s 延迟，对高频循环是灾难
pydirectinput.PAUSE = 0.0


class CaptureModule:
    """
    延迟实例化 mss。在首次调用时创建 mss 实例，以确保绑定到调用的线程。
    """

    def __init__(self) -> None:
        self._sct = None

    def _get_sct(self):
        if self._sct is None:
            self._sct = mss.mss()
        return self._sct

    def grab_bgr(self, roi: dict) -> np.ndarray:
        """
        截取指定 ROI 并返回 BGR uint8 ndarray，形状 (H, W, 3)。

        mss.grab() 返回 BGRA 四通道（第四通道永远是 255）。
        直接把 BGRA 传给 cv2.cvtColor(img, COLOR_BGR2HSV) 会把
        alpha 通道当作 R 通道，导致整个颜色识别系统全部出错。
        这里统一去掉 alpha，只保留 BGR。

        使用 np.ascontiguousarray 确保内存布局连续，
        避免后续 cv2 操作产生额外拷贝。
        """
        raw = self._get_sct().grab(roi)
        return np.ascontiguousarray(np.array(raw)[..., :3])

    def grab_full_screen(self) -> np.ndarray:
        """截取主显示器全屏，仅用于冷启动校准，主循环禁止调用。"""
        sct = self._get_sct()
        return self.grab_bgr(sct.monitors[1])

    def get_screen_size(self) -> tuple[int, int]:
        """返回主显示器 (width, height)。"""
        sct = self._get_sct()
        m = sct.monitors[1]
        return m["width"], m["height"]


class InputModule:
    """
    pydirectinput 封装。
    维护当前按下的按键集合，避免重复 keyDown 导致游戏端
    接收到多个连续 down 事件（部分引擎会重置按键计时器）。
    """

    def __init__(self) -> None:
        self._held: set[str] = set()

    def press(self, key: str, duration: float = 0.05) -> None:
        """按下并释放一个按键，不影响 _held 集合（用于单次触发）。"""
        pydirectinput.keyDown(key)
        time.sleep(duration)
        pydirectinput.keyUp(key)

    def hold(self, key: str) -> None:
        """持续按住，每次循环都发送 keyDown 模拟硬件连发，确保游戏引擎不会断触。"""
        pydirectinput.keyDown(key)
        self._held.add(key)

    def release(self, key: str) -> None:
        """释放按键，若本来就没按则跳过。"""
        if key in self._held:
            pydirectinput.keyUp(key)
            self._held.discard(key)

    def release_all(self) -> None:
        """释放所有当前按住的按键，状态切换时必须调用。"""
        for key in list(self._held):
            pydirectinput.keyUp(key)
        self._held.clear()

    def click(self, x: int, y: int) -> None:
        """在指定屏幕坐标点击（用于 RESULT 界面的"点击空白区域关闭"）。"""
        pydirectinput.click(x, y)

"""
gui/bridge.py
线程安全的 Bot ↔ GUI 通信桥。
Bot 线程通过此模块发布状态更新；GUI 主线程消费更新来刷新界面。
使用 queue.Queue（内部有锁）保证线程安全，无需手动加锁。
"""
import dataclasses
import queue
import time
from typing import Optional

from modules.logic import FishingState


@dataclasses.dataclass
class BotStatus:
    """Bot 向 GUI 推送的完整状态快照。"""
    state:       FishingState = FishingState.IDLE
    fish_count:  int = 0
    session_secs: float = 0.0
    pid_output:  float = 0.0   # 最近一次 PID 输出，用于绘图
    cursor_x:    Optional[int] = None  # 进度条内游标 X（像素）
    target_x:    Optional[int] = None  # 进度条内安全区中心 X（像素）
    bar_width:   int = 0    # 进度条 ROI 宽度（归一化用）
    fps:         float = 0.0  # STRUGGLING 帧率
    is_running:  bool = False


class BotBridge:
    """
    单例桥接对象，在 app.py 中实例化后注入给 BotRunner。
    """

    def __init__(self) -> None:
        # Bot -> GUI：状态更新（Queue，GUI 只需最新帧；限制大小防爆内存）
        self._status_q: queue.Queue[BotStatus] = queue.Queue(maxsize=60)
        # Bot -> GUI：日志消息（保留历史，LifoQueue 不适合）
        self._log_q: queue.Queue[str] = queue.Queue(maxsize=500)
        # GUI -> Bot：控制指令 ('start', 'stop', 'recalibrate')
        self._cmd_q: queue.Queue[str] = queue.Queue(maxsize=10)

        self._current_status = BotStatus()

    # ------------------------------------------------------------------ #
    # Bot 端调用                                                           #
    # ------------------------------------------------------------------ #
    def push_status(self, status: BotStatus) -> None:
        """Bot 每帧推送状态；若队列已满则丢弃旧帧。"""
        if self._status_q.full():
            try:
                self._status_q.get_nowait()
            except queue.Empty:
                pass
        try:
            self._status_q.put_nowait(status)
        except queue.Full:
            pass

    def push_log(self, msg: str) -> None:
        """Bot 推送日志消息。若队列满则丢弃最早一条。"""
        if self._log_q.full():
            try:
                self._log_q.get_nowait()
            except queue.Empty:
                pass
        try:
            self._log_q.put_nowait(f"[{_fmt_time()}] {msg}")
        except queue.Full:
            pass

    def poll_cmd(self) -> Optional[str]:
        """Bot 轮询 GUI 下发的指令，无指令时返回 None。"""
        try:
            return self._cmd_q.get_nowait()
        except queue.Empty:
            return None

    # ------------------------------------------------------------------ #
    # GUI 端调用                                                           #
    # ------------------------------------------------------------------ #
    def latest_status(self) -> BotStatus:
        """GUI 获取最新状态，消耗队列中所有帧，只返回最后一帧。"""
        latest = self._current_status
        while True:
            try:
                latest = self._status_q.get_nowait()
            except queue.Empty:
                break
        self._current_status = latest
        return latest

    def drain_logs(self) -> list[str]:
        """GUI 获取所有待显示日志。"""
        msgs = []
        while True:
            try:
                msgs.append(self._log_q.get_nowait())
            except queue.Empty:
                break
        return msgs

    def send_cmd(self, cmd: str) -> None:
        """GUI 向 Bot 发送控制指令。"""
        try:
            self._cmd_q.put_nowait(cmd)
        except queue.Full:
            pass


def _fmt_time() -> str:
    t = time.localtime()
    return f"{t.tm_hour:02d}:{t.tm_min:02d}:{t.tm_sec:02d}"

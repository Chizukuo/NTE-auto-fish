"""Thread-safe bridge between the bot worker and the DearPyGui UI."""
import dataclasses
import queue
import time
from typing import Optional, Tuple

from modules.logic import FishingState


@dataclasses.dataclass
class BotStatus:
    """Snapshot pushed from the bot thread to the GUI."""

    state: FishingState = FishingState.IDLE
    fish_count: int = 0
    session_secs: float = 0.0
    pid_output: float = 0.0
    cursor_x: Optional[int] = None
    target_x: Optional[int] = None
    bar_width: int = 0
    button_roi: Tuple[int, int, int, int] = (0, 0, 0, 0)
    bar_roi: Tuple[int, int, int, int] = (0, 0, 0, 0)
    fps: float = 0.0
    lost_frames: int = 0
    lost_cursor_frames: int = 0
    lost_target_frames: int = 0
    is_running: bool = False
    is_stopped: bool = True


class BotBridge:
    """Small queue-based boundary shared by GUI and bot threads."""

    def __init__(self) -> None:
        self._status_q: queue.Queue[BotStatus] = queue.Queue(maxsize=60)
        self._log_q: queue.Queue[str] = queue.Queue(maxsize=500)
        self._cmd_q: queue.Queue[str] = queue.Queue(maxsize=10)
        self._current_status = BotStatus()

    def push_status(self, status: BotStatus) -> None:
        """Push a status frame. Older frames are dropped when the GUI lags."""
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
        """Push a log message. The oldest entry is dropped if the queue is full."""
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
        """Return the next command for the bot thread, if any."""
        try:
            return self._cmd_q.get_nowait()
        except queue.Empty:
            return None

    def latest_status(self) -> BotStatus:
        """Drain pending status frames and return only the newest snapshot."""
        latest = self._current_status
        while True:
            try:
                latest = self._status_q.get_nowait()
            except queue.Empty:
                break
        self._current_status = latest
        return latest

    def drain_logs(self) -> list[str]:
        """Return all logs waiting to be rendered."""
        msgs = []
        while True:
            try:
                msgs.append(self._log_q.get_nowait())
            except queue.Empty:
                break
        return msgs

    def send_cmd(self, cmd: str) -> None:
        """Queue a GUI command for the bot.

        Stop is urgent: stale commands are cleared so the worker sees it as
        soon as possible. For other commands, the oldest pending command is
        dropped instead of silently losing the latest user action.
        """
        if cmd == "stop":
            self._drain_cmds()
        try:
            self._cmd_q.put_nowait(cmd)
        except queue.Full:
            try:
                self._cmd_q.get_nowait()
                self._cmd_q.put_nowait(cmd)
            except (queue.Empty, queue.Full):
                pass

    def _drain_cmds(self) -> None:
        while True:
            try:
                self._cmd_q.get_nowait()
            except queue.Empty:
                break


def _fmt_time() -> str:
    t = time.localtime()
    return f"{t.tm_hour:02d}:{t.tm_min:02d}:{t.tm_sec:02d}"

"""
modules/logic.py
职责：
  PIDController      — 带积分抗饱和和死区的 PID 控制器
  FishingState       — 强类型状态枚举
  FishingStateMachine — 状态转换管理器
"""
import enum
import logging
import time

log = logging.getLogger("NTEFish")


class FishingState(enum.Enum):
    IDLE = "IDLE"
    WAITING = "WAITING"
    STRUGGLING = "STRUGGLING"
    RESULT = "RESULT"


class PIDController:
    def __init__(self, kp: float, ki: float, kd: float,
                 integral_limit: float = 150.0,
                 deadband: float = 8.0) -> None:
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.integral_limit = integral_limit
        self.deadband = deadband
        self._integral = 0.0
        self._prev_error = 0.0
        self._last_ts = time.perf_counter()
        self._first_call = True

    def update(self, current: float, target: float) -> float:
        now = time.perf_counter()
        dt = now - self._last_ts
        self._last_ts = now

        if self._first_call:
            self._first_call = False
            dt = 0.016

        if dt < 1e-6:
            dt = 1e-6

        error = target - current

        if abs(error) >= self.deadband:
            self._integral += error * dt
            self._integral = max(-self.integral_limit,
                                 min(self.integral_limit, self._integral))

        derivative = (error - self._prev_error) / dt
        self._prev_error = error

        return self.kp * error + self.ki * self._integral + self.kd * derivative

    def reset(self) -> None:
        self._integral = 0.0
        self._prev_error = 0.0
        self._last_ts = time.perf_counter()
        self._first_call = True


class FishingStateMachine:
    def __init__(self) -> None:
        self._state = FishingState.IDLE
        self._entered_at = time.perf_counter()

    @property
    def state(self) -> FishingState:
        return self._state

    @property
    def time_in_state(self) -> float:
        return time.perf_counter() - self._entered_at

    def transition(self, new_state: FishingState) -> None:
        if new_state is self._state:
            return
        log.info(f"[State] {self._state.value:12s} -> {new_state.value}")
        self._state = new_state
        self._entered_at = time.perf_counter()

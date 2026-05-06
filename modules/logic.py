"""Fishing state machine and PID control logic."""
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
    def __init__(
        self,
        kp: float,
        ki: float,
        kd: float,
        integral_limit: float = 150.0,
        deadband: float = 8.0,
        adaptive: bool = True,
    ) -> None:
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.integral_limit = integral_limit
        self.deadband = deadband
        self.adaptive = adaptive

        self._integral = 0.0
        self._prev_error = 0.0
        self._last_ts = time.perf_counter()
        self._first_call = True
        self._d_term_filtered = 0.0
        self._ema_alpha = 0.3
        self._oscillation_count = 0
        self._last_sign: int | None = None
        self._adaptive_kp_scale = 1.0

    def update_params(
        self,
        kp: float,
        ki: float,
        kd: float,
        deadband: float,
        adaptive: bool,
        integral_limit: float | None = None,
    ):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.deadband = deadband
        self.adaptive = adaptive
        if integral_limit is not None:
            self.integral_limit = integral_limit

    def update(self, current: float, target: float) -> float:
        now = time.perf_counter()
        dt = now - self._last_ts
        self._last_ts = now

        if self._first_call:
            self._first_call = False
            dt = 0.033

        if dt < 1e-6:
            dt = 1e-6

        error = target - current

        if abs(error) >= self.deadband:
            self._integral += error * dt
            self._integral = max(
                -self.integral_limit,
                min(self.integral_limit, self._integral),
            )
        else:
            self._integral *= 0.9

        raw_derivative = (error - self._prev_error) / dt
        self._d_term_filtered = (
            self._ema_alpha * raw_derivative
            + (1.0 - self._ema_alpha) * self._d_term_filtered
        )

        current_kp = self.kp
        if self.adaptive:
            current_sign = 1 if error > 0 else -1
            if self._last_sign is not None and current_sign != self._last_sign and abs(error) < 50:
                self._oscillation_count += 1
                self._last_sign = current_sign

            if self._oscillation_count > 3:
                self._adaptive_kp_scale = max(0.4, self._adaptive_kp_scale * 0.9)
                self._oscillation_count = 0
            else:
                self._adaptive_kp_scale = min(1.0, self._adaptive_kp_scale + 0.05)

            distance_scale = min(1.0, abs(error) / 40.0)
            current_kp = (
                self.kp
                * self._adaptive_kp_scale
                * (0.6 + 0.4 * distance_scale)
            )

        self._prev_error = error
        return (
            current_kp * error
            + self.ki * self._integral
            + self.kd * self._d_term_filtered
        )

    def reset(self) -> None:
        self._integral = 0.0
        self._prev_error = 0.0
        self._last_ts = time.perf_counter()
        self._first_call = True
        self._d_term_filtered = 0.0
        self._oscillation_count = 0
        self._last_sign = None
        self._adaptive_kp_scale = 1.0


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

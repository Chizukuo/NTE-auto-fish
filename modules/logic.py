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
        ema_alpha: float = 0.25,
        max_dt: float = 0.1,
    ) -> None:
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.integral_limit = integral_limit
        self.deadband = deadband
        self.adaptive = adaptive
        self.ema_alpha = ema_alpha
        self.max_dt = max_dt

        self._integral = 0.0
        self._prev_measurement = 0.0
        self._last_ts = time.perf_counter()
        self._first_call = True
        self._d_term_filtered = 0.0

        # Adaptive state
        self._last_sign: int | None = None
        self._sign_changes: list[float] = []  # timestamps of sign changes
        self._adaptive_kp_scale = 1.0

    def update_params(
        self,
        kp: float,
        ki: float,
        kd: float,
        deadband: float,
        adaptive: bool,
        integral_limit: float | None = None,
        ema_alpha: float | None = None,
        max_dt: float | None = None,
    ):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.deadband = deadband
        self.adaptive = adaptive
        if integral_limit is not None:
            self.integral_limit = integral_limit
        if ema_alpha is not None:
            self.ema_alpha = ema_alpha
        if max_dt is not None:
            self.max_dt = max_dt

    def update(self, current: float, target: float, bar_half_width: float = 200.0) -> float:
        now = time.perf_counter()
        dt = now - self._last_ts
        self._last_ts = now

        if self._first_call:
            self._first_call = False
            dt = 0.033
            self._prev_measurement = current

        dt = max(1e-6, min(dt, self.max_dt))

        error = target - current

        # --- P term ---
        current_kp = self.kp
        if self.adaptive:
            current_sign = 1 if error > 0 else -1
            if self._last_sign is not None and current_sign != self._last_sign:
                self._sign_changes.append(now)
                # Keep only the last 8 sign changes
                if len(self._sign_changes) > 8:
                    self._sign_changes = self._sign_changes[-8:]
            self._last_sign = current_sign

            # Oscillation: 4+ sign changes within 2 seconds
            recent = [t for t in self._sign_changes if now - t < 2.0]
            if len(recent) >= 4:
                self._adaptive_kp_scale = max(0.4, self._adaptive_kp_scale * 0.95)
                self._sign_changes.clear()
            else:
                self._adaptive_kp_scale = min(1.0, self._adaptive_kp_scale + 0.02)

            # Distance scaling normalized to bar half-width
            distance_scale = min(1.0, abs(error) / max(bar_half_width, 1.0))
            current_kp = self.kp * self._adaptive_kp_scale * (0.5 + 0.5 * distance_scale)

        kp_term = current_kp * error

        # --- D term (derivative on measurement to avoid setpoint kick) ---
        raw_derivative = -(current - self._prev_measurement) / dt
        self._d_term_filtered = (
            self.ema_alpha * raw_derivative
            + (1.0 - self.ema_alpha) * self._d_term_filtered
        )
        kd_term = self.kd * self._d_term_filtered
        self._prev_measurement = current

        # --- I term with conditional integration (anti-windup) ---
        ki_term = self.ki * self._integral
        output_unscaled = kp_term + ki_term + kd_term

        # Only integrate when output is not saturated
        if abs(output_unscaled) < self.integral_limit * 2:
            if abs(error) >= self.deadband:
                self._integral += error * dt
                self._integral = max(
                    -self.integral_limit,
                    min(self.integral_limit, self._integral),
                )
            else:
                self._integral *= 0.9
        ki_term = self.ki * self._integral

        return kp_term + ki_term + kd_term

    def reset(self) -> None:
        self._integral = 0.0
        self._prev_measurement = 0.0
        self._last_ts = time.perf_counter()
        self._first_call = True
        self._d_term_filtered = 0.0
        self._last_sign = None
        self._sign_changes.clear()
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

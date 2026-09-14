"""
Timing validation.

Wraps the raw latency numbers (stimulus-sent monotonic timestamp vs.
signal-observed monotonic timestamp) with named requirement thresholds, so
test code reads like the requirement it's checking rather than a bag of
time.monotonic() arithmetic.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TimingResult:
    requirement_name: str
    measured_s: float
    max_allowed_s: float

    @property
    def passed(self) -> bool:
        return self.measured_s <= self.max_allowed_s

    @property
    def measured_ms(self) -> float:
        return self.measured_s * 1000.0

    @property
    def max_allowed_ms(self) -> float:
        return self.max_allowed_s * 1000.0

    def __str__(self) -> str:
        verdict = "PASS" if self.passed else "FAIL"
        return (
            f"[{verdict}] {self.requirement_name}: measured={self.measured_ms:.1f}ms "
            f"limit={self.max_allowed_ms:.1f}ms"
        )


class TimingValidator:
    """Requirement thresholds for AEB response timing (illustrative values --
    in a real project these trace back to the ADAS functional safety /
    requirements spec, e.g. ISO 26262-derived timing budgets)."""

    REQUIREMENTS_S = {
        "warning_response": 0.30,
        "partial_brake_response": 0.30,
        "full_brake_response": 0.30,
        "fault_detection": 0.65,        # stale_timeout_s (0.50) + one ECU cycle + margin
        "recovery_response": 0.30,
    }

    @classmethod
    def evaluate(cls, requirement_name: str, send_ts: float, observed_ts: float) -> TimingResult:
        if requirement_name not in cls.REQUIREMENTS_S:
            raise KeyError(f"Unknown timing requirement '{requirement_name}'")
        measured = observed_ts - send_ts
        return TimingResult(requirement_name, measured, cls.REQUIREMENTS_S[requirement_name])

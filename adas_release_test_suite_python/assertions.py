from __future__ import annotations

import os
from typing import Any


def assert_prediction(case_id: str, expected: dict[str, Any], actual: dict[str, Any]) -> None:
    assert isinstance(actual, dict), f"[{case_id}] actual response must be dict"
    assert "status" in actual, f"[{case_id}] actual response missing 'status'"
    assert "signals" in actual, f"[{case_id}] actual response missing 'signals'"
    assert isinstance(actual["signals"], dict), f"[{case_id}] 'signals' must be dict"

    exp_status = expected.get("status")
    act_status = actual.get("status")
    assert exp_status == act_status, (
        f"[{case_id}] status mismatch: expected={exp_status}, actual={act_status}"
    )

    exp_signals = expected.get("signals", {})
    act_signals = actual.get("signals", {})

    for key, exp_value in exp_signals.items():
        assert key in act_signals, f"[{case_id}] missing signal '{key}' in actual output"
        act_value = act_signals[key]
        assert isinstance(act_value, type(exp_value)), (
            f"[{case_id}] signal type mismatch for '{key}': "
            f"expected={type(exp_value).__name__}, actual={type(act_value).__name__}"
        )
        assert exp_value == act_value, (
            f"[{case_id}] signal mismatch for '{key}': expected={exp_value}, actual={act_value}"
        )

    strict_signals = os.getenv("ADAS_STRICT_SIGNALS", "0").strip() == "1"
    if strict_signals:
        extra = sorted(set(act_signals.keys()) - set(exp_signals.keys()))
        assert not extra, f"[{case_id}] unexpected extra signals in actual output: {extra}"

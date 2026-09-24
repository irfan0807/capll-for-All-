"""
AEB state-machine validator.

Encodes which AEB_State transitions are legal so tests can assert not just
"did it reach FULL_BRAKE" but "did it get there through a sane sequence"
(e.g. flagging an ECU that jumps straight from IDLE to FULL_BRAKE without
ever asserting WARNING, which would be a real requirements violation even
though the final state looks correct).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from src.simulation.ecu_sim import AebState

# Adjacency list of allowed direct transitions. FAULT is reachable from any
# state (a real fault can occur at any time); recovery from FAULT back to
# IDLE is allowed once the ECU re-validates its inputs.
ALLOWED_TRANSITIONS = {
    AebState.IDLE: {AebState.IDLE, AebState.WARNING, AebState.FAULT},
    AebState.WARNING: {AebState.WARNING, AebState.IDLE, AebState.PARTIAL_BRAKE, AebState.FAULT},
    AebState.PARTIAL_BRAKE: {AebState.PARTIAL_BRAKE, AebState.WARNING, AebState.FULL_BRAKE, AebState.IDLE, AebState.FAULT},
    AebState.FULL_BRAKE: {AebState.FULL_BRAKE, AebState.PARTIAL_BRAKE, AebState.IDLE, AebState.FAULT},
    AebState.FAULT: {AebState.FAULT, AebState.IDLE},
}


@dataclass
class TransitionViolation:
    index: int
    from_state: AebState
    to_state: AebState

    def __str__(self) -> str:
        return f"Illegal transition at step {self.index}: {self.from_state.name} -> {self.to_state.name}"


@dataclass
class StateMachineValidator:
    observed: List[AebState] = field(default_factory=list)

    def record(self, state: AebState) -> None:
        self.observed.append(state)

    def violations(self) -> List[TransitionViolation]:
        found = []
        for i in range(1, len(self.observed)):
            prev, cur = self.observed[i - 1], self.observed[i]
            if cur == prev:
                continue  # steady-state heartbeats repeat the same state
            if cur not in ALLOWED_TRANSITIONS.get(prev, set()):
                found.append(TransitionViolation(i, prev, cur))
        return found

    def is_valid(self) -> bool:
        return len(self.violations()) == 0

    def sequence_names(self) -> List[str]:
        # De-duplicated consecutive states -- the "shape" of the run.
        out: List[str] = []
        for s in self.observed:
            if not out or out[-1] != s.name:
                out.append(s.name)
        return out

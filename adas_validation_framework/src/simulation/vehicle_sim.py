"""
Host vehicle dynamics simulator -- provides the VehicleDynamics context frame
(speed, yaw rate) that a real AEB ECU would fuse with object TTC before
deciding to brake (e.g. AEB is typically suppressed below a minimum host
speed). Kept separate from SensorSimulator because in a real vehicle these
come from a different ECU (ESC/ABS) on the bus.
"""
from __future__ import annotations

import time

from src.can_comm.can_interface import CanInterface
from src.dbc_layer.dbc_decoder import DbcDecoder
from src.utils.logger import get_logger

log = get_logger("vehicle_sim")

MESSAGE_NAME = "VehicleDynamics"


class VehicleSimulator:
    def __init__(self, can_if: CanInterface, decoder: DbcDecoder):
        self._can_if = can_if
        self._decoder = decoder
        self._msg_id = decoder.id_for(MESSAGE_NAME)

    def send_speed(self, speed_kph: float, yaw_rate_degps: float = 0.0) -> float:
        signals = {"VehicleSpeed_kph": speed_kph, "YawRate_degps": yaw_rate_degps}
        data = self._decoder.encode(MESSAGE_NAME, signals)
        send_ts = time.monotonic()
        self._can_if.send(self._msg_id, data)
        log.info("Set host vehicle speed=%.1fkph yaw=%.2fdeg/s", speed_kph, yaw_rate_degps)
        return send_ts

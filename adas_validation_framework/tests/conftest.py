"""
Shared pytest fixtures for the AEB validation suite.

Fixture chain (function-scoped, so every test gets a fresh bus / ECU /
signal store -- no state leaks between test cases):

    can_bus -> can_listener -> ecu_sim -> aeb_api

Each test gets its own uniquely-named virtual CAN channel so tests can, in
principle, run with pytest-xdist in parallel without cross-talk.
"""
from __future__ import annotations

import uuid

import pytest

from src.adas_api.aeb_api import AebTestAPI
from src.can_comm.can_interface import CanInterface
from src.can_comm.can_listener import BackgroundCanListener
from src.can_comm.signal_store import SignalStore
from src.dbc_layer.dbc_decoder import DbcDecoder
from src.simulation.ecu_sim import AebEcuSimulator, EcuThresholds, STATUS_MESSAGE, SENSOR_MESSAGE, VEHICLE_MESSAGE
from src.utils.logger import get_logger

log = get_logger("conftest")


@pytest.fixture(scope="session")
def dbc_decoder() -> DbcDecoder:
    """DBC is stateless/read-only -- safe and cheap to share across the session."""
    return DbcDecoder()


@pytest.fixture()
def can_channel() -> str:
    """A fresh virtual-bus channel name per test = full test isolation."""
    return f"aeb_test_{uuid.uuid4().hex[:8]}"


@pytest.fixture()
def can_bus(can_channel, dbc_decoder):
    """The tester-side CAN interface (this is the framework's own node on
    the bus, separate from the simulated ECU's node)."""
    log.info("=== SETUP: connecting tester CAN interface on '%s' ===", can_channel)
    iface = CanInterface(channel=can_channel, interface="virtual")
    iface.connect()
    yield iface
    log.info("=== TEARDOWN: disconnecting tester CAN interface ===")
    iface.disconnect()


@pytest.fixture()
def signal_store() -> SignalStore:
    return SignalStore()


@pytest.fixture()
def can_listener(can_bus, dbc_decoder, signal_store):
    """Background listener decoding everything the DBC knows about."""
    allow_ids = [
        dbc_decoder.id_for(STATUS_MESSAGE),
        dbc_decoder.id_for(SENSOR_MESSAGE),
        dbc_decoder.id_for(VEHICLE_MESSAGE),
    ]
    listener = BackgroundCanListener(can_bus, dbc_decoder, signal_store, allow_ids=allow_ids)
    listener.start()
    yield listener
    listener.stop()
    log.info("Listener stats: %s", listener.stats)


@pytest.fixture()
def ecu_thresholds() -> EcuThresholds:
    """Override in a test with @pytest.mark.parametrize / direct instantiation
    if a scenario needs non-default thresholds; default here covers the
    common case."""
    return EcuThresholds()


@pytest.fixture()
def ecu_sim(can_channel, dbc_decoder, ecu_thresholds):
    """The simulated device under test -- a separate CAN node on the same
    virtual channel as `can_bus`."""
    log.info("=== SETUP: starting simulated AEB ECU ===")
    ecu = AebEcuSimulator(can_channel, dbc_decoder, thresholds=ecu_thresholds)
    ecu.start()
    yield ecu
    log.info("=== TEARDOWN: stopping simulated AEB ECU ===")
    ecu.stop()


@pytest.fixture()
def aeb_api(can_bus, dbc_decoder, signal_store, can_listener, ecu_sim) -> AebTestAPI:
    """The single fixture most tests should depend on -- pulling it in wires
    up the whole bus + ECU + listener stack in the right order."""
    api = AebTestAPI(can_bus, dbc_decoder, signal_store, can_listener)
    # Give the ECU a sane default host speed so AEB is "armed"; tests that
    # care about the speed envelope override this explicitly.
    api.set_host_speed(50.0)
    return api


@pytest.fixture(autouse=True)
def _test_boundary_logging(request):
    log.info("########## START TEST: %s ##########", request.node.name)
    yield
    log.info("########## END TEST:   %s ##########", request.node.name)

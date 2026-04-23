from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Any


@dataclass(frozen=True)
class ADASTestCase:
    case_id: str
    title: str
    feature: str
    tags: tuple[str, ...]
    scenario: dict[str, Any]
    expected: dict[str, Any]


def _edge(value: float, threshold: float, eps: float = 0.1) -> bool:
    return abs(value - threshold) <= eps


def _oracle(feature: str, scenario: dict[str, Any]) -> dict[str, Any]:
    sensor_ok = scenario.get("sensor_ok", True)
    ego_speed = float(scenario.get("ego_speed_mps", 0.0))

    if not sensor_ok:
        return {"status": "FAILSAFE", "signals": {"failsafe": True}}

    if feature == "AEB":
        distance = float(scenario.get("target_distance_m", 999.0))
        closing = float(scenario.get("closing_speed_mps", 0.0))
        if closing <= 0.1 or distance >= 90:
            return {"status": "OK", "signals": {"aeb_warn": False, "aeb_brake": False}}
        ttc = distance / max(closing, 0.1)
        friction = float(scenario.get("road_friction", 0.8))
        brake_ttc = 1.2 if friction >= 0.4 else 1.6
        warn_ttc = 2.5 if friction >= 0.4 else 3.0
        return {
            "status": "OK",
            "signals": {
                "aeb_warn": ttc <= warn_ttc,
                "aeb_brake": ttc <= brake_ttc,
            },
        }

    if feature == "FCW":
        distance = float(scenario.get("target_distance_m", 999.0))
        closing = float(scenario.get("closing_speed_mps", 0.0))
        visibility = float(scenario.get("visibility_m", 150.0))
        if closing <= 0.1:
            return {"status": "OK", "signals": {"fcw_warn": False}}
        ttc = distance / max(closing, 0.1)
        warn = ttc <= 3.0 or (visibility < 40 and ttc <= 4.0)
        return {"status": "OK", "signals": {"fcw_warn": warn}}

    if feature == "ACC":
        set_speed = float(scenario.get("set_speed_mps", ego_speed))
        lead_gap = float(scenario.get("lead_gap_m", 100.0))
        speed_limit = float(scenario.get("speed_limit_kph", 120.0)) / 3.6
        reduce_speed = set_speed > speed_limit + 2.0
        maintain_gap = lead_gap < max(12.0, ego_speed * 1.2)
        return {
            "status": "OK",
            "signals": {
                "acc_reduce_speed": reduce_speed,
                "acc_maintain_gap": maintain_gap,
            },
        }

    if feature == "LKA":
        lane_conf = float(scenario.get("lane_confidence", 1.0))
        lane_offset = float(scenario.get("lane_offset_m", 0.0))
        indicator_on = bool(scenario.get("turn_indicator_on", False))
        intervene = lane_conf >= 0.6 and abs(lane_offset) >= 0.25 and not indicator_on
        return {"status": "OK", "signals": {"lka_intervene": intervene}}

    if feature == "BSD":
        blind_spot_obj = bool(scenario.get("blind_spot_obj", False))
        rel_speed = float(scenario.get("relative_obj_speed_mps", 0.0))
        indicator_on = bool(scenario.get("turn_indicator_on", False))
        warn = blind_spot_obj and indicator_on and rel_speed > -8.0
        return {"status": "OK", "signals": {"bsd_warn": warn}}

    if feature == "TSR":
        sign_detected = bool(scenario.get("sign_detected", False))
        speed_limit = int(scenario.get("speed_limit_kph", 120))
        ego_kph = ego_speed * 3.6
        overspeed_warn = sign_detected and ego_kph > speed_limit + 5
        return {
            "status": "OK",
            "signals": {
                "tsr_detected": sign_detected,
                "tsr_overspeed_warn": overspeed_warn,
            },
        }

    if feature == "DMS":
        eyes_off = float(scenario.get("eyes_off_road_s", 0.0))
        yawning = bool(scenario.get("yawning", False))
        drowsy = eyes_off >= 2.0 or yawning
        takeover = eyes_off >= 4.0
        return {
            "status": "OK",
            "signals": {
                "dms_alert": drowsy,
                "dms_takeover": takeover,
            },
        }

    return {"status": "OK", "signals": {}}


def _case_tags(feature: str, is_smoke: bool, edge_case: bool) -> tuple[str, ...]:
    tags: list[str] = [feature.lower()]
    tags.append("smoke" if is_smoke else "regression")
    if edge_case:
        tags.append("edge")
    return tuple(tags)


def _mk_case(feature: str, idx: int, scenario: dict[str, Any], smoke_cutoff: int, edge_case: bool) -> ADASTestCase:
    is_smoke = idx <= smoke_cutoff
    case_id = f"{feature}-{'SMK' if is_smoke else 'REG'}-{idx:03d}"
    expected = _oracle(feature, scenario)
    title = f"{feature} scenario {idx}"
    return ADASTestCase(
        case_id=case_id,
        title=title,
        feature=feature,
        tags=_case_tags(feature, is_smoke, edge_case),
        scenario=scenario,
        expected=expected,
    )


def _generate_aeb() -> list[ADASTestCase]:
    target = 40
    smoke_cutoff = 10
    cases: list[ADASTestCase] = []
    speeds = [0.0, 1.0, 5.0, 13.9, 22.2, 33.3]
    distances = [2.0, 5.0, 10.0, 20.0, 40.0, 90.0]
    closing = [0.0, 2.0, 5.0, 10.0, 15.0]
    friction = [0.2, 0.4, 0.8]

    i = 0
    for es, d, cs, fr in product(speeds, distances, closing, friction):
        if len(cases) >= target:
            break
        i += 1
        scenario = {
            "ego_speed_mps": es,
            "target_distance_m": d,
            "closing_speed_mps": cs,
            "road_friction": fr,
            "sensor_ok": not (i % 19 == 0),
        }
        edge_case = es in (0.0, 1.0, 33.3) or d in (2.0, 90.0) or _edge(fr, 0.4)
        cases.append(_mk_case("AEB", i, scenario, smoke_cutoff, edge_case))
    return cases


def _generate_fcw() -> list[ADASTestCase]:
    target = 35
    smoke_cutoff = 7
    cases: list[ADASTestCase] = []
    speeds = [0.0, 5.0, 13.9, 25.0]
    distances = [3.0, 8.0, 15.0, 30.0, 60.0]
    closing = [0.0, 3.0, 6.0, 12.0]
    visibility = [20.0, 40.0, 80.0, 150.0]

    i = 0
    for es, d, cs, vis in product(speeds, distances, closing, visibility):
        if len(cases) >= target:
            break
        i += 1
        scenario = {
            "ego_speed_mps": es,
            "target_distance_m": d,
            "closing_speed_mps": cs,
            "visibility_m": vis,
            "sensor_ok": not (i % 17 == 0),
        }
        edge_case = d in (3.0, 60.0) or vis in (20.0, 40.0) or cs in (0.0, 12.0)
        cases.append(_mk_case("FCW", i, scenario, smoke_cutoff, edge_case))
    return cases


def _generate_acc() -> list[ADASTestCase]:
    target = 35
    smoke_cutoff = 7
    cases: list[ADASTestCase] = []
    ego = [8.3, 13.9, 22.2, 30.0]
    set_speeds = [10.0, 13.9, 25.0, 35.0]
    gaps = [8.0, 12.0, 20.0, 35.0, 70.0]
    limits = [30, 50, 80, 120]

    i = 0
    for es, ss, gap, lim in product(ego, set_speeds, gaps, limits):
        if len(cases) >= target:
            break
        i += 1
        scenario = {
            "ego_speed_mps": es,
            "set_speed_mps": ss,
            "lead_gap_m": gap,
            "speed_limit_kph": lim,
            "sensor_ok": not (i % 23 == 0),
        }
        edge_case = gap in (8.0, 12.0) or lim in (30, 120)
        cases.append(_mk_case("ACC", i, scenario, smoke_cutoff, edge_case))
    return cases


def _generate_lka() -> list[ADASTestCase]:
    target = 35
    smoke_cutoff = 7
    cases: list[ADASTestCase] = []
    speeds = [5.0, 12.0, 22.2, 30.5]
    offsets = [-0.45, -0.25, -0.1, 0.1, 0.25, 0.45]
    confs = [0.4, 0.59, 0.6, 0.8, 1.0]
    indicators = [False, True]

    i = 0
    for es, off, conf, ind in product(speeds, offsets, confs, indicators):
        if len(cases) >= target:
            break
        i += 1
        scenario = {
            "ego_speed_mps": es,
            "lane_offset_m": off,
            "lane_confidence": conf,
            "turn_indicator_on": ind,
            "sensor_ok": not (i % 29 == 0),
        }
        edge_case = _edge(abs(off), 0.25, 0.01) or _edge(conf, 0.6, 0.01)
        cases.append(_mk_case("LKA", i, scenario, smoke_cutoff, edge_case))
    return cases


def _generate_bsd() -> list[ADASTestCase]:
    target = 35
    smoke_cutoff = 7
    cases: list[ADASTestCase] = []
    speeds = [8.0, 16.0, 25.0]
    obj_presence = [False, True]
    rel_speed = [-12.0, -8.0, -2.0, 0.0, 4.0]
    indicators = [False, True]

    i = 0
    for es, obj, rs, ind in product(speeds, obj_presence, rel_speed, indicators):
        if len(cases) >= target:
            break
        i += 1
        scenario = {
            "ego_speed_mps": es,
            "blind_spot_obj": obj,
            "relative_obj_speed_mps": rs,
            "turn_indicator_on": ind,
            "sensor_ok": not (i % 13 == 0),
        }
        edge_case = rs in (-8.0, 0.0) or (obj and ind)
        cases.append(_mk_case("BSD", i, scenario, smoke_cutoff, edge_case))
    return cases


def _generate_tsr() -> list[ADASTestCase]:
    target = 35
    smoke_cutoff = 7
    cases: list[ADASTestCase] = []
    ego_kph = [20, 30, 35, 50, 55, 80, 90, 130]
    limits = [30, 50, 80, 120]
    sign_detected = [False, True]

    i = 0
    for ek, lim, detected in product(ego_kph, limits, sign_detected):
        if len(cases) >= target:
            break
        i += 1
        scenario = {
            "ego_speed_mps": ek / 3.6,
            "speed_limit_kph": lim,
            "sign_detected": detected,
            "sensor_ok": not (i % 31 == 0),
        }
        edge_case = ek in (30, 35, 50, 55, 80, 90) or lim in (30, 120)
        cases.append(_mk_case("TSR", i, scenario, smoke_cutoff, edge_case))
    return cases


def _generate_dms() -> list[ADASTestCase]:
    target = 35
    smoke_cutoff = 5
    cases: list[ADASTestCase] = []
    speeds = [0.0, 8.3, 16.6, 27.7]
    eyes_off = [0.0, 1.9, 2.0, 3.5, 4.0, 5.0]
    yawning = [False, True]

    i = 0
    for es, eye, yaw in product(speeds, eyes_off, yawning):
        if len(cases) >= target:
            break
        i += 1
        scenario = {
            "ego_speed_mps": es,
            "eyes_off_road_s": eye,
            "yawning": yaw,
            "sensor_ok": not (i % 27 == 0),
        }
        edge_case = eye in (1.9, 2.0, 4.0)
        cases.append(_mk_case("DMS", i, scenario, smoke_cutoff, edge_case))
    return cases


def build_catalog() -> list[ADASTestCase]:
    catalog = (
        _generate_aeb()
        + _generate_fcw()
        + _generate_acc()
        + _generate_lka()
        + _generate_bsd()
        + _generate_tsr()
        + _generate_dms()
    )

    if len(catalog) != 250:
        raise ValueError(f"Catalog size must be 250, got {len(catalog)}")

    smoke_count = sum("smoke" in c.tags for c in catalog)
    regression_count = sum("regression" in c.tags for c in catalog)
    if smoke_count != 50 or regression_count != 200:
        raise ValueError(
            f"Expected smoke/regression = 50/200, got {smoke_count}/{regression_count}"
        )

    ids = [c.case_id for c in catalog]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate case IDs found")

    return catalog


CATALOG = build_catalog()
SMOKE_CASES = [c for c in CATALOG if "smoke" in c.tags]
REGRESSION_CASES = [c for c in CATALOG if "regression" in c.tags]

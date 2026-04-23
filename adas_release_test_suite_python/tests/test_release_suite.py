from __future__ import annotations

import pytest

from assertions import assert_prediction
from test_catalog import CATALOG, REGRESSION_CASES, SMOKE_CASES


def _marks_for_case(case):
    marks = []
    for tag in case.tags:
        if hasattr(pytest.mark, tag):
            marks.append(getattr(pytest.mark, tag))
    return marks


def _params(cases):
    params = []
    for case in cases:
        params.append(
            pytest.param(
                case,
                id=case.case_id,
                marks=_marks_for_case(case),
            )
        )
    return params


@pytest.mark.parametrize("case", _params(SMOKE_CASES))
def test_smoke_release(case, sut):
    actual = sut.predict(case.feature, case.scenario)
    assert_prediction(case.case_id, case.expected, actual)


@pytest.mark.parametrize("case", _params(REGRESSION_CASES))
def test_regression_release(case, sut):
    actual = sut.predict(case.feature, case.scenario)
    assert_prediction(case.case_id, case.expected, actual)


def test_catalog_size_and_split():
    assert len(CATALOG) == 250
    assert len(SMOKE_CASES) == 50
    assert len(REGRESSION_CASES) == 200


def test_edge_coverage_exists():
    edge_cases = [c for c in CATALOG if "edge" in c.tags]
    assert len(edge_cases) >= 100, "Expected broad edge coverage across catalog"

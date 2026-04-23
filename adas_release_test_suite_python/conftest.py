from __future__ import annotations

import pytest

from sut_adapter import ADASSUTAdapter


@pytest.fixture(scope="session")
def sut() -> ADASSUTAdapter:
    return ADASSUTAdapter()

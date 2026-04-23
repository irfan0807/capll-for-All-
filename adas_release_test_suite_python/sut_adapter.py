from __future__ import annotations

import os
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from test_catalog import _oracle


class ADASSUTAdapter:
    def __init__(self) -> None:
        self.mode = os.getenv("ADAS_SUT_MODE", "mock").strip().lower()
        self.url = os.getenv("ADAS_SUT_URL", "").strip()
        self.timeout_s = float(os.getenv("ADAS_SUT_TIMEOUT_S", "8"))
        self.retries = int(os.getenv("ADAS_SUT_HTTP_RETRIES", "2"))
        self.backoff_s = float(os.getenv("ADAS_SUT_BACKOFF_S", "0.2"))
        self.session = requests.Session()

        retry = Retry(
            total=self.retries,
            backoff_factor=self.backoff_s,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(["POST"]),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def predict(self, feature: str, scenario: dict[str, Any]) -> dict[str, Any]:
        if self.mode == "http":
            if not self.url:
                raise RuntimeError("ADAS_SUT_URL is required when ADAS_SUT_MODE=http")
            return self._predict_http(feature, scenario)
        return self._predict_mock(feature, scenario)

    def _predict_mock(self, feature: str, scenario: dict[str, Any]) -> dict[str, Any]:
        return _oracle(feature, scenario)

    def _predict_http(self, feature: str, scenario: dict[str, Any]) -> dict[str, Any]:
        payload = {"feature": feature, "scenario": scenario}
        response = self.session.post(self.url, json=payload, timeout=self.timeout_s)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("Invalid SUT response: body must be JSON object")
        if "status" not in data or "signals" not in data:
            raise ValueError("Invalid SUT response: must contain 'status' and 'signals'")
        if not isinstance(data["signals"], dict):
            raise ValueError("Invalid SUT response: 'signals' must be an object")
        if not isinstance(data["status"], str):
            raise ValueError("Invalid SUT response: 'status' must be a string")
        return data

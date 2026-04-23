from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st


ROOT = Path(__file__).parent
REPORTS_DIR = ROOT / "reports"


def _run_gate(build_id: str, suite: str, min_pass_rate: float, max_failures: int, max_errors: int) -> tuple[int, str]:
    cmd = [
        sys.executable,
        "run_release_gate.py",
        "--suite",
        suite,
        "--build-id",
        build_id,
        "--min-pass-rate",
        str(min_pass_rate),
        "--max-failures",
        str(max_failures),
        "--max-errors",
        str(max_errors),
    ]

    process = subprocess.Popen(
        cmd,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    lines: list[str] = []
    if process.stdout:
        for line in process.stdout:
            lines.append(line)
    process.wait()
    return process.returncode, "".join(lines)


def _load_recent_runs(limit: int = 25) -> list[dict[str, Any]]:
    if not REPORTS_DIR.exists():
        return []

    rows: list[dict[str, Any]] = []
    for build_dir in REPORTS_DIR.iterdir():
        if not build_dir.is_dir():
            continue
        for run_dir in build_dir.iterdir():
            summary_path = run_dir / "summary.json"
            if not summary_path.exists():
                continue
            try:
                summary = json.loads(summary_path.read_text(encoding="utf-8"))
                row = {
                    "build_id": summary.get("build_id", ""),
                    "suite": summary.get("suite", ""),
                    "status": summary.get("status", ""),
                    "tests": summary.get("stats", {}).get("tests", 0),
                    "failures": summary.get("stats", {}).get("failures", 0),
                    "errors": summary.get("stats", {}).get("errors", 0),
                    "pass_rate": summary.get("gate", {}).get("pass_rate_percent", 0),
                    "generated_at": summary.get("generated_at", ""),
                    "summary_path": str(summary_path),
                    "html_report": str((run_dir / "report.html").resolve()),
                    "junit": str((run_dir / "junit.xml").resolve()),
                }
                rows.append(row)
            except (json.JSONDecodeError, OSError):
                continue

    rows.sort(key=lambda x: x.get("generated_at", ""), reverse=True)
    return rows[:limit]


def _default_build_id() -> str:
    return f"adas-{datetime.now().strftime('%Y.%m.%d')}-prod"


def main() -> None:
    st.set_page_config(page_title="ADAS Release Test UI", layout="wide")
    st.title("ADAS Release Test Execution UI")
    st.caption("Run smoke/regression/all suites and inspect execution output + reports")

    with st.sidebar:
        st.header("Run Configuration")
        suite = st.selectbox("Suite", ["smoke", "regression", "all"], index=0)
        build_id = st.text_input("Build ID", value=_default_build_id())
        min_pass_rate = st.number_input("Min pass rate (%)", min_value=0.0, max_value=100.0, value=100.0, step=0.1)
        max_failures = st.number_input("Max failures", min_value=0, max_value=1000, value=0, step=1)
        max_errors = st.number_input("Max errors", min_value=0, max_value=1000, value=0, step=1)

        st.subheader("SUT Mode")
        sut_mode = st.selectbox("ADAS_SUT_MODE", ["mock", "http"], index=0)
        sut_url = st.text_input("ADAS_SUT_URL", value=os.getenv("ADAS_SUT_URL", ""))
        strict_signals = st.checkbox("Strict signals (fail on extra keys)", value=False)

        run_clicked = st.button("Run Test Suite", type="primary", use_container_width=True)

    if run_clicked:
        os.environ["ADAS_SUT_MODE"] = sut_mode
        if sut_url.strip():
            os.environ["ADAS_SUT_URL"] = sut_url.strip()
        elif "ADAS_SUT_URL" in os.environ:
            del os.environ["ADAS_SUT_URL"]

        os.environ["ADAS_STRICT_SIGNALS"] = "1" if strict_signals else "0"

        with st.spinner("Executing release gate..."):
            rc, logs = _run_gate(
                build_id=build_id.strip(),
                suite=suite,
                min_pass_rate=float(min_pass_rate),
                max_failures=int(max_failures),
                max_errors=int(max_errors),
            )

        if rc == 0:
            st.success("Test gate PASSED")
        else:
            st.error("Test gate FAILED")

        st.subheader("Execution Log")
        st.code(logs or "No output captured", language="bash")

    st.divider()
    st.subheader("Recent Runs")

    runs = _load_recent_runs(limit=25)
    if not runs:
        st.info("No run artifacts found yet. Execute a suite to populate history.")
        return

    for run in runs:
        col1, col2, col3 = st.columns([3, 2, 2])
        with col1:
            st.markdown(
                f"**{run['build_id']}** · `{run['suite']}` · `{run['status']}`  \\n"
                f"Tests: {run['tests']} | Failures: {run['failures']} | Errors: {run['errors']} | Pass rate: {run['pass_rate']}%"
            )
            st.caption(f"Generated: {run['generated_at']}")
        with col2:
            st.link_button("Open HTML Report", f"file://{run['html_report']}", use_container_width=True)
        with col3:
            st.link_button("Open JUnit XML", f"file://{run['junit']}", use_container_width=True)


if __name__ == "__main__":
    main()

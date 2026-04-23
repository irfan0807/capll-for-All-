from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from xml.etree import ElementTree as ET


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run ADAS release gate with versioned JUnit + HTML reports"
    )
    parser.add_argument(
        "--suite",
        choices=["smoke", "regression", "all"],
        default="all",
        help="Test scope to run",
    )
    parser.add_argument(
        "--build-id",
        default=os.getenv("BUILD_ID", "local-build"),
        help="Build identifier (e.g., adas-2026.04.23-rc1)",
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python executable for pytest invocation",
    )
    parser.add_argument(
        "--min-pass-rate",
        type=float,
        default=float(os.getenv("ADAS_MIN_PASS_RATE", "100")),
        help="Minimum required pass rate percentage for gate success",
    )
    parser.add_argument(
        "--max-failures",
        type=int,
        default=int(os.getenv("ADAS_MAX_FAILURES", "0")),
        help="Maximum allowed failed tests for gate success",
    )
    parser.add_argument(
        "--max-errors",
        type=int,
        default=int(os.getenv("ADAS_MAX_ERRORS", "0")),
        help="Maximum allowed test errors for gate success",
    )
    return parser.parse_args()


def marker_for_suite(suite: str) -> str | None:
    if suite == "all":
        return None
    return suite


def create_report_paths(build_id: str, suite: str) -> dict[str, Path]:
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    base = Path("reports") / build_id / f"{suite}_{timestamp}"
    artifacts = {
        "base": base,
        "junit": base / "junit.xml",
        "html": base / "report.html",
        "summary": base / "summary.json",
    }
    base.mkdir(parents=True, exist_ok=True)
    return artifacts


def build_pytest_cmd(python_exec: str, suite: str, paths: dict[str, Path]) -> list[str]:
    cmd: list[str] = [
        python_exec,
        "-m",
        "pytest",
        "tests/test_release_suite.py",
        f"--junitxml={paths['junit']}",
        f"--html={paths['html']}",
        "--self-contained-html",
    ]

    marker = marker_for_suite(suite)
    if marker:
        cmd.extend(["-m", marker])

    return cmd


def run_pytest(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=True)


def compute_pass_rate(stats: dict[str, int]) -> float:
    tests = max(stats.get("tests", 0), 0)
    failures = max(stats.get("failures", 0), 0)
    errors = max(stats.get("errors", 0), 0)
    skipped = max(stats.get("skipped", 0), 0)

    executed = max(tests - skipped, 0)
    passed = max(executed - failures - errors, 0)
    if executed == 0:
        return 0.0
    return round((passed / executed) * 100.0, 2)


def evaluate_thresholds(
    stats: dict[str, int],
    min_pass_rate: float,
    max_failures: int,
    max_errors: int,
) -> tuple[bool, list[str], float]:
    pass_rate = compute_pass_rate(stats)
    violations: list[str] = []
    if pass_rate < min_pass_rate:
        violations.append(f"pass_rate {pass_rate}% < min_pass_rate {min_pass_rate}%")
    if stats.get("failures", 0) > max_failures:
        violations.append(
            f"failures {stats.get('failures', 0)} > max_failures {max_failures}"
        )
    if stats.get("errors", 0) > max_errors:
        violations.append(f"errors {stats.get('errors', 0)} > max_errors {max_errors}")
    return (len(violations) == 0, violations, pass_rate)


def parse_junit(junit_xml: Path) -> dict[str, int]:
    if not junit_xml.exists():
        return {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}

    root = ET.parse(junit_xml).getroot()

    if root.tag == "testsuites":
        tests = int(root.attrib.get("tests", 0))
        failures = int(root.attrib.get("failures", 0))
        errors = int(root.attrib.get("errors", 0))
        skipped = int(root.attrib.get("skipped", 0))

        if tests == failures == errors == skipped == 0:
            suite_nodes = list(root.findall("testsuite"))
            tests = sum(int(node.attrib.get("tests", 0)) for node in suite_nodes)
            failures = sum(int(node.attrib.get("failures", 0)) for node in suite_nodes)
            errors = sum(int(node.attrib.get("errors", 0)) for node in suite_nodes)
            skipped = sum(int(node.attrib.get("skipped", 0)) for node in suite_nodes)

        return {
            "tests": tests,
            "failures": failures,
            "errors": errors,
            "skipped": skipped,
        }

    if root.tag == "testsuite":
        return {
            "tests": int(root.attrib.get("tests", 0)),
            "failures": int(root.attrib.get("failures", 0)),
            "errors": int(root.attrib.get("errors", 0)),
            "skipped": int(root.attrib.get("skipped", 0)),
        }

    return {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}


def write_summary(
    suite: str,
    build_id: str,
    cmd: list[str],
    paths: dict[str, Path],
    result: subprocess.CompletedProcess[str],
    duration_s: float,
    gate_passed: bool,
    violations: list[str],
    pass_rate: float,
    thresholds: dict[str, float | int],
) -> dict[str, object]:
    stats = parse_junit(paths["junit"])
    status = "PASSED" if gate_passed else "FAILED"

    payload: dict[str, object] = {
        "build_id": build_id,
        "suite": suite,
        "status": status,
        "return_code": result.returncode,
        "gate": {
            "passed": gate_passed,
            "violations": violations,
            "thresholds": thresholds,
            "pass_rate_percent": pass_rate,
        },
        "stats": stats,
        "duration_seconds": round(duration_s, 3),
        "command": cmd,
        "artifacts": {
            "junit": str(paths["junit"]),
            "html": str(paths["html"]),
        },
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }

    paths["summary"].write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def main() -> int:
    args = parse_args()
    paths = create_report_paths(args.build_id, args.suite)

    cmd = build_pytest_cmd(args.python, args.suite, paths)
    start = time.perf_counter()
    result = run_pytest(cmd)
    duration_s = time.perf_counter() - start

    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    stats = parse_junit(paths["junit"])
    gate_passed, violations, pass_rate = evaluate_thresholds(
        stats=stats,
        min_pass_rate=args.min_pass_rate,
        max_failures=args.max_failures,
        max_errors=args.max_errors,
    )

    thresholds = {
        "min_pass_rate": args.min_pass_rate,
        "max_failures": args.max_failures,
        "max_errors": args.max_errors,
    }

    summary = write_summary(
        args.suite,
        args.build_id,
        cmd,
        paths,
        result,
        duration_s,
        gate_passed and result.returncode == 0,
        violations,
        pass_rate,
        thresholds,
    )

    print("=== ADAS RELEASE GATE SUMMARY ===")
    print(json.dumps(summary, indent=2))

    if not summary["gate"]["passed"]:
        return 1
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())

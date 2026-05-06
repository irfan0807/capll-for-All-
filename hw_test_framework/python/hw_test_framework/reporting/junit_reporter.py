"""
hw_test_framework/reporting/junit_reporter.py

JUnit XML reporter — compatible with Jenkins, GitHub Actions, GitLab CI.
"""

from __future__ import annotations

import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List

from ..framework.test_case import TestResult, TestStatus
from ..framework.test_runner import SuiteResult


def _escape(text: str) -> str:
    if not text:
        return ""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;"))


def write_junit(suite_results: List[SuiteResult], output_path: str) -> None:
    """Write one or more SuiteResults to a JUnit XML file."""
    root = ET.Element("testsuites")

    for suite in suite_results:
        ts = ET.SubElement(root, "testsuite")
        ts.set("name",      suite.suite_name)
        ts.set("tests",     str(suite.total))
        ts.set("failures",  str(suite.failed))
        ts.set("errors",    str(suite.errors))
        ts.set("skipped",   str(suite.skipped))
        ts.set("time",      f"{suite.duration_ms / 1000:.3f}")
        ts.set("timestamp", time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(suite.start_time)))

        for result in suite.results:
            tc = ET.SubElement(ts, "testcase")
            tc.set("name",      result.test_name)
            tc.set("classname", result.metadata.get("feature", "general"))
            tc.set("time",      f"{result.duration_ms / 1000:.3f}")

            if result.status == TestStatus.FAIL:
                failure = ET.SubElement(tc, "failure")
                failure.set("message", _escape(result.error_message))
                failure.set("type", "AssertionError")
                # Include step details
                step_detail = "\n".join(
                    f"  Step {s.step_number} [{s.status.name}]: {s.description}"
                    + (f"\n    {s.message}" if s.message else "")
                    for s in result.steps
                )
                failure.text = step_detail

            elif result.status == TestStatus.ERROR:
                error = ET.SubElement(tc, "error")
                error.set("message", _escape(result.error_message))
                error.set("type", "TestError")
                error.text = result.tb or result.error_message

            elif result.status == TestStatus.SKIP:
                skipped = ET.SubElement(tc, "skipped")
                skipped.set("message", _escape(result.error_message))

            # System-out: step log
            if result.steps:
                sys_out = ET.SubElement(tc, "system-out")
                sys_out.text = "\n".join(
                    f"Step {s.step_number}: {s.description} [{s.status.name}] {s.elapsed_ms:.0f}ms"
                    for s in result.steps
                )

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    tree.write(str(output), encoding="utf-8", xml_declaration=True)

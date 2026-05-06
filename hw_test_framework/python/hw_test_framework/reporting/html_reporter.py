"""
hw_test_framework/reporting/html_reporter.py

HTML report generator — self-contained single-file report with
pass/fail/skip table, step details, and feature summary.
No external CSS/JS dependencies; works offline.
"""

from __future__ import annotations

import html
import time
from pathlib import Path
from typing import List

from ..framework.test_case import TestResult, TestStatus
from ..framework.test_runner import SuiteResult

_STATUS_COLOR = {
    TestStatus.PASS:    "#28a745",
    TestStatus.FAIL:    "#dc3545",
    TestStatus.ERROR:   "#fd7e14",
    TestStatus.SKIP:    "#6c757d",
    TestStatus.BLOCKED: "#6f42c1",
    TestStatus.NOT_RUN: "#adb5bd",
}

_STATUS_BADGE = {
    TestStatus.PASS:    "PASS",
    TestStatus.FAIL:    "FAIL",
    TestStatus.ERROR:   "ERROR",
    TestStatus.SKIP:    "SKIP",
    TestStatus.BLOCKED: "BLOCKED",
    TestStatus.NOT_RUN: "NOT RUN",
}


def _badge(status: TestStatus) -> str:
    color = _STATUS_COLOR.get(status, "#adb5bd")
    label = _STATUS_BADGE.get(status, "?")
    return (f'<span style="background:{color};color:#fff;'
            f'padding:2px 8px;border-radius:3px;font-size:0.8em;font-weight:bold">'
            f'{label}</span>')


def _steps_table(result: TestResult) -> str:
    if not result.steps:
        return ""
    rows = ""
    for s in result.steps:
        color = _STATUS_COLOR.get(s.status, "#adb5bd")
        rows += (f"<tr>"
                 f"<td>{s.step_number}</td>"
                 f"<td>{html.escape(s.description)}</td>"
                 f"<td style='color:{color};font-weight:bold'>{s.status.name}</td>"
                 f"<td>{s.elapsed_ms:.0f} ms</td>"
                 f"<td>{html.escape(s.message)}</td>"
                 f"</tr>\n")
    return (
        "<table style='width:100%;font-size:0.85em;margin-top:6px;border-collapse:collapse'>"
        "<thead><tr>"
        "<th>#</th><th>Description</th><th>Status</th><th>Time</th><th>Notes</th>"
        "</tr></thead><tbody>" + rows + "</tbody></table>"
    )


def write_html(
    suite_results: List[SuiteResult],
    output_path: str,
    title: str = "HW Test Framework — Report",
) -> None:
    total    = sum(s.total   for s in suite_results)
    passed   = sum(s.passed  for s in suite_results)
    failed   = sum(s.failed  for s in suite_results)
    errored  = sum(s.errors  for s in suite_results)
    skipped  = sum(s.skipped for s in suite_results)
    pass_pct = round(passed / total * 100, 1) if total else 0.0
    overall  = "PASS" if failed == 0 and errored == 0 else "FAIL"
    overall_color = _STATUS_COLOR[TestStatus.PASS if overall == "PASS" else TestStatus.FAIL]
    generated_at  = time.strftime("%Y-%m-%d %H:%M:%S")

    # ── Summary cards
    def card(label: str, value, color: str) -> str:
        return (f'<div style="background:{color};color:#fff;'
                f'border-radius:6px;padding:12px 20px;text-align:center;min-width:80px">'
                f'<div style="font-size:1.8em;font-weight:bold">{value}</div>'
                f'<div style="font-size:0.85em">{label}</div></div>')

    cards = "".join([
        card("Total",   total,    "#495057"),
        card("Passed",  passed,   _STATUS_COLOR[TestStatus.PASS]),
        card("Failed",  failed,   _STATUS_COLOR[TestStatus.FAIL]),
        card("Errors",  errored,  _STATUS_COLOR[TestStatus.ERROR]),
        card("Skipped", skipped,  _STATUS_COLOR[TestStatus.SKIP]),
        card("Pass %",  f"{pass_pct}%", "#007bff"),
    ])

    # ── Suite detail sections
    suite_sections = ""
    for suite in suite_results:
        rows = ""
        for r in suite.results:
            bg = "#fff8f8" if r.failed else "#f8fff8" if r.passed else "#fff"
            rows += (
                f'<tr style="background:{bg}">'
                f'<td><code>{html.escape(r.test_id)}</code></td>'
                f'<td>{html.escape(r.test_name)}</td>'
                f'<td>{html.escape(r.metadata.get("feature",""))}</td>'
                f'<td>{html.escape(r.metadata.get("requirement",""))}</td>'
                f'<td>{_badge(r.status)}</td>'
                f'<td>{r.duration_ms:.0f} ms</td>'
                f'<td>{html.escape(r.error_message[:120] if r.error_message else "")}</td>'
                f'</tr>\n'
                f'<tr style="display:none" class="steps-{html.escape(r.test_id)}">'
                f'<td colspan="7" style="padding:0 20px 12px">{_steps_table(r)}</td>'
                f'</tr>\n'
            )

        suite_sections += f"""
<section style="margin:24px 0">
  <h2 style="border-bottom:2px solid #dee2e6;padding-bottom:6px">
    {html.escape(suite.suite_name)}
    <small style="font-size:0.6em;color:#6c757d">
      {suite.passed}/{suite.total} passed · {suite.duration_ms/1000:.2f}s
    </small>
  </h2>
  <table style="width:100%;border-collapse:collapse;font-size:0.9em">
    <thead>
      <tr style="background:#f8f9fa">
        <th align="left">ID</th>
        <th align="left">Name</th>
        <th align="left">Feature</th>
        <th align="left">Requirement</th>
        <th>Status</th>
        <th>Duration</th>
        <th align="left">Notes</th>
      </tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>
</section>
"""

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{html.escape(title)}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            margin:0;padding:20px;background:#f4f6f8;color:#212529 }}
    h1   {{ margin:0 0 4px }}
    table td, table th {{ padding:6px 10px;border:1px solid #dee2e6 }}
    table thead {{ position:sticky;top:0 }}
    code {{ background:#f1f3f5;padding:1px 4px;border-radius:3px }}
    .summary-cards {{ display:flex;gap:12px;flex-wrap:wrap;margin:16px 0 }}
    .overall-badge {{ font-size:1.1em;font-weight:bold;padding:4px 16px;
                      border-radius:4px;color:#fff;background:{overall_color} }}
  </style>
</head>
<body>
  <h1>{html.escape(title)}</h1>
  <p>Generated: {generated_at} &nbsp; <span class="overall-badge">{overall}</span></p>
  <div class="summary-cards">{cards}</div>
  {suite_sections}
</body>
</html>
"""
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(page, encoding="utf-8")

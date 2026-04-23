# ADAS Release Automation Suite (Python)

This suite provides:
- Release **smoke** validation
- Full **regression** validation
- **250 total ADAS test cases** with edge/boundary coverage

Detailed integration reference:
- `REALTIME_INTEGRATION_GUIDE.md` (mock data location, real-time HTTP connection, software options, mapping strategy)

## Features covered
- AEB, FCW, ACC, LKA, BSD, TSR, DMS

## Test split
- Smoke: 50
- Regression: 200
- Total: 250

## Quick start
1. Create env and install:
   - `python3 -m venv .venv`
   - `source .venv/bin/activate`
   - `pip install -r requirements.txt`

2. Run smoke only:
   - `pytest tests/test_release_suite.py -m smoke`

3. Run full regression:
   - `pytest tests/test_release_suite.py -m regression`

4. Run all release tests:
   - `pytest tests/test_release_suite.py`

## Interactive UI (human-friendly execution)

Launch UI:
- `streamlit run ui_app.py`

UI capabilities:
- Run `smoke`, `regression`, or `all` suites with one click.
- Configure build ID and gate thresholds (`min pass rate`, `max failures`, `max errors`).
- Switch SUT mode (`mock` or `http`) and set `ADAS_SUT_URL`.
- View full execution logs after run.
- Browse recent run history and open HTML/JUnit artifacts.

## One-command release gate (versioned artifacts)

Run smoke gate:
- `python run_release_gate.py --suite smoke --build-id adas-2026.04.23-rc1`

Run regression gate:
- `python run_release_gate.py --suite regression --build-id adas-2026.04.23-rc1`

Run complete release gate:
- `python run_release_gate.py --suite all --build-id adas-2026.04.23-rc1`

Generated artifacts:
- `reports/<build-id>/<suite>_<timestamp>/junit.xml`
- `reports/<build-id>/<suite>_<timestamp>/report.html`
- `reports/<build-id>/<suite>_<timestamp>/summary.json`

Gate behavior:
- Non-zero exit code if selected suite fails.
- JSON summary includes total tests/failures/errors/skipped and artifact paths.

Production controls:
- `--min-pass-rate` (default `100`) gate threshold.
- `--max-failures` (default `0`) gate threshold.
- `--max-errors` (default `0`) gate threshold.
- Duration, command, and threshold violations are captured in `summary.json`.

Example strict release gate:
- `python run_release_gate.py --suite all --build-id adas-2026.04.23-rc2 --min-pass-rate 100 --max-failures 0 --max-errors 0`

## CI/CD workflow

GitHub Actions workflow added at:
- `.github/workflows/adas_release_gate.yml`

Trigger manually using `workflow_dispatch` with:
- `build_id`
- `suite` (`smoke`, `regression`, `all`)

Workflow uploads `reports/` as build artifacts.

## Running against real model build
By default, suite runs in `mock` mode (internal oracle) so pipeline is always runnable.

Set env to run against actual release endpoint:
- `export ADAS_SUT_MODE=http`
- `export ADAS_SUT_URL=http://<host>:<port>/predict`

Optional production adapter tuning:
- `export ADAS_SUT_TIMEOUT_S=8`
- `export ADAS_SUT_HTTP_RETRIES=2`
- `export ADAS_SUT_BACKOFF_S=0.2`
- `export ADAS_STRICT_SIGNALS=1`  (fail if response contains unexpected extra signals)

Expected HTTP contract:
- Request JSON:
  - `{"feature": "AEB", "scenario": {...}}`
- Response JSON:
  - `{"status":"OK","signals": {"aeb_warn": true, "aeb_brake": false, ...}}`

The assertions validate expected signal keys per test case.

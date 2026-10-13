# Outbreak Nowcaster

A local, illustrative **reporting-delay-adjusted incidence** calculator for aggregated outbreak surveillance, with preserved legacy medical-score and agent-audit utilities.

## What it does

The **static web application** accepts aggregated case counts indexed by **event date** (such as symptom onset). For each event date it divides the number of cases already reported by the cumulative probability that such events would have been reported after the elapsed number of days. It displays observed and adjusted daily counts, a chart, and an exportable CSV.

This is a deterministic inverse-completeness correction, **not** a trained outbreak forecast, validated epidemiologic model, or clinical decision-support tool. It does not predict future incidence, estimate uncertainty intervals, account for changing delay distributions, or infer reporting delays from supplied counts. The default weights `0.50,0.25,0.15,0.10` are *illustrative*. Calibrate delays from your own reporting history before interpreting results.

## Browser use

Open the deployed GitHub Pages site, or open `web/index.html` locally. Enter a snapshot date, reporting-delay weights for delays of 0, 1, 2, ... days, and CSV data such as:

```csv
date,reported
2026-10-11,90
2026-10-12,15
2026-10-13,5
```

Select **Calculate nowcast**; **Export CSV** downloads the adjusted results. The **Load example** button creates illustrative relative-date records. Files must be at most 1 MB, event dates must be unique and no later than the snapshot date, and counts must be nonnegative integers. All modern evergreen browsers with JavaScript, Blob downloads, and File API support can run the page without Python, Pyodide, a service worker, or a backend.

**Privacy:** Browser calculations are local and do not transmit, persist, or log entered data. The page uses no third-party fonts, trackers, or external JavaScript. Use aggregated de-identified counts only.

## Python CLI

Python 3.10 or newer; no dependencies are needed for the standalone `incidence.py` nowcasting CLI:

```bash
python incidence.py --input surveillance.csv --as-of 2026-10-13 --delays 0.5,0.3,0.2 --output result.csv
```

The installed entry point is `incidence-nowcast` and returns the same columns: `date,reported,age_days,completeness,nowcast,additional_estimated`.

For the retained legacy API/agents and unrelated medical-score utilities:

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
python cli.py audit --task-id TEST-01 --primary 15
python nowcaster.py single --qt 400 --rr 1000
python cli.py serve --host 127.0.0.1 --port 8000
```

The FastAPI routes are `/health`, `/metrics`, `/api/audit`, `/api/chat`, and `/api/audit/logs`. The `/metrics` route responds with JSON, not Prometheus exposition format. The legacy chat provider is a deterministic mock; setting a remote-model provider does not activate remote inference. Existing score methods include approximations and are not validated for clinical care.

## Deployment and safety

The web page is static and runs independently of the Python backend. GitHub Actions tests the Python and browser calculations and deploys the `web/` directory to GitHub Pages on `master` updates.

The optional FastAPI server is **not authenticated** and should not be exposed publicly. Its regular-expression identifier filter is limited and is **not a comprehensive PHI de-identification solution**. The HMAC audit chain is stored in process memory, not durable storage. Run it only on a trusted local network with de-identified inputs.

For Docker Compose, set `AUDIT_SECRET_KEY` to a unique random value in your environment (see `.env.example`) before running `docker compose up --build`. The Compose configuration publishes to loopback only. Do not commit keys or add them to client-side code.

## Development

The repository uses Python, FastAPI, Pydantic, vanilla JavaScript, CSS, and Node's built-in test runner. Run:

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
node --test web/nowcast.test.cjs
node --check web/app.js
```

The legacy `cli.py`, `nowcaster.py`, `agents/`, `enrichment.py`, and `simulator.py` remain available for their existing workflows.

## License

[MIT](LICENSE).

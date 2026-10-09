# Verification record

Executed: 22 backend pytest tests, Ruff lint/format, SQLite Alembic upgrade and schema check, frontend Prettier check and production Vite build. Headless Chromium exercises registration, demo, forecast setup, saved scenarios, stock arrivals, invalid and valid CSV previews/import, scenario comparison, CSV download, session restore, mobile layout and logout. Screenshots show synthetic data only.

Not executed: Docker image/runtime, PostgreSQL runtime/concurrency, external ERP/e-commerce synchronization and production load. No external connector exists. The browser smoke script requires playwright-core and a compatible Chromium; set FORECAST_BROWSER and FORECAST_URL to use your own installation.

Unit/API tests cover model constants, weekly model selection, chronology, short-history ranges, multiplier behavior, arrivals, missing dates, finite values, snapshot/replay, owner isolation, comparison constraints and CSRF. Review backend/tests/test_forecasting.py for exact cases.

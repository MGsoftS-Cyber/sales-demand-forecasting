# DemandIQ — Sales & Demand Forecasting

Independent, runnable application for e-commerce, retail and factories: import daily sales, compare transparent models, save forecasts, explore stock scenarios and export reports. Python/FastAPI backend, React/JavaScript dashboard, SQLAlchemy/Alembic and PostgreSQL in Compose; SQLite for development. Version 1.0.0. MIT license.

## Start with Docker

1. Copy `.env.example` to `.env`; replace POSTGRES_PASSWORD with a long random URL-safe value.
2. Run `docker compose up --build`.
3. Open http://localhost:8084 and create an account (no default credentials).
4. Load demo data, run a forecast, then inspect Forecast setup and Stock planning.

Docker and PostgreSQL runtime were not executed in the delivery environment. Verify these on your machine before deployment. The entrypoint runs Alembic migrations; do not run multiple migration jobs concurrently.

## Start locally (Python 3.12, Node 24)

```sh
cd backend
python -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --host 127.0.0.1 --port 8004
```

In a second terminal:
```sh
cd frontend
npm ci
npm run dev
```

Open http://localhost:5177. Vite forwards /api to port 8004. For a single-process preview, `npm run build` in frontend and open backend port 8004. Database defaults to local `backend/forecast.db`. API documentation: `/docs`.

## Typical workflow

Create one series per SKU and location. Import `examples/sales.csv` (synthetic data) with exact `date,quantity` columns. Preview before saving. Choose a dataset version, 1–90 future calendar days, a model and demand multiplier. Starting stock and dated arrivals are manual planning inputs. Save, review model scores and empirical ranges, compare matching scenarios, download JSON or CSV.

This release models observed sales, not latent demand when stockouts suppress sales. It captures weekly patterns; annual seasonality, holidays, prices and campaigns are future extensions. One account owns its data; shared teams and roles are not implemented. InventoryIQ is a separate application: no live connector or automatic purchase orders are included. The PDF includes both application designs and a proposed integration.

## Documentation

- docs/ARCHITECTURE.md — components and persistence
- docs/METHODOLOGY.md — formulas, selection, validation and limits
- docs/API.md — routes, payloads and errors
- docs/PRODUCTION.md — operational requirements
- docs/VERIFICATION.md — executed checks and limits
- CONTRIBUTING.md — contributor setup and review expectations
- docs/dashboard.png, forecast-setup.png, stock-planning.png — actual screens
- docs/inventory-design.png — companion InventoryIQ screen

Forecast quantities may be fractional estimates. The planning calculation does not round to cartons, account for backorders or place supplier orders.

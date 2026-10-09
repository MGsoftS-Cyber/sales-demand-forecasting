# HTTP API

Base prefix `/api`. `/docs` exposes live OpenAPI. Register/login returns session cookie and csrf_token. Subsequent writes require X-CSRF-Token and accepted Origin; all durable business writes require Idempotency-Key (1–100 characters). Preserve a key when retrying the same operation; create a new key for changed work. Never expose session tokens in client storage.

| Method/path | Purpose |
|---|---|
| POST /auth/register, /auth/login | Start owner session |
| GET /auth/session | Restore session and CSRF token |
| POST /auth/logout | Revoke session |
| GET /health | Liveness |
| GET, POST /v1/series | List/create SKU-location series |
| POST /v1/imports/sales/preview | Parse CSV and return row errors |
| GET, POST /v1/series/{id}/datasets | Dataset versions |
| POST /v1/series/{id}/analyses | Calculate and freeze forecast |
| GET /v1/analyses | Latest 100 saved analyses |
| POST /v1/comparisons | Compare 2–10 distinct analyses with same series/origin/horizon |
| GET /v1/analyses/{id}/report?format=json or csv | Download saved inputs/results or daily output |
| POST /v1/demo | Synthetic seed; empty catalog only |

Forecast payload:
```json
{"dataset_id":"replace-id","scenario_name":"Base forecast","horizon":30,"model":"auto","demand_multiplier":1,"starting_stock":300,"arrivals":[]}
```
Dataset payload:
```json
{"source":"Store export","missing_policy":"reject","observations":[{"date":"2026-01-01","quantity":12}]}
```
The short dataset example shows row shape; real requests need at least 14 rows. CSV preview takes {"csv_text":"date,quantity\n..."}. Arrival entries use {"date":"YYYY-MM-DD","quantity":200} within the forecast dates.

401 means no active session, 403 rejected CSRF/origin, 404 unavailable or foreign record, 409 duplicate/conflict/replay mismatch, 422 invalid input and 429 throttle. Preview returns errors as data; do not save an invalid preview. CSV reports contain date, forecast, lower, upper, range_samples, arrival, ending_stock and unmet_demand.

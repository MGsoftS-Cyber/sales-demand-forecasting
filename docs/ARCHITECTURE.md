# Architecture

React dashboard → same-origin HTTP → FastAPI authentication/ownership → routes → immutable data and pure engine → saved results and report exports.

## Programming file map

| File | Responsibility |
|---|---|
| main.py | Account/session endpoints, headers, static assets and safe errors |
| security.py | Argon2, opaque session tokens, CSRF, origin checks, throttling |
| schemas.py | Bounded input contracts and finite values |
| imports.py | CSV row errors and complete daily-history normalization |
| engine.py | Prefix-only model fitting, rolling evaluation and stock simulation |
| models.py | SQLAlchemy relational records and uniqueness |
| services.py | Payload fingerprints and atomic idempotency receipt |
| routes.py | Owner-scoped workflows, comparisons and exports |
| database.py/config.py | Request sessions and deployment settings |
| frontend/src/main.jsx | Views, scenario state and SVG forecast chart |
| frontend/src/api.js | JSON transport and CSRF attachment |

## Data model

User owns SalesSeries and LoginSession. Series owns Dataset and Analysis. Dataset observations and quality are JSON; Analysis inputs/results preserve a complete frozen history and engine_version. RequestRecord belongs to User and stores scope/key/payload hash/response for safe replay. Relational uniqueness prevents duplicate owner/SKU/location and duplicate dataset fingerprints. Fingerprints include normalized rows, source and missing policy.

Business writes and replay receipt commit atomically. Same key and payload returns the original result; changed payload returns 409. Ownership checks apply to series, datasets and analyses. SQLite development does not prove PostgreSQL behavior under production concurrency.

No distributed worker, scheduled synchronization, third-party connector, workspace membership, account recovery or billing system is implemented. These are future SaaS modules.

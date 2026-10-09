# Contributing

Read README and docs/METHODOLOGY.md first. Keep forecasting mathematics in app/engine.py, parsing in imports.py, HTTP ownership in routes.py and durable replay behavior in services.py. React coordinates workflows, not model formulas. Explain time boundaries and assumptions in code comments.

Install requirements-dev.txt and npm ci. Before submitting:
```sh
cd backend
ruff check app tests migrations
ruff format --check app tests migrations
pytest -q
alembic upgrade head
alembic check
```
```sh
cd frontend
npm run format:check
npm run build
```

Use an isolated database for migrations/tests. Add meaningful tests when changing chronology, model selection, intervals, ownership, transaction or schema rules. Migration revisions are required for persistent schema changes. Never edit old revisions for deployed databases. Preserve immutable datasets and saved analyses; version the calculation engine when semantics change.

Create your own GitHub repository, unpack the source, initialize git, add files and push. `.github/workflows/ci.yml` defines validation and image build jobs. Never commit `.env`, local databases or credentials. A pull request should state the user-visible behavior, methodology changes, validation and remaining limitations.

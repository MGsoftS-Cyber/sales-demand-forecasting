# Production preparation

Compose binds localhost:8084 and PostgreSQL is internal. Put an HTTPS reverse proxy in front; set COOKIE_SECURE=true, explicit trusted ALLOWED_ORIGINS and a strong database credential. Configure proxy body limits, timeout/rate limits and monitoring. Check backups with actual restore drills. Run migrations once before replicas start; the bundled entrypoint is suitable for a single application instance.

Test PostgreSQL migrations, concurrent identical idempotency keys and failure recovery on the target runtime. Dependency review, vulnerability scanning and load testing must be repeated for deployment. Local tests and Docker build configuration are not proof of production capacity.

This starter lacks shared workspaces, SSO, email verification, account recovery, durable distributed rate limiting, asynchronous jobs, connector secrets management and billing. Add these explicitly before offering a multi-team service. Avoid logging credentials or sales payloads. Session cookies are HttpOnly; deploy over TLS. Product limits bound computations but no background forecast queue is present.

Inventory integration is a proposal: map owner/workspace, SKU and location; read available stock and dated open purchase quantities; send normalized sales history to DemandIQ; show saved forecasting results in inventory planning. Require freshness timestamps, source IDs, reconciliation and authorization. Purchase decisions remain a separate explicit action. Neither source application implements this connector in this release.

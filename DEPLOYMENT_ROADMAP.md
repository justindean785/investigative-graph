# Trace Analyst Deployment Roadmap

## Objectives
- Deploy `backend` and `frontend` with secure defaults.
- Preserve core capabilities: CRUD, autonomous investigation, SSE live feed, OSINT fan-out, exports.
- Minimize operational risk with staged rollout, observability, and rollback.

## Target Runtime Architecture
- **Frontend**: static React build served via CDN/edge.
- **Backend**: FastAPI on container runtime with autoscaling.
- **Database**: managed MongoDB (Atlas recommended).
- **Secrets**: environment-injected via platform secret manager.
- **Traffic**: TLS termination at load balancer/reverse proxy.

## Environments
- **Dev**: local stack (`mongod`, `uvicorn`, `yarn start`).
- **Staging**: production-like infra, separate Mongo DB, test provider keys.
- **Production**: isolated DB/keys, tighter rate limits, explicit CORS origin list.

## Phase 1 — Pre-Deploy Hardening
- Set explicit backend env vars:
  - `MONGO_URL`, `DB_NAME`, `API_KEY`, `CORS_ORIGINS`
  - optional AI/OSINT: `GEMINI_API_KEY`, `GHOSINT_API_KEY`, `SWATTED_*`, `BOSINT_API_KEY`
- Set explicit frontend env vars:
  - `REACT_APP_BACKEND_URL`
  - `REACT_APP_API_KEY`
- Rotate default `API_KEY`; never use `trace-analyst-secret-2026` in production.
- Set `CORS_ORIGINS` to exact frontend URL(s), never wildcard.
- Ensure MongoDB auth + network controls are enabled.

## Phase 2 — CI/CD Gates
- Keep CI gates mandatory on merge:
  - Backend lint: `python3 -m flake8 backend/server.py --max-line-length=150`
  - Backend tests: `python3 -m pytest backend/tests/ -v`
  - Frontend build/lint gate: `cd frontend && yarn build`
- Add deploy jobs per environment:
  - `main` → staging deploy
  - release tag/manual approval → production deploy
- Store build artifacts and image tags for deterministic rollback.

## Phase 3 — Backend Deployment
- Build backend image from `backend/`.
- Run `uvicorn server:app --host 0.0.0.0 --port 8001`.
- Health checks:
  - Liveness: `GET /api/`
  - Readiness: `GET /api/auth/validate` with service API key (or custom health endpoint later)
- Configure horizontal autoscaling on CPU + latency.
- Keep sticky sessions off (SSE supported per connection; no server session state required for standard CRUD).

## Phase 4 — Frontend Deployment
- Build with:
  - `REACT_APP_BACKEND_URL=https://<api-domain>`
  - `REACT_APP_API_KEY=<shared-api-key>`
- Serve static `frontend/build` via CDN or static hosting.
- Configure cache policy:
  - fingerprinted assets: long TTL
  - `index.html`: short TTL/no-cache

## Phase 5 — Data & Migration Safety
- Take Mongo backup snapshot before first production cut.
- Validate indexes are created at app startup.
- Smoke test key collections:
  - `investigations`, `entities`, `relationships`, `evidence`, `timeline_events`, `investigation_leads`, `chat_messages`.

## Phase 6 — Observability
- Centralize logs (backend app logs + reverse proxy logs).
- Track key metrics:
  - request rate, p95 latency, error rate
  - SSE connection count
  - OSINT provider timeout/failure rates
  - AI call success/failure and token-cost proxies
- Alerting:
  - elevated 5xx
  - Mongo connection failures
  - sustained provider failure spikes

## Phase 7 — Rollout & Verification
- Deploy to staging and run:
  - investigation CRUD
  - ingest URL/text/file
  - AI analysis + suggestion accept/dismiss
  - lead generation
  - graph analysis endpoints
  - export JSON/CSV/Markdown
  - SSE live stream verification
- Production rollout:
  - canary (small traffic slice) or controlled cutover
  - verify dashboards and smoke tests
  - full rollout after stability window

## Rollback Plan
- Keep prior backend image and frontend artifact available.
- Rollback sequence:
  - backend deployment rollback first
  - frontend artifact rollback second
  - revert env var changes if incident is config-driven
- Restore Mongo snapshot only for severe data corruption scenarios.

## Near-Term Improvements After First Stable Deploy
- Split `backend/server.py` into modular routers for safer iteration.
- Persist autonomous investigation state/queue for restart resilience.
- Replace fixed polling strategy with SSE-driven incremental refresh.
- Add per-provider rate limits and provider cost telemetry.
- Add user authentication/RBAC if multi-user production is required.

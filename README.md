# Trace Analyst — Investigative Graph Platform

## Changes in this update

### Backend
- **Grok-3 native enrichment** — new `/grok-enrich` endpoint using `xai-sdk` directly; no LangChain wrapper
- **SSRF hardening** — URL validation on all user-supplied URLs before outbound fetch
- **CORS hardening** — wildcard `*` origin disables credentials; explicit origins required for credentialed requests
- **AI suggestion persistence** — suggestions written to MongoDB so they survive page reload
- **Investigation engine** (`backend/engine/`) — entity processor, pivot planner, result normaliser, graph updater
- **SSE streaming endpoint** — real-time investigation progress pushed to the client
- **Flake8 clean** — all lint errors resolved in `server.py`

### Frontend
- **UnifiedInvestigation component** — replaces the previous 7-tab workspace with a single investigation view
- **UniversalInput component** — unified search/seed input for starting investigations
- **LiveFeed component** — SSE-backed real-time stream of investigation events
- **Dashboard bulk delete** — checkbox multi-select + confirmation dialog to delete multiple investigations at once
- **Store updates** (`investigationStore`) — adds `nodes`, `edges`, `currentInvestigationId`; AI suggestions persisted via API
- **Design compliance** — `data-testid` attributes added throughout; removed broad `transition-all` in favour of targeted transitions
- **ReportView component** — investigation report rendering
- **confirm-dialog UI primitive** — reusable confirmation dialog backed by Shadcn Dialog

### Infrastructure / Docs
- CI workflow updated with flake8 lint step and frontend build job
- `docker-compose.yml`, `LOCAL_DEV.md`, `HANDOFF.md`, `REFACTOR_PLAN.md` added
- `AGENTS.md` documents AI agent conventions

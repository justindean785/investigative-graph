# Trace Analyst — engineering handoff

**Repo:** investigative-graph-1 (Trace Analyst)  
**Stack:** Python **FastAPI** (`backend/server.py`), **React 19** + CRACO (`frontend/`), **MongoDB** (Motor), **React Flow** graph UI.

This document is the canonical handoff for anyone picking up the project cold.

---

## 1. What this product is

OSINT-style investigation workspace: create investigations, entities, relationships, evidence, timeline; OSINT search integrations; AI-assisted analysis and chat (Gemini); autonomous investigation engine with streaming-oriented UX on the frontend.

---

## 2. Repository layout (high level)

| Area | Location | Notes |
|------|-----------|--------|
| API + business logic | `backend/server.py` | Very large single module; newer engine code in `backend/engine/` |
| Investigation engine | `backend/engine/` | `InvestigationEngine`, graph updater, normalizer, pivot planner, etc. |
| Frontend app | `frontend/src/` | Unified investigation UI under `components/investigation/` |
| API tests (HTTP + in-process) | `backend/tests/test_investigation_api.py` | Uses `requests` against live URL + `TestClient` for autonomous routes |
| Local dev guide | `LOCAL_DEV.md` | Atlas vs Docker vs Windows Mongo; daily two-terminal flow |
| Cursor/agent notes | `AGENTS.md` | Ports, env, CORS, lint/test commands |

---

## 3. How to run locally (summary)

**Prerequisite:** MongoDB reachable at `MONGO_URL` (see **`LOCAL_DEV.md`** — recommended paths: **MongoDB Atlas**, or **`docker compose up -d`** from repo root).

**Backend** (`backend/.env` from `backend/.env.example`):

```text
MONGO_URL=...
DB_NAME=trace_analyst
API_KEY=trace-analyst-secret-2026   # default; must match frontend if customized
```

```powershell
cd backend
uvicorn server:app --host 127.0.0.1 --port 8001 --reload
```

**Frontend** (`frontend/.env`):

```text
REACT_APP_BACKEND_URL=http://localhost:8001
```

```powershell
cd frontend
$env:BROWSER='none'
yarn start
```

**API auth:** almost all routes expect header `x-api-key` (default key above).

**Optional Docker Mongo only:** `docker-compose.yml` at repo root; helper `scripts/start-mongo-docker.ps1`.

---

## 4. Recent fixes & behavior you should know

### 4.1 Autonomous investigation API

- Routes: `POST /api/investigations/{id}/auto-investigate`, `GET /api/investigations/{id}/auto-status`.
- **Bug fixed:** lookup used `find_one({"_id": investigation_id})` while the app stores investigation UUID in field **`id`**. Now uses `{"id": investigation_id}` — without this, auto-investigate always 404’d for real investigations.
- Routes live on the main `api_router` (grouped with other investigation routes); `app.include_router(api_router)` registers them.

### 4.2 Gemini / AI analyze & chat

- **Bug fixed:** hard-coded `gemini-2.0-flash-exp` / `gemini-exp-1206` could return **404 NOT_FOUND** from Google’s API as model IDs rotate.
- **Now:** defaults `GEMINI_MODEL_FLASH=gemini-2.0-flash`, `GEMINI_MODEL_PRO=gemini-1.5-pro`, `GEMINI_MODEL_CHAT` defaults to flash; all overridable via `backend/.env`. Documented in `backend/.env.example`.

### 4.3 Tests

- `backend/tests/test_investigation_api.py`: **36** tests including **`TestAutonomousInvestigation`**.
- Autonomous tests use **FastAPI `TestClient`** + `sys.path` to `backend/` so they validate **current code** even if uvicorn wasn’t restarted.
- Other tests use **`requests`** and require `REACT_APP_BACKEND_URL` pointing at a running backend + Mongo.

Run:

```powershell
$env:REACT_APP_BACKEND_URL='http://127.0.0.1:8001'
python -m pytest backend/tests/test_investigation_api.py -v
```

---

## 5. Known rough edges / tech debt

- **`server.py` size:** consider splitting routers (investigations, OSINT, AI, etc.) into `backend/routers/` when touching API surface heavily.
- **Frontend ESLint:** `react-hooks/exhaustive-deps` warnings in `LiveFeed.js`, `UnifiedInvestigation.js`, `UniversalInput.js` (non-blocking for `yarn build` but noisy).
- **External OSINT:** live keys hit third-party APIs; failures/log noise are expected when upstream returns 5xx.
- **`test_autonomous_engine.py`** at repo root: currently **no pytest tests collected** (script-style or placeholder — verify before relying on CI).
- **Emergent package:** private; local stub via `backend/install_emergent_stub.py` per `AGENTS.md`.

---

## 6. Security / ops reminders

- Rotate **`API_KEY`** and **`GEMINI_API_KEY`** for anything beyond local dev.
- **`CORS_ORIGINS`:** use explicit origins in production; wildcard + credentials rules per `AGENTS.md`.
- Do **not** commit real `.env` files; use `*.env.example` as templates.

---

## 7. Suggested next steps for the next owner

1. Confirm **Atlas** or **Docker** Mongo documented in `LOCAL_DEV.md` is the team default; onboard new devs with that one path.
2. Add CI job: Mongo service or skip integration tests; run at least **TestAutonomousInvestigation** + unit tests that don’t need live HTTP.
3. Implement or wire **`GET /api/investigations/{id}/stream`** if the UI references SSE and the route is still missing (verify OpenAPI).
4. Triage **Gemini** model names periodically against [Google’s model list](https://ai.google.dev/gemini-api/docs/models).
5. Optionally silence or fix **hook dependency** ESLint warnings for cleaner `yarn start` output.

---

## 8. Key files quick index

- `backend/server.py` — FastAPI app, routes, lifespan (engine init, indexes).
- `backend/engine/` — autonomous investigation pipeline.
- `frontend/src/components/investigation/` — unified workspace, live feed, universal input.
- `LOCAL_DEV.md` — simplest local DB + daily commands.
- `HANDOFF.md` — this document.

---

*Last updated: handoff pass (autonomous routes, Gemini defaults, tests, local dev ergonomics).*

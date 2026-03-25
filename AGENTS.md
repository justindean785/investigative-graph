## Cursor Cloud specific instructions

### Project overview
Trace Analyst is an AI-powered OSINT (Open Source Intelligence) investigation platform. It has a Python/FastAPI backend (`backend/server.py`) and a React 19 frontend (`frontend/`) using Shadcn/UI, Tailwind CSS, and React Flow for graph visualization. Data is stored in MongoDB.

### Services

| Service | Command | Port | Notes |
|---------|---------|------|-------|
| MongoDB | See **Database** below (Docker, Atlas, or local `mongod`) | 27017 | Must be reachable before backend |
| Backend | `cd /workspace/backend && uvicorn server:app --host 0.0.0.0 --port 8001 --reload` | 8001 | Requires `MONGO_URL` and `DB_NAME` env vars (loaded from `backend/.env`) |
| Frontend | `cd /workspace/frontend && BROWSER=none yarn start` | 3000 | Requires `REACT_APP_BACKEND_URL` and `REACT_APP_API_KEY` (same value as backend `API_KEY`; see `frontend/.env.example`) |

### Database (you do not need MongoDB installed on the host)

1. **Docker Compose (full stack):** From the repo root run `docker compose up -d` (see `docker-compose.yml` — includes MongoDB, backend, frontend). For MongoDB only when developing backend against a container, run a `mongo:7` container on port **27017** yourself or use Atlas below.
2. **MongoDB Atlas:** Create a free cluster, then set `MONGO_URL` to your Atlas connection string in `backend/.env` (see `backend/.env.example`).
3. **Local install:** Install `mongod` and run it on `127.0.0.1:27017` if you prefer.

**Integration tests:** `pytest` uses **testcontainers** to start a fresh **MongoDB 7** Docker container for the session (no local `mongod`, no compose file required). **Docker must be running.** If you already run the API yourself, set `REACT_APP_BACKEND_URL` before pytest to skip auto-start.

### Environment files
- `backend/.env` — Copy from `backend/.env.example`. Must include `MONGO_URL` and `DB_NAME=trace_analyst`. Optional: `EMERGENT_LLM_KEY` / `GEMINI_API_KEY` for AI chat features.
- `frontend/.env` — Must contain `REACT_APP_BACKEND_URL` and `REACT_APP_API_KEY` (must match backend `API_KEY`). Copy from `frontend/.env.example`.

### Non-obvious caveats
- The `emergentintegrations` Python package is a private Emergent platform package not available on PyPI. A local stub is installed from `/tmp/emergentintegrations_stub/` to satisfy the import. AI chat/suggestion features return a placeholder message without a real `EMERGENT_LLM_KEY`.
- The API requires an `x-api-key` header for all requests. Default key: `trace-analyst-secret-2026`.
- ESLint is integrated into CRA/CRACO (runs during `yarn start` and `yarn build`), not as a standalone config. There is no `eslint.config.js` file.
- Python dependencies install to `~/.local` (user site-packages). Ensure `$HOME/.local/bin` is on `PATH` for CLI tools like `flake8`, `black`, `uvicorn`.

### Lint / Test / Build
- **Backend lint**: `python3 -m flake8 backend/server.py --max-line-length=150`
- **Backend tests**: `python3 -m pytest backend/tests/ -v` — requires **Docker** (MongoDB spins up automatically via testcontainers; no local `mongod`). To hit an already-running API instead, set `REACT_APP_BACKEND_URL` first.
- **Frontend build**: `cd frontend && yarn build`
- **Frontend dev**: `cd frontend && BROWSER=none yarn start`

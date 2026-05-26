## Cursor Cloud specific instructions

### Project overview
Trace Analyst is an AI-powered OSINT (Open Source Intelligence) investigation platform. It has a Python/FastAPI backend (`backend/server.py`) and a React 19 frontend (`frontend/`) using Shadcn/UI, Tailwind CSS, and React Flow for graph visualization. Data is stored in MongoDB.

### Services

| Service | Command | Port | Notes |
|---------|---------|------|-------|
| MongoDB | `mongod --dbpath /tmp/mongodb/data --logpath /tmp/mongodb/log/mongod.log --fork --bind_ip 127.0.0.1` | 27017 | Must start before backend |
| Backend | `cd /workspace/backend && uvicorn server:app --host 0.0.0.0 --port 8001 --reload` | 8001 | Requires `MONGO_URL` and `DB_NAME` env vars (loaded from `backend/.env`) |
| Frontend | `cd /workspace/frontend && BROWSER=none yarn start` | 3000 | Requires `REACT_APP_BACKEND_URL=http://localhost:8001` (loaded from `frontend/.env`) |

### Environment files
- `backend/.env` — Must contain:
  - `MONGO_URL=mongodb://localhost:27017` (required)
  - `DB_NAME=trace_analyst` (required)
  - `API_KEY=trace-analyst-secret-2026` (default, change in production)
  - `CORS_ORIGINS=http://localhost:3000` (required, set to actual frontend URL in production)
  - `EMERGENT_LLM_KEY` (optional, for AI chat features)
- `frontend/.env` — Must contain:
  - `REACT_APP_BACKEND_URL=http://localhost:8001` (required)
  - `REACT_APP_API_KEY=trace-analyst-secret-2026` (required, must match backend API_KEY)

### Non-obvious caveats
- The `emergentintegrations` Python package is a private Emergent platform package not available on PyPI. A local stub is installed from `/tmp/emergentintegrations_stub/` to satisfy the import. AI chat/suggestion features return a placeholder message without a real `EMERGENT_LLM_KEY`.
- The API requires an `x-api-key` header for all requests. Default key: `trace-analyst-secret-2026`.
- ESLint is integrated into CRA/CRACO (runs during `yarn start` and `yarn build`), not as a standalone config. There is no `eslint.config.js` file.
- Python dependencies install to `~/.local` (user site-packages). Ensure `$HOME/.local/bin` is on `PATH` for CLI tools like `flake8`, `black`, `uvicorn`.

### Lint / Test / Build
- **Backend lint**: `python3 -m flake8 backend/server.py --max-line-length=150`
- **Backend tests**: `REACT_APP_BACKEND_URL=http://localhost:8001 python3 -m pytest backend/tests/ -v` (requires backend + MongoDB running)
- **Frontend build**: `cd frontend && yarn build`
- **Frontend dev**: `cd frontend && BROWSER=none yarn start`

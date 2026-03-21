# Trace Analyst -- Engineering Handoff

**Repo:** `investigative-graph-1`
**Branch:** `main` (latest: `660bd37`)
**Date:** 2026-03-21

---

## 1. What This Product Is

Trace Analyst is an AI-powered OSINT (Open Source Intelligence) investigation platform. Analysts paste raw input -- phone numbers, emails, usernames, breach data, free-text -- and the system automatically extracts entities, queries multiple OSINT providers in parallel, discovers connections, and constructs an investigative graph. Think: "paste anything, watch the investigation unfold."

Key capabilities:
- Autonomous investigation engine that extracts, enriches, and pivots across entities without manual intervention
- Real-time SSE streaming of investigation progress to the frontend
- Graph visualization of entities, relationships, and evidence using React Flow
- AI-assisted analysis and chat (Google Gemini) for pattern recognition and threat assessment
- Three OSINT provider integrations: GHOSINT, Swatted, BOSINT
- Full CRUD for investigations, entities, relationships, evidence, and leads
- Export to JSON, CSV, and Markdown
- Entity deduplication and merge
- URL/text/file ingestion with OCR and PDF extraction

---

## 2. Architecture Overview

```
                          +-------------------+
                          |   React 19 SPA    |
                          |   (Port 3000)     |
                          |                   |
                          |  Zustand Store    |
                          |  React Flow Graph |
                          |  Tailwind + Shadcn|
                          +--------+----------+
                                   |
                            axios + SSE
                         x-api-key header
                                   |
                          +--------v----------+
                          |  FastAPI Backend   |
                          |   (Port 8001)     |
                          |                   |
                          |  server.py (3818L)|
                          |  engine/          |
                          +--------+----------+
                                   |
                    +--------------+---------------+
                    |              |                |
              +-----v----+  +-----v------+  +------v-----+
              |  MongoDB  |  |  Gemini AI |  | OSINT APIs |
              | (Motor)   |  | (google-   |  | GHOSINT    |
              | Port 27017|  |  genai)    |  | Swatted    |
              +-----------+  +------------+  | BOSINT     |
                                             +------------+
```

**Communication:** The frontend makes REST calls to `{BACKEND_URL}/api/*` with an `x-api-key` header. For live investigation streaming, the frontend opens an SSE connection to `/api/investigations/{id}/stream`.

---

## 3. Repository Layout

```
investigative-graph-1/
  backend/
    server.py                  # Monolithic FastAPI app (3818 lines) -- ALL routes, models, logic
    .env / .env.example        # Backend config (Mongo URL, API keys)
    requirements.txt           # Python deps (pinned)
    install_emergent_stub.py   # Stub installer for private emergentintegrations package
    engine/                    # Autonomous investigation engine
      __init__.py              # Exports: InvestigationEngine, EntityProcessor, PivotPlanner, etc.
      investigation_engine.py  # Main orchestrator -- async generator yielding ExecutionEvents
      entity_processor.py      # Entity extraction & OSINT enrichment
      pivot_planner.py         # Decides which entities to investigate next + priority scoring
      normalizer.py            # Normalizes GHOSINT/Swatted/BOSINT output to unified schema
      graph_updater.py         # Writes entities/relationships/evidence to MongoDB
      models.py                # Pydantic models: NormalizedEntity, PivotTask, InvestigationState, etc.
    routers/                   # Placeholder for future server.py decomposition
      __init__.py
      README.md
    tests/
      conftest.py              # Auto-starts MongoDB + uvicorn; installs emergent stub
      test_investigation_api.py # 918 lines, ~36 tests (HTTP + TestClient)

  frontend/
    package.json               # React 19, React Flow 11, Zustand 5, Tailwind, Shadcn/UI
    craco.config.js            # CRA override: Tailwind PostCSS + path aliases (@/)
    src/
      App.js                   # Two routes: / (Dashboard), /investigation/:id (Unified)
      index.js                 # React root + global CSS imports (Manrope, JetBrains Mono, Rajdhani)
      index.css                # Tailwind directives + custom theme (dark, investigation-tool aesthetic)
      config/
        api.js                 # Axios instance with x-api-key header, BACKEND_URL normalization
      store/
        investigationStore.js  # Zustand store: entities, relationships, evidence, timeline, UI state
      components/
        investigation/
          UnifiedInvestigation.js  # Main investigation workspace (header, panels, graph)
          UniversalInput.js        # "Paste anything" input + auto-investigate trigger
          LiveFeed.js              # Real-time SSE event stream display
        workspace/
          GraphView.js             # React Flow graph with custom nodes, edge styles, layout
          EntitiesWorkspace.js     # Entity list with CRUD, risk display, enrichment
          EvidenceWorkspace.js     # Evidence list with CRUD, verification, tagging
          ReportView.js            # Investigation report generator (threat assessment, key findings)
        ui/                        # Shadcn/UI primitives (button, badge, dialog, select, input, label, sonner, confirm-dialog)
        CustomNode.js              # React Flow custom node component (entity visualization)
        ErrorBoundary.js           # React error boundary wrapper
      pages/
        Dashboard.js               # Investigation list with create, bulk delete, search
      lib/
        entityTypes.js             # Entity type definitions and display config
      hooks/                       # (empty after refactor -- use-toast.js was removed)

  .github/workflows/ci.yml      # GitHub Actions: backend lint + tests, frontend build
  docker-compose.yml             # Optional: Mongo 7 container
  scripts/start-mongo-docker.ps1 # PowerShell helper to start Mongo via Docker
  AGENTS.md                      # Agent/IDE configuration and project conventions
  LOCAL_DEV.md                   # Local development setup guide
  SECURITY.md                    # Security policy
```

---

## 4. Technology Stack

### Backend
| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | FastAPI | 0.110.1 |
| ASGI Server | uvicorn | 0.25.0 |
| Database Driver | Motor (async MongoDB) | 3.3.1 |
| Validation | Pydantic v2 | 2.12.5 |
| AI/LLM | Google GenAI (Gemini) | 1.65.0 |
| HTTP Client | httpx (async) | 0.28.1 |
| SSE | sse-starlette | (EventSourceResponse) |
| OCR | pytesseract + Pillow | Optional |
| PDF | PyPDF2 | Optional |
| HTML parsing | BeautifulSoup4 | Optional |
| Linting | flake8 | 7.3.0 |
| Testing | pytest | 9.0.2 |

### Frontend
| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | React | 19.x |
| Build Tool | CRA + CRACO | 7.1.0 |
| Routing | react-router-dom | 7.5.1 |
| State Management | Zustand | 5.0.11 |
| Graph Visualization | React Flow | 11.11.4 |
| HTTP Client | Axios | 1.8.4 |
| UI Components | Shadcn/UI (Radix primitives) | -- |
| Styling | Tailwind CSS | 3.4.17 |
| Icons | Lucide React | 0.507.0 |
| Toasts | Sonner | 2.0.3 |
| Fonts | Manrope, JetBrains Mono, Rajdhani | @fontsource |

---

## 5. How to Run Locally

### Prerequisites
- Node.js 20+ with Yarn 1.22
- Python 3.11+ (3.14 works but CI uses 3.11)
- MongoDB accessible (Atlas free tier, Docker, or local install)

### Step 1: Database
Pick one:
- **Atlas (easiest):** Create free cluster, copy connection string
- **Docker:** `docker compose up -d` from repo root
- **Local install:** `net start MongoDB` (Windows MSI)

### Step 2: Backend
```powershell
cd backend
# Copy and edit .env
cp .env.example .env
# Set MONGO_URL and DB_NAME at minimum

# Install deps
pip install -r requirements.txt

# Install emergent stub (private package not on PyPI)
python install_emergent_stub.py

# Start
uvicorn server:app --host 127.0.0.1 --port 8001 --reload
```

### Step 3: Frontend
```powershell
cd frontend
# Create .env with: REACT_APP_BACKEND_URL=http://localhost:8001
yarn install
$env:BROWSER='none'
yarn start
```

Open http://localhost:3000.

---

## 6. Environment Variables

### Backend (`backend/.env`)
| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `MONGO_URL` | Yes | -- | MongoDB connection string |
| `DB_NAME` | Yes | -- | Database name (e.g. `trace_analyst`) |
| `API_KEY` | No | `trace-analyst-secret-2026` | Shared API key for all requests |
| `GEMINI_API_KEY` | No | -- | Google Gemini API key (AI features return 503 without it) |
| `GEMINI_MODEL_FLASH` | No | `gemini-2.0-flash` | Gemini model for fast analysis |
| `GEMINI_MODEL_PRO` | No | `gemini-1.5-pro` | Gemini model for deep analysis |
| `GEMINI_MODEL_CHAT` | No | (same as flash) | Gemini model for chat |
| `GHOSINT_API_KEY` | No | -- | GHOSINT OSINT provider key |
| `SWATTED_API_TOKEN` | No | -- | Swatted OSINT provider token |
| `BOSINT_API_KEY` | No | -- | BOSINT OSINT provider key |
| `CORS_ORIGINS` | No | `*` | Comma-separated allowed origins |
| `EMERGENT_LLM_KEY` | No | -- | Legacy Emergent AI key (stub used without it) |

### Frontend (`frontend/.env`)
| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `REACT_APP_BACKEND_URL` | Yes (prod) | `http://localhost:8001` (dev) | Backend API base URL |
| `REACT_APP_API_KEY` | No | `trace-analyst-secret-2026` | API key sent in x-api-key header |

---

## 7. API Surface (55 Endpoints)

All routes are prefixed with `/api` and require `x-api-key` header. Rate-limited per category.

### Core CRUD
| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/` | Health check |
| `POST` | `/auth/validate` | Validate API key |
| `POST` | `/investigations` | Create investigation |
| `GET` | `/investigations` | List investigations |
| `GET` | `/investigations/{id}` | Get investigation |
| `PATCH` | `/investigations/{id}` | Update investigation |
| `DELETE` | `/investigations/{id}` | Delete investigation + cascade |
| `POST` | `/investigations/{id}/entities` | Create entity |
| `GET` | `/investigations/{id}/entities` | List entities |
| `PATCH` | `/investigations/{id}/entities/{eid}` | Update entity |
| `DELETE` | `/investigations/{id}/entities/{eid}` | Delete entity |
| `POST` | `/investigations/{id}/relationships` | Create relationship |
| `GET` | `/investigations/{id}/relationships` | List relationships |
| `DELETE` | `/investigations/{id}/relationships/{rid}` | Delete relationship |
| `POST` | `/investigations/{id}/evidence` | Create evidence |
| `GET` | `/investigations/{id}/evidence` | List evidence |
| `PATCH` | `/investigations/{id}/evidence/{eid}` | Update evidence |
| `DELETE` | `/investigations/{id}/evidence/{eid}` | Delete evidence |
| `GET` | `/investigations/{id}/timeline` | Get timeline events |

### Autonomous Investigation
| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/investigations/{id}/auto-investigate` | Start autonomous investigation |
| `GET` | `/investigations/{id}/auto-status` | Get investigation engine status |
| `GET` | `/investigations/{id}/stream` | SSE stream of live events |
| `POST` | `/investigations/{id}/pause` | Pause investigation (planned) |
| `POST` | `/investigations/{id}/resume` | Resume investigation (planned) |

### OSINT & AI
| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/osint/search` | Manual OSINT search (GHOSINT + Swatted + BOSINT) |
| `POST` | `/ai/analyze` | AI analysis of investigation (Gemini flash/pro) |
| `POST` | `/investigations/{id}/chat` | AI chat with investigation context |
| `GET` | `/investigations/{id}/chat/history` | Chat history |
| `DELETE` | `/investigations/{id}/chat/clear` | Clear chat history |

### Graph Analysis
| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/investigations/{id}/graph/analyze` | Full graph analysis (centrality, clusters, patterns) |
| `GET` | `/investigations/{id}/graph/clusters` | Community detection |
| `GET` | `/investigations/{id}/graph/suspicious-patterns` | Pattern detection (high-risk clusters, hubs) |

### Leads
| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/investigations/{id}/leads/generate` | Generate investigation leads (6 pattern types) |
| `GET` | `/investigations/{id}/leads` | List leads |
| `PATCH` | `/investigations/{id}/leads/{lid}` | Update lead status |
| `DELETE` | `/investigations/{id}/leads/{lid}` | Delete lead |

### Ingestion
| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/investigations/{id}/ingest/url` | Ingest URL (scrapes + extracts entities) |
| `POST` | `/investigations/{id}/ingest/text` | Ingest raw text (extracts entities) |
| `POST` | `/investigations/{id}/ingest/file` | Ingest file (image OCR, PDF, text) |

### Utility
| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/extract/entities` | Extract entities from text (stateless) |
| `POST` | `/enrich/entity` | Enrich a single entity via OSINT |
| `GET` | `/investigations/{id}/entities/{eid}/enrichment` | Get entity enrichment data |
| `POST` | `/investigations/{id}/entities/batch` | Batch create entities |
| `GET` | `/investigations/{id}/entities/duplicates` | Find duplicate entities |
| `POST` | `/investigations/{id}/entities/merge` | Merge duplicate entities |
| `GET` | `/evidence/categories` | List evidence categories |
| `GET` | `/investigations/{id}/suggestions` | List AI suggestions |
| `PATCH` | `/investigations/{id}/suggestions/{sid}` | Update suggestion status |
| `GET` | `/investigations/{id}/report` | Generate threat assessment report |

### Export
| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/investigations/{id}/export/json` | Full JSON export |
| `GET` | `/investigations/{id}/export/csv` | CSV export (entities + relationships) |
| `GET` | `/investigations/{id}/export/markdown` | Markdown report export |

---

## 8. Autonomous Investigation Engine

The engine lives in `backend/engine/` and is the core differentiator. It runs an async loop:

```
User input ("paste anything")
  |
  v
EntityProcessor.extract_entities_from_text()  -- regex extraction of phones, emails, IPs, etc.
  |
  v
For each seed entity, create PivotTask and enqueue
  |
  v
Main Loop (while queue not empty & within limits):
  |
  +-- Dequeue highest-priority task
  |
  +-- EntityProcessor.enrich_entity()  -- fans out to GHOSINT + Swatted + BOSINT in parallel
  |
  +-- ProviderNormalizer.normalize_osint_search_results()  -- unified entity/evidence schema
  |
  +-- GraphUpdater.add_entity_to_graph() / add_evidence() / link_derived_entity()
  |
  +-- PivotPlanner.should_pivot()  -- checks confidence threshold, depth limit, entity type value
  |
  +-- If yes: PivotPlanner.create_pivot_task() with priority scoring, enqueue
  |
  +-- Yield ExecutionEvent for each step (SSE streamed to frontend)
  |
  v
Investigation complete (or paused at limit)
```

**Key parameters:**
- `max_depth`: Maximum pivot hops from seed (default 5)
- `max_entities`: Maximum entities to process (default 100)
- `confidence_threshold`: Minimum confidence to pivot (default 0.3)

**Priority scoring** factors: entity confidence, depth penalty (shallower = higher), type boost (email > phone > username > wallet > ip > domain > name > address), multi-source corroboration bonus, high-risk bonus.

**SSE events** streamed to `/api/investigations/{id}/stream`:
- `connected`, `entity_discovered`, `enrichment_started`, `enrichment_completed`, `provider_queried`, `pivot_selected`, `evidence_added`, `relationship_created`, `investigation_completed`, `error`

---

## 9. OSINT Provider Integration

### GHOSINT (`GHOSINT_API_KEY`)
- Endpoint: `https://api.ghosint.io/search`
- Services: leakcheck, snusbase, breachvip (free); ghosint.search, leakosint (paid)
- Timeout: 30s

### Swatted (`SWATTED_API_TOKEN`)
- Session-based auth: token exchange for session credentials + CSRF
- Modules: leakosint, snusbase, breachint, stealerlogs, tiktok, instagram, shodan, shodan_dns, infodra, crypto
- Timeout: 60s per module

### BOSINT (`BOSINT_API_KEY`)
- REST API: `https://app.bosint.gg/bosintapi/{key}/{command}/{query}`
- Commands: email, username, phone, domain, ip, darkweb
- Timeout: 30s (90s for username)

All providers return optional/degraded results. The system works without any provider keys -- it just won't find external data.

---

## 10. Frontend Architecture

### Routing (2 pages)
| Path | Component | Purpose |
|------|-----------|---------|
| `/` | `Dashboard` | Investigation list, create, bulk delete |
| `/investigation/:id` | `UnifiedInvestigation` | Main investigation workspace |

### State Management
**Zustand store** (`store/investigationStore.js`) holds:
- `investigation`: Current investigation metadata
- `entities[]`: Mapped from API entities to frontend format (kind, value, label, confidence, risk, etc.)
- `relationships[]`: Mapped edges (fromId, toId, relType, confidence)
- `evidence[]`: Mapped evidence (type, content, verificationStatus, linked entity/edge IDs)
- `timeline[]`: Client-side timeline events
- `aiSuggestions[]`: AI-generated suggestions
- `ui`: Selection state, active tab, filters, graph layout positions

### Data Flow
1. `UnifiedInvestigation.loadInvestigation()` fetches all data via 4 parallel API calls
2. Data is mapped from API format to store format (different field names)
3. Polling every 3 seconds refreshes state during autonomous investigation
4. SSE via `LiveFeed` provides real-time event display (independent of polling)

### Layout
```
+-------------------------------------------------------------+
| Header: [Back] | Case Name + ID | Entity/Edge/Evidence count|
+-------------------------------------------------------------+
| Case Notes Panel (collapsible)                              |
+-------------------------------------------------------------+
| UniversalInput: Paste anything, Ctrl+Enter to investigate   |
| Status bar: Processed / Discovered / Depth / Queue          |
+-------------------------------------------------------------+
| Graph View (React Flow)    | Right Panel Tabs:              |
|                            |   [Live Feed] [Entities]       |
| - Auto-layout nodes       |   [Evidence]  [Report]         |
| - Custom entity nodes      |                               |
| - Edge confidence display  | Active panel content          |
+-------------------------------------------------------------+
```

### Styling
- Dark theme throughout (`bg-[#050505]`, `bg-black/50`, white/5 borders)
- Tailwind CSS with custom config via CRACO
- Shadcn/UI Radix primitives (button, badge, dialog, select, input, label)
- Sonner toasts (top-right, dark themed)
- Custom fonts: Manrope (body), JetBrains Mono (code), Rajdhani (headings)

---

## 11. Data Models (MongoDB Collections)

### `investigations`
```json
{
  "id": "uuid",
  "case_id": "CASE-XXXXXXXX",
  "name": "string",
  "description": "string",
  "notes": "string",
  "tags": ["string"],
  "status": "active|archived",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### `entities`
```json
{
  "id": "uuid",
  "investigation_id": "uuid",
  "entity_type": "person|username|email|phone|domain|ip|company|location|wallet|social|hash|url",
  "value": "string",
  "label": "string|null",
  "metadata": {},
  "confidence": 0.0-1.0,
  "risk_score": 0.0-1.0,
  "sources": ["string"],
  "notes": "string",
  "created_at": "datetime"
}
```

### `relationships`
```json
{
  "id": "uuid",
  "investigation_id": "uuid",
  "source_entity_id": "uuid",
  "target_entity_id": "uuid",
  "relationship_type": "owns|registered|resolves_to|used_on|interacts_with|linked_to|derived_from",
  "label": "string",
  "metadata": {},
  "confidence": 0.0-1.0,
  "created_at": "datetime"
}
```

### `evidence`
```json
{
  "id": "uuid",
  "investigation_id": "uuid",
  "entity_id": "uuid|null",
  "evidence_type": "screenshot|document|social_post|web_archive|metadata|breach|social_profile|public_record|infrastructure",
  "source_url": "string",
  "content": "string",
  "notes": "string",
  "tags": ["string"],
  "verification_status": "verified|unverified|disputed",
  "collected_at": "datetime"
}
```

### `timeline_events`
```json
{
  "id": "uuid",
  "investigation_id": "uuid",
  "event_type": "entity_added|evidence_added|relationship_discovered|enrichment_run|...",
  "entity_id": "uuid|null",
  "description": "string",
  "metadata": {},
  "timestamp": "datetime"
}
```

### `investigation_leads`
```json
{
  "id": "uuid",
  "investigation_id": "uuid",
  "lead_type": "alias_cluster|wallet_cluster|shared_infrastructure|username_reuse|high_risk_connection|timing_anomaly|missing_connection",
  "title": "string",
  "description": "string",
  "confidence": 0.0-1.0,
  "severity": "critical|high|medium|low",
  "status": "new|investigating|resolved|dismissed",
  "affected_entities": ["uuid"],
  "suggested_actions": [{"type": "string", "label": "string", "action": "string"}],
  "metadata": {}
}
```

### `chat_messages`
```json
{
  "id": "uuid",
  "investigation_id": "uuid",
  "session_id": "uuid",
  "role": "user|assistant",
  "content": "string",
  "timestamp": "datetime",
  "metadata": {}
}
```

### MongoDB Indexes
Created at startup in `lifespan()`:
- `investigations.id` (unique)
- `entities.investigation_id`, `entities.(id, investigation_id)`
- `relationships.investigation_id`, `relationships.(id, investigation_id)`
- `timeline_events.investigation_id`, `timeline_events.(investigation_id, timestamp desc)`
- `evidence.investigation_id`, `evidence.(id, investigation_id)`
- `ai_suggestions.(investigation_id, status)`
- `investigation_leads.investigation_id`, `investigation_leads.(id, investigation_id)`
- `chat_messages.(investigation_id, session_id)`

---

## 12. Testing

### Backend Tests (`backend/tests/test_investigation_api.py`)
- **918 lines, ~36 test cases** organized in classes:
  - `TestHealthAndAuth` -- API root, key validation
  - `TestInvestigations` -- CRUD, status toggle
  - `TestEntities` -- CRUD, type validation, batch create
  - `TestRelationships` -- CRUD
  - `TestEvidence` -- CRUD, verification status
  - `TestTimeline` -- Event listing
  - `TestAIAnalysis` -- AI analysis endpoint
  - `TestOSINTSearch` -- OSINT search (graceful degradation without keys)
  - `TestAutonomousInvestigation` -- Auto-investigate, status, engine integration (uses `TestClient`)

### Test Infrastructure (`conftest.py`)
- `pytest_configure()` runs before collection: starts MongoDB + uvicorn automatically
- Installs emergent stub if missing
- Creates `backend/.env` with test DB name if not present
- `pytest_unconfigure()` tears down mongod + server processes
- If `REACT_APP_BACKEND_URL` is already set, skips auto-start (for manual server testing)

### Running Tests
```powershell
# Auto-managed (conftest starts everything):
cd backend
python -m pytest tests/ -v

# Against manually-started server:
$env:REACT_APP_BACKEND_URL='http://127.0.0.1:8001'
python -m pytest tests/ -v
```

### Linting
```powershell
# Backend
python -m flake8 backend/server.py --max-line-length=150

# Frontend (built into CRA/CRACO -- no standalone eslint config)
cd frontend && yarn build   # ESLint errors fail build
cd frontend && yarn start   # ESLint warnings shown in console
```

---

## 13. CI/CD (`.github/workflows/ci.yml`)

Two jobs run on push to `main`/`copilot/**` and PRs to `main`:

### `backend-tests` (ubuntu-22.04)
1. Checkout + Python 3.11 setup
2. Install MongoDB 7.0 from official repo
3. `pip install` requirements (excluding `emergentintegrations` -- conftest installs stub)
4. **`flake8 backend/server.py --max-line-length=150`** (lint gate)
5. **`pytest backend/tests/ -v --tb=short`** with `PYTHONPATH=backend`

### `frontend-build` (ubuntu-22.04)
1. Checkout + Node 20 setup
2. `yarn install --frozen-lockfile`
3. **`yarn build`** with dummy env vars (validates ESLint + compilation)

### TestSprite (External GitHub App)
- Expects `testsprite_tests/` directory; blocks PRs if missing
- Either generate via TestSprite MCP or remove from branch protection

---

## 14. Security Considerations

- **API authentication:** All endpoints require `x-api-key` header. Default key is `trace-analyst-secret-2026` (must be rotated for production).
- **Rate limiting:** In-memory token-bucket rate limiter per API key. Categories: `general` (120 req/60s), `ai` (10 req/60s), `osint` (20 req/60s).
- **CORS:** Default `*` with `allow_credentials=False`. Set explicit `CORS_ORIGINS` for production with cookies/credentials.
- **No auth/session system:** No user accounts, sessions, or RBAC. The API key is the only gate.
- **Secrets:** All secrets loaded from environment variables. `.env` files are gitignored. `.env.example` contains only placeholders.
- **MongoDB:** No authentication configured by default (local dev). Use Atlas or configure auth for production.
- **OSINT provider keys:** Stored in env vars, never logged. Provider failures are caught and logged at debug level.

---

## 15. Known Issues and Tech Debt

### Critical / High Priority
1. **`server.py` is 3818 lines.** A `backend/routers/` directory exists as a placeholder. Splitting into `investigations.py`, `osint.py`, `ai.py`, `export.py`, `ingest.py`, `graph.py`, `leads.py` would massively improve maintainability. This is the single biggest tech debt item.
2. **No user authentication system.** A single shared API key is insufficient for multi-tenant or production use.
3. **In-memory investigation state.** `InvestigationEngine.investigations` dict is lost on server restart. Active investigations are abandoned. Consider persisting state to MongoDB.
4. **In-memory SSE queues.** `_investigation_event_queues` dict is also in-memory. Missed events on reconnect.

### Medium Priority
5. **Gemini model names rotate.** Google deprecates model IDs. Names are configurable via env but require manual updates. `GEMINI_MODEL_FLASH`, `GEMINI_MODEL_PRO`, `GEMINI_MODEL_CHAT`.
6. **Entity extraction uses regex only.** No NLP/NER. Phone, email, IP, wallet patterns are caught; freeform names, addresses, and context-dependent entities are missed.
7. **Frontend polling every 3 seconds.** `UnifiedInvestigation` polls all data via 4 API calls every 3s. This is wasteful for idle investigations. Should be reduced or switched to SSE-driven invalidation.
8. **`test_autonomous_engine.py` at repo root** is a placeholder script with no collected tests. Either implement or remove.
9. **`test_swatted.py` at repo root** is a manual test script, not integrated with pytest.

### Low Priority
10. **Frontend/backend field name mismatch.** The store maps API fields (e.g. `entity_type` -> `kind`, `source_entity_id` -> `fromId`) in `loadInvestigation()`. This creates a translation layer that's easy to get wrong.
11. **No pagination.** Entity/evidence lists use `.to_list(N)` with hardcoded limits. Large investigations could hit memory limits.
12. **No WebSocket fallback.** SSE works with HTTP/2 but some proxies buffer or drop SSE connections.
13. **`dy` file in repo root** is a junk API response dump. Should be deleted and added to `.gitignore`.
14. **`.cursor/` directory** should be added to `.gitignore`.

---

## 16. Suggested Next Steps

### Immediate (before next feature work)
1. **Split `server.py`** into route modules under `backend/routers/`. The file is too large to safely edit. Group by domain: investigations, entities, relationships, evidence, osint, ai, leads, graph, export, ingest.
2. **Add `.cursor/` and `dy` to `.gitignore`**, delete `dy`.
3. **Clean up root-level test scripts** (`test_autonomous_engine.py`, `test_swatted.py`) -- either integrate into pytest suite or remove.

### Short-term (next sprint)
4. **Persist investigation state to MongoDB** so autonomous investigations survive server restarts.
5. **Add pause/resume API endpoints** that actually work with the engine (currently the engine supports pause/resume but the routes only modify in-memory state).
6. **Reduce frontend polling** -- use SSE events to trigger data refresh instead of blind 3-second polling.
7. **Add error handling for SSE reconnection** in `LiveFeed.js` (currently retries after 3s but doesn't recover missed events).

### Medium-term
8. **Add user authentication** (JWT or session-based) if multi-user or production deployment is planned.
9. **Add NLP entity extraction** alongside regex for better freeform text parsing.
10. **Implement entity dedup at ingestion time** to prevent graph bloat (the `/entities/duplicates` + `/entities/merge` endpoints exist but aren't auto-triggered).
11. **Rate limit provider calls** per provider, not just per API key category.

### Optional Enhancements
12. Graph intelligence: node clustering visualization, risk score propagation, confidence color coding.
13. Visual upgrades: animated graph layout transitions, live node highlighting during enrichment.
14. Advanced pivoting: image reverse search, document parsing, timeline correlation.
15. Provider optimization: per-provider rate limits, cost tracking, failover ordering.

---

## 17. Key Files Quick Reference

| File | Lines | What It Does |
|------|-------|-------------|
| `backend/server.py` | 3818 | Everything: FastAPI app, all routes, models, OSINT providers, entity extraction, graph analysis, lead generation, AI chat, export |
| `backend/engine/investigation_engine.py` | 336 | Autonomous investigation orchestrator (async generator) |
| `backend/engine/pivot_planner.py` | 123 | Priority scoring + pivot decisions |
| `backend/engine/normalizer.py` | 276 | OSINT result normalization to unified schema |
| `backend/engine/graph_updater.py` | 189 | Writes investigation data to MongoDB |
| `backend/engine/models.py` | 96 | Pydantic models for engine domain |
| `backend/tests/conftest.py` | ~200 | Auto-start MongoDB + backend for tests |
| `backend/tests/test_investigation_api.py` | 918 | 36 integration tests |
| `frontend/src/components/investigation/UnifiedInvestigation.js` | 350 | Main investigation UI |
| `frontend/src/components/investigation/UniversalInput.js` | 157 | "Paste anything" input |
| `frontend/src/components/investigation/LiveFeed.js` | 194 | SSE event display |
| `frontend/src/components/workspace/GraphView.js` | 22558B | React Flow graph |
| `frontend/src/store/investigationStore.js` | 7392B | Zustand state management |
| `frontend/src/pages/Dashboard.js` | 15536B | Investigation list + create |
| `frontend/src/config/api.js` | ~30 | Axios config + BACKEND_URL |

---

## 18. Commit History (Recent)

```
660bd37 Autonomous investigation refactor: unified UI, investigation engine, SSE streaming, lint fixes
2c8386c Create SECURITY.md for security policy
4c76419 Add GitHub Actions CI workflow to run backend integration tests (#7)
35379ca Upgrade OSINT platform: export, entity/evidence CRUD, dedup/merge, ESLint CI fix (#8)
beb6d34 Merge pull request #6 (execution plan for cleanup)
a35fcb7 Address code review: use tempfile, extract TEST_DB_NAME, conda mongod paths
2d85726 Add conftest.py: auto-start MongoDB + backend for tests
b6b2e71 Refactor: env var API_KEY, timeline helper, remove unused tasks field
1e3935b Remove dead files: 5 Tab components, unused EntitiesPanel, 39 UI components
155d844 Improve performance: pre-compile regex, GZip, MongoDB indexes, useMemo
```

---

*Last updated: 2026-03-21 by Factory Droid (session: lint fixes, ESLint hook deps, CI flake8 step, commit)*

# Router Split Plan

`server.py` is ~3600 lines. Recommended split:

## Phase 1: Extract shared code
- `backend/deps.py` — DB connection, auth, rate limiter, helpers (serialize_datetime, create_timeline_event)
- `backend/models.py` — All Pydantic models (Investigation, Entity, Evidence, etc.)

## Phase 2: Extract routers
- `routers/investigations.py` — CRUD for investigations
- `routers/entities.py` — Entity CRUD + batch + dedup/merge
- `routers/relationships.py` — Relationship CRUD
- `routers/evidence.py` — Evidence CRUD + categories
- `routers/timeline.py` — Timeline events
- `routers/ai.py` — AI analysis + AI chat + suggestions (~500 lines)
- `routers/osint.py` — OSINT search (~200 lines)
- `routers/export.py` — JSON/CSV/Markdown export (~200 lines)
- `routers/ingest.py` — URL/text/file ingestion (~200 lines)
- `routers/graph.py` — Graph analysis, clusters, patterns
- `routers/leads.py` — Lead generation + CRUD
- `routers/auto_investigate.py` — Autonomous investigation + SSE stream

## Phase 3: Assembly
- `server.py` becomes thin: app creation, middleware, lifespan, include_router calls

## Dependencies to watch
- `create_timeline_event()` is called from entity/evidence/relationship CRUD
- `extract_entities_from_text()` is used in evidence ingest AND entity extraction endpoint
- `generate_investigation_leads()` has 500+ lines of business logic used by the leads router
- OSINT search functions are shared between `/osint/search` and the engine

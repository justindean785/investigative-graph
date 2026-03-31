"""
main.py — FastAPI application factory.

Responsibilities:
  - Configure logging
  - Define lifespan (MongoDB index creation, engine init, client teardown)
  - Wire CORS + GZip middleware
  - Include all routers

Entry point:  uvicorn main:app --host 0.0.0.0 --port 8001
Compat shim:  server.py re-exports `app` so `uvicorn server:app` also works.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from core.config import CORS_ORIGINS
from core.deps import (
    client,
    create_mongodb_indexes,
    db,
    set_investigation_engine,
)
from engine import InvestigationEngine
from fastapi import FastAPI
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from routers import (
    ai,
    auth,
    enrichment,
    entities,
    graph,
    investigations,
    osint,
    stream,
    system,
)
from routers.osint import osint_search_for_engine
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware

# ---------------------------------------------------------------------------
# Logging — configure once at the top of the entry-point module
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan — runs on startup and shutdown
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.

    Startup:
      1. Create MongoDB indexes (fail fast if Mongo is unreachable)
      2. Initialise the InvestigationEngine with the DB handle and the
         OSINT search wrapper from routers/osint.py
      3. Store the engine reference in core.deps so routers can retrieve it

    Shutdown:
      - Close the Motor MongoDB client cleanly
    """
    # 1. MongoDB indexes
    try:
        await create_mongodb_indexes()
    except (ServerSelectionTimeoutError, ConnectionFailure) as exc:
        logger.error(
            "MongoDB is not reachable. Start Mongo (see LOCAL_DEV.md: Docker, "
            "Atlas, or local service) and verify MONGO_URL in backend/.env. "
            "Details: %s",
            exc,
        )
        raise RuntimeError(
            "MongoDB connection failed during startup; "
            "fix MongoDB/MONGO_URL and restart the backend."
        ) from exc

    # 2. Investigation engine
    engine = InvestigationEngine(db, osint_search_for_engine)
    set_investigation_engine(engine)
    logger.info("Investigation engine initialised")

    yield

    # Shutdown — close Motor client
    client.close()
    logger.info("MongoDB client closed")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Trace Analyst API",
    description="AI-powered OSINT investigation platform",
    version="1.0.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# ---------------------------------------------------------------------------
# Routers
#
# Order matters: FastAPI matches routes in registration order.
# More-specific paths (e.g. /entities/duplicates) must be registered before
# broader parameterised paths (e.g. /entities/{entity_id}) within the same
# prefix.  Each router already handles this internally; here we just include
# them all.
# ---------------------------------------------------------------------------

app.include_router(auth.router)  # GET /api/,  POST /api/auth/validate
app.include_router(investigations.router)  # /api/investigations/...
app.include_router(
    entities.router
)  # /api/investigations/{id}/entities|relationships|evidence
app.include_router(graph.router)  # /api/investigations/{id}/graph/...
app.include_router(ai.router)  # /api/ai/..., /api/investigations/{id}/chat|suggestions
app.include_router(
    stream.router
)  # /api/investigations/{id}/auto-investigate|auto-status|stream
app.include_router(osint.router)  # /api/osint/search
app.include_router(
    enrichment.router
)  # /api/enrich/entity, /api/extract/entities, /api/investigations/{id}/entities/{eid}/enrichment
app.include_router(system.router)  # /api/evidence/categories

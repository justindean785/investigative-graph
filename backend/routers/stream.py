"""
routers/stream.py — Autonomous investigation and SSE streaming endpoints.

Routes (all nested under /api/investigations):
  POST /{investigation_id}/auto-investigate — start autonomous investigation
  GET  /{investigation_id}/auto-status      — poll investigation status
  GET  /{investigation_id}/stream           — SSE event stream

SSE CRITICAL NOTES:
  - event_generator() is a pure async generator; no blocking calls
  - asyncio.ensure_future() fires the investigation coroutine without awaiting it
  - investigation_event_queues is a module-level dict shared with the background task
  - The background task writes to every registered queue; the SSE handler reads one queue
  - A None sentinel signals completion to the SSE consumer
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

from core.deps import (
    db,
    enforce_rate_limit,
    get_investigation_engine,
    investigation_event_queues,
)
from core.security import validate_api_key
from fastapi import APIRouter, Header, HTTPException
from models import AutoInvestigateRequest
from sse_starlette.sse import EventSourceResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/investigations", tags=["stream"])


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/{investigation_id}/auto-investigate")
async def start_auto_investigation(
    investigation_id: str,
    request: AutoInvestigateRequest,
    x_api_key: str = Header(None),
):
    """
    Start autonomous investigation.

    Fires the investigation coroutine in the background via
    asyncio.ensure_future() so the HTTP response returns immediately
    while the engine runs and pushes events to the SSE queues.
    """
    await validate_api_key(x_api_key)
    enforce_rate_limit(x_api_key, "ai")

    engine = get_investigation_engine()

    inv = await db.investigations.find_one({"id": investigation_id})
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")

    if not engine:
        raise HTTPException(
            status_code=503, detail="Investigation engine not initialized"
        )

    current_state = engine.get_investigation_status(investigation_id)
    if current_state and current_state.status == "running":
        raise HTTPException(status_code=409, detail="Investigation already running")

    async def run_investigation() -> None:
        try:
            async for event in engine.start_investigation(
                investigation_id=investigation_id,
                seed_input=request.seed_input,
                max_depth=request.max_depth,
                max_entities=request.max_entities,
                confidence_threshold=request.confidence_threshold,
            ):
                queues = investigation_event_queues.get(investigation_id, [])
                for q in queues:
                    try:
                        q.put_nowait(event)
                    except asyncio.QueueFull:
                        pass
        except Exception as exc:
            logger.error("Auto-investigation failed: %s", exc, exc_info=True)
        finally:
            # Send None sentinel to every listening SSE consumer to signal completion
            queues = investigation_event_queues.get(investigation_id, [])
            for q in queues:
                q.put_nowait(None)

    asyncio.ensure_future(run_investigation())

    return {
        "success": True,
        "message": "Investigation started",
        "investigation_id": investigation_id,
        "stream_url": f"/api/investigations/{investigation_id}/stream",
    }


@router.get("/{investigation_id}/auto-status")
async def get_investigation_auto_status(
    investigation_id: str,
    x_api_key: str = Header(None),
):
    """Return the current status of an autonomous investigation."""
    await validate_api_key(x_api_key)

    engine = get_investigation_engine()

    if not engine:
        return {"engine_available": False, "status": "unavailable"}

    state = engine.get_investigation_status(investigation_id)

    if not state:
        return {"engine_available": True, "status": "not_started"}

    return {
        "engine_available": True,
        "status": state.status,
        "processed_count": state.processed_count,
        "entities_discovered": state.entities_discovered,
        "current_depth": state.current_depth,
        "queue_size": len(state.queue),
        "max_depth": state.max_depth,
        "max_entities": state.max_entities,
        "started_at": state.started_at.isoformat() if state.started_at else None,
        "completed_at": state.completed_at.isoformat() if state.completed_at else None,
        "error": state.error,
    }


@router.get("/{investigation_id}/stream")
async def stream_investigation_events(
    investigation_id: str,
    x_api_key: Optional[str] = Header(None),
    api_key: Optional[str] = None,
):
    """
    SSE stream of real-time investigation events.

    Accepts the API key via either:
      - x-api-key header  (standard)
      - ?api_key query parameter  (used by EventSource which cannot set headers)

    The generator yields events until a None sentinel is received from the
    background investigation task, then emits a 'completed' event and exits.
    """
    key = x_api_key or api_key
    if not key:
        raise HTTPException(status_code=401, detail="Missing API key")
    await validate_api_key(key)

    queue: asyncio.Queue = asyncio.Queue(maxsize=256)
    investigation_event_queues.setdefault(investigation_id, []).append(queue)

    async def event_generator():
        try:
            # Announce connection
            yield {
                "event": "connected",
                "data": json.dumps({"investigation_id": investigation_id}),
            }

            while True:
                event = await queue.get()

                if event is None:
                    # Sentinel: investigation completed or engine shut down
                    yield {
                        "event": "completed",
                        "data": json.dumps({"investigation_id": investigation_id}),
                    }
                    break

                yield {
                    "data": json.dumps(
                        event if isinstance(event, dict) else {"message": str(event)}
                    )
                }

        finally:
            # Always deregister this queue to prevent memory leaks
            queues = investigation_event_queues.get(investigation_id, [])
            if queue in queues:
                queues.remove(queue)

    return EventSourceResponse(event_generator())

"""
Autonomous investigation runner with MongoDB-backed state.

Survives process restarts: full state is upserted to ``investigation_states`` on
each emitted event; startup restores running/paused runs into memory.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field
from motor.motor_asyncio import AsyncIOMotorCollection

logger = logging.getLogger(__name__)


def _serialize_for_mongo(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _serialize_for_mongo(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize_for_mongo(v) for v in obj]
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, BaseModel):
        return _serialize_for_mongo(obj.model_dump(mode="python"))
    return obj


class ExecutionEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    kind: str
    message: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PersistedInvestigationState(BaseModel):
    """Full serializable snapshot for MongoDB ``investigation_states``."""

    model_config = ConfigDict(extra="ignore")

    investigation_id: str
    status: Literal["idle", "running", "paused", "completed", "failed"] = "idle"
    step_index: int = 0
    events: List[Dict[str, Any]] = Field(default_factory=list)
    event_queue: List[Dict[str, Any]] = Field(default_factory=list)
    active_tasks: List[Dict[str, Any]] = Field(default_factory=list)
    graph_snapshot: Dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error_message: Optional[str] = None


class InvestigationEngine:
    """
    In-memory cache keyed by investigation_id, backed by ``investigation_states``.
    """

    def __init__(self, collection: AsyncIOMotorCollection):
        self._col = collection
        self._investigations: Dict[str, PersistedInvestigationState] = {}

    def _default_queue(self) -> List[Dict[str, Any]]:
        return [
            {"id": "scan_entities", "label": "Scan entities", "status": "pending"},
            {"id": "enrich_indicators", "label": "Enrich indicators", "status": "pending"},
            {"id": "graph_pass", "label": "Graph intelligence pass", "status": "pending"},
            {"id": "finalize", "label": "Finalize pass", "status": "pending"},
        ]

    def _steps(self) -> List[tuple]:
        return [
            ("step", "Scanning case entities", {"phase": "scan_entities"}),
            ("step", "Running enrichment heuristics", {"phase": "enrich_indicators"}),
            ("graph_update", "Refreshing graph intelligence context", {"phase": "graph_pass"}),
            ("step", "Finalizing autonomous pass", {"phase": "finalize"}),
        ]

    async def _persist(self, state: PersistedInvestigationState) -> None:
        state.updated_at = datetime.now(timezone.utc)
        doc = _serialize_for_mongo(state.model_dump(mode="python"))
        await self._col.update_one(
            {"investigation_id": state.investigation_id},
            {"$set": doc},
            upsert=True,
        )

    async def load_state_from_db(self, investigation_id: str) -> Optional[PersistedInvestigationState]:
        doc = await self._col.find_one({"investigation_id": investigation_id}, {"_id": 0})
        if not doc:
            return None
        if isinstance(doc.get("updated_at"), str):
            doc["updated_at"] = datetime.fromisoformat(doc["updated_at"])
        for ev in doc.get("events") or []:
            if isinstance(ev.get("timestamp"), str):
                ev["timestamp"] = datetime.fromisoformat(ev["timestamp"])
        return PersistedInvestigationState(**doc)

    def _get_or_create_memory(self, investigation_id: str) -> PersistedInvestigationState:
        if investigation_id not in self._investigations:
            self._investigations[investigation_id] = PersistedInvestigationState(
                investigation_id=investigation_id,
                event_queue=self._default_queue(),
            )
        return self._investigations[investigation_id]

    async def ensure_loaded(self, investigation_id: str) -> PersistedInvestigationState:
        if investigation_id in self._investigations:
            return self._investigations[investigation_id]
        loaded = await self.load_state_from_db(investigation_id)
        if loaded:
            self._investigations[investigation_id] = loaded
            return loaded
        return self._get_or_create_memory(investigation_id)

    async def restore_running_from_mongo(self) -> int:
        """Load investigations with status running/paused into memory. Returns count restored."""
        count = 0
        cursor = self._col.find(
            {"status": {"$in": ["running", "paused"]}},
            {"_id": 0},
        )
        async for doc in cursor:
            iid = doc.get("investigation_id")
            if not iid:
                continue
            if isinstance(doc.get("updated_at"), str):
                doc["updated_at"] = datetime.fromisoformat(doc["updated_at"])
            for ev in doc.get("events") or []:
                if isinstance(ev.get("timestamp"), str):
                    ev["timestamp"] = datetime.fromisoformat(ev["timestamp"])
            try:
                self._investigations[iid] = PersistedInvestigationState(**doc)
                count += 1
            except Exception as e:
                logger.warning("Skip corrupt engine state for %s: %s", iid, e)
        if count:
            logger.info("Restored %d investigation engine run(s) from MongoDB", count)
        return count

    async def sync_cache_from_db(self, investigation_id: str) -> PersistedInvestigationState:
        """Drop in-memory entry and reload from Mongo (simulates reconnect after restart)."""
        self._investigations.pop(investigation_id, None)
        loaded = await self.load_state_from_db(investigation_id)
        if loaded:
            self._investigations[investigation_id] = loaded
            return loaded
        return self._get_or_create_memory(investigation_id)

    async def get_public_state(self, investigation_id: str) -> Optional[PersistedInvestigationState]:
        return await self.ensure_loaded(investigation_id)

    async def delete_state(self, investigation_id: str) -> None:
        self._investigations.pop(investigation_id, None)
        await self._col.delete_one({"investigation_id": investigation_id})

    async def investigate(self, investigation_id: str) -> AsyncIterator[ExecutionEvent]:
        """
        Autonomous investigation generator. Persists after each yielded event.
        Resumes from ``step_index`` if status was running; if completed, starts a new pass.
        """
        state = await self.ensure_loaded(investigation_id)

        if state.status == "completed":
            state.step_index = 0
            state.events = []
            state.error_message = None
            state.event_queue = self._default_queue()
            state.active_tasks = []
            state.graph_snapshot = {}

        state.status = "running"
        await self._persist(state)

        steps = self._steps()
        try:
            for i in range(state.step_index, len(steps)):
                kind, message, payload = steps[i]
                phase = payload.get("phase", "")
                for t in state.event_queue:
                    if t.get("id") == phase:
                        t["status"] = "running"
                state.active_tasks = [
                    {
                        "id": phase,
                        "label": next(
                            (x["label"] for x in state.event_queue if x["id"] == phase),
                            phase,
                        ),
                        "status": "running",
                    }
                ]

                ev = ExecutionEvent(kind=kind, message=message, payload=payload)
                state.events.append(ev.model_dump(mode="json"))
                state.step_index = i + 1
                for t in state.event_queue:
                    if t.get("id") == phase:
                        t["status"] = "completed"
                state.active_tasks = []
                await self._persist(state)
                yield ev
                await asyncio.sleep(0)

            state.status = "completed"
            state.step_index = len(steps)
            state.active_tasks = []
            await self._persist(state)
            done_ev = ExecutionEvent(
                kind="completed",
                message="Autonomous investigation pass finished",
                payload={},
            )
            state.events.append(done_ev.model_dump(mode="json"))
            await self._persist(state)
            yield done_ev
        except Exception as e:
            logger.exception("Engine failed for %s", investigation_id)
            state.status = "failed"
            state.error_message = str(e)
            await self._persist(state)
            yield ExecutionEvent(kind="error", message=str(e), payload={"error": True})


_engine: Optional[InvestigationEngine] = None


def get_investigation_engine(collection: AsyncIOMotorCollection) -> InvestigationEngine:
    global _engine
    if _engine is None:
        _engine = InvestigationEngine(collection)
    return _engine

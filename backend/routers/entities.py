"""
routers/entities.py — Entity, Relationship, and Evidence endpoints.

Routes (all nested under /api/investigations):
  POST   /{investigation_id}/entities                          — create entity
  GET    /{investigation_id}/entities                          — list entities
  PATCH  /{investigation_id}/entities/{entity_id}             — update entity
  DELETE /{investigation_id}/entities/{entity_id}             — delete entity
  POST   /{investigation_id}/entities/batch                   — batch create entities
  GET    /{investigation_id}/entities/duplicates              — find duplicate candidates
  POST   /{investigation_id}/entities/merge                   — merge duplicate entities

  POST   /{investigation_id}/relationships                    — create relationship
  GET    /{investigation_id}/relationships                    — list relationships
  DELETE /{investigation_id}/relationships/{relationship_id} — delete relationship

  POST   /{investigation_id}/evidence                         — create evidence
  GET    /{investigation_id}/evidence                         — list evidence
  PATCH  /{investigation_id}/evidence/{evidence_id}          — update evidence
  DELETE /{investigation_id}/evidence/{evidence_id}          — delete evidence

All business logic preserved verbatim from server.py.
Only import paths and router prefix differ.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from core.deps import (
    create_timeline_event,
    db,
    serialize_datetime,
)
from core.security import validate_api_key
from fastapi import APIRouter, Header, HTTPException
from models import (
    Entity,
    EntityCreate,
    EntityMergeRequest,
    EntityUpdate,
    Evidence,
    EvidenceCreate,
    EvidenceUpdate,
    Relationship,
    RelationshipCreate,
)

router = APIRouter(prefix="/api/investigations", tags=["entities"])


# ---------------------------------------------------------------------------
# Deduplication helpers  (only used by this router)
# ---------------------------------------------------------------------------

_DEDUP_SUBSTRING_SCORE: float = 0.85  # one value is a substring of the other
_DEDUP_MIN_SCORE: float = 0.75  # minimum Jaccard bigram score to report


def _bigrams(s: str) -> set:
    """Return the set of character bigrams for *s*."""
    return {s[i : i + 2] for i in range(len(s) - 1)}


# ===========================================================================
# ENTITY ROUTES
# ===========================================================================


@router.post("/{investigation_id}/entities", response_model=Entity)
async def create_entity(
    investigation_id: str,
    input: EntityCreate,
    x_api_key: str = Header(None),
):
    await validate_api_key(x_api_key)

    entity = Entity(investigation_id=investigation_id, **input.model_dump())

    doc = serialize_datetime(entity.model_dump())
    await db.entities.insert_one(doc)

    await create_timeline_event(
        investigation_id,
        "entity_added",
        f"Added {entity.entity_type}: {entity.value}",
        entity_id=entity.id,
    )

    return entity


@router.get("/{investigation_id}/entities")
async def get_entities(
    investigation_id: str,
    x_api_key: str = Header(None),
    skip: int = 0,
    limit: int = 500,
):
    await validate_api_key(x_api_key)
    limit = min(limit, 2000)

    entities = (
        await db.entities.find({"investigation_id": investigation_id}, {"_id": 0})
        .skip(skip)
        .limit(limit)
        .to_list(limit)
    )
    for ent in entities:
        if isinstance(ent.get("created_at"), str):
            ent["created_at"] = datetime.fromisoformat(ent["created_at"])

    return entities


@router.patch(
    "/{investigation_id}/entities/{entity_id}",
    response_model=Entity,
)
async def update_entity(
    investigation_id: str,
    entity_id: str,
    input: EntityUpdate,
    x_api_key: str = Header(None),
):
    """Partially update an entity's mutable fields (value, label, notes, confidence, etc.)."""
    await validate_api_key(x_api_key)

    entity = await db.entities.find_one(
        {"id": entity_id, "investigation_id": investigation_id}, {"_id": 0}
    )
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    update_data = input.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    await db.entities.update_one(
        {"id": entity_id, "investigation_id": investigation_id},
        {"$set": update_data},
    )

    updated = await db.entities.find_one(
        {"id": entity_id, "investigation_id": investigation_id}, {"_id": 0}
    )
    if isinstance(updated.get("created_at"), str):
        updated["created_at"] = datetime.fromisoformat(updated["created_at"])

    await create_timeline_event(
        investigation_id,
        "entity_updated",
        f"Entity updated: {updated.get('value', entity_id)}",
        entity_id=entity_id,
    )

    return updated


@router.delete("/{investigation_id}/entities/{entity_id}")
async def delete_entity(
    investigation_id: str,
    entity_id: str,
    x_api_key: str = Header(None),
):
    await validate_api_key(x_api_key)

    result = await db.entities.delete_one(
        {"id": entity_id, "investigation_id": investigation_id}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Entity not found")

    # Cascade-delete relationships that reference this entity
    await db.relationships.delete_many(
        {
            "investigation_id": investigation_id,
            "$or": [
                {"source_entity_id": entity_id},
                {"target_entity_id": entity_id},
            ],
        }
    )

    await create_timeline_event(
        investigation_id,
        "entity_removed",
        "Removed entity",
        entity_id=entity_id,
    )

    return {"success": True}


@router.post("/{investigation_id}/entities/batch")
async def add_entities_batch(
    investigation_id: str,
    entities: List[EntityCreate],
    x_api_key: Optional[str] = Header(None),
):
    """Add multiple entities at once (e.g. from detected indicators)."""
    await validate_api_key(x_api_key)

    created_entities: List[Entity] = []
    docs_to_insert: List[Dict[str, Any]] = []

    for entity_data in entities:
        entity = Entity(investigation_id=investigation_id, **entity_data.model_dump())
        docs_to_insert.append(serialize_datetime(entity.model_dump()))
        created_entities.append(entity)

    if docs_to_insert:
        await db.entities.insert_many(docs_to_insert)

    await create_timeline_event(
        investigation_id,
        "entities_batch_added",
        f"Batch added {len(created_entities)} entities",
        metadata={"count": len(created_entities)},
    )

    return {
        "success": True,
        "created_count": len(created_entities),
        "entities": [serialize_datetime(e.model_dump()) for e in created_entities],
    }


@router.get("/{investigation_id}/entities/duplicates")
async def find_duplicate_entities(
    investigation_id: str,
    x_api_key: Optional[str] = Header(None),
):
    """
    Detect potential duplicate entities by comparing normalised values
    across entities of the same type.  Returns candidate pairs with a
    similarity score so the analyst can decide whether to merge.
    """
    await validate_api_key(x_api_key)

    entities = await db.entities.find(
        {"investigation_id": investigation_id}, {"_id": 0}
    ).to_list(10000)

    # Group by type to limit comparison scope
    by_type: Dict[str, list] = {}
    for e in entities:
        et = e.get("entity_type", "unknown")
        by_type.setdefault(et, []).append(e)

    candidates: List[Dict[str, Any]] = []

    for etype, group in by_type.items():
        for i, a in enumerate(group):
            for b in group[i + 1 :]:
                val_a = (a.get("value") or "").lower().strip()
                val_b = (b.get("value") or "").lower().strip()
                if not val_a or not val_b:
                    continue

                if val_a == val_b:
                    score = 1.0
                elif val_a in val_b or val_b in val_a:
                    score = _DEDUP_SUBSTRING_SCORE
                else:
                    bg_a = _bigrams(val_a)
                    bg_b = _bigrams(val_b)
                    union = bg_a | bg_b
                    score = len(bg_a & bg_b) / len(union) if union else 0.0

                if score >= _DEDUP_MIN_SCORE:
                    candidates.append(
                        {
                            "entity_a": {
                                "id": a["id"],
                                "value": a.get("value"),
                                "label": a.get("label"),
                                "type": etype,
                            },
                            "entity_b": {
                                "id": b["id"],
                                "value": b.get("value"),
                                "label": b.get("label"),
                                "type": etype,
                            },
                            "similarity_score": round(score, 3),
                            "match_type": "exact" if score == 1.0 else "fuzzy",
                        }
                    )

    candidates.sort(key=lambda x: x["similarity_score"], reverse=True)

    return {
        "success": True,
        "duplicate_candidates": candidates,
        "total_found": len(candidates),
    }


@router.post("/{investigation_id}/entities/merge")
async def merge_entities(
    investigation_id: str,
    request: EntityMergeRequest,
    x_api_key: Optional[str] = Header(None),
):
    """
    Merge a duplicate entity into a primary entity.

    All relationships that pointed to the duplicate are re-parented to the
    primary entity, evidence links are updated, and the duplicate is deleted.
    The primary entity's sources list is augmented with the duplicate's sources.
    """
    await validate_api_key(x_api_key)

    primary = await db.entities.find_one(
        {"id": request.primary_entity_id, "investigation_id": investigation_id},
        {"_id": 0},
    )
    if not primary:
        raise HTTPException(status_code=404, detail="Primary entity not found")

    duplicate = await db.entities.find_one(
        {"id": request.duplicate_entity_id, "investigation_id": investigation_id},
        {"_id": 0},
    )
    if not duplicate:
        raise HTTPException(status_code=404, detail="Duplicate entity not found")

    if primary["id"] == duplicate["id"]:
        raise HTTPException(
            status_code=400, detail="Cannot merge an entity with itself"
        )

    dup_id = duplicate["id"]
    pri_id = primary["id"]

    # Re-parent relationships: replace duplicate references with primary
    await db.relationships.update_many(
        {"investigation_id": investigation_id, "source_entity_id": dup_id},
        {"$set": {"source_entity_id": pri_id}},
    )
    await db.relationships.update_many(
        {"investigation_id": investigation_id, "target_entity_id": dup_id},
        {"$set": {"target_entity_id": pri_id}},
    )

    # Remove self-loops that may have been created
    await db.relationships.delete_many(
        {
            "investigation_id": investigation_id,
            "source_entity_id": pri_id,
            "target_entity_id": pri_id,
        }
    )

    # Re-link evidence
    await db.evidence.update_many(
        {"investigation_id": investigation_id, "entity_id": dup_id},
        {"$set": {"entity_id": pri_id}},
    )

    # Merge sources lists (deduplicate)
    merged_sources = list(
        set(primary.get("sources", []) + duplicate.get("sources", []))
    )

    # Merge notes if duplicate has non-empty notes
    merged_notes = primary.get("notes", "")
    if duplicate.get("notes"):
        sep = "\n---\n" if merged_notes else ""
        merged_notes = merged_notes + sep + duplicate["notes"]

    await db.entities.update_one(
        {"id": pri_id},
        {"$set": {"sources": merged_sources, "notes": merged_notes}},
    )

    # Delete the duplicate
    await db.entities.delete_one({"id": dup_id, "investigation_id": investigation_id})

    await create_timeline_event(
        investigation_id,
        "entities_merged",
        f"Merged entity '{duplicate.get('value')}' into '{primary.get('value')}'",
        entity_id=pri_id,
        metadata={"merged_entity_id": dup_id, "primary_entity_id": pri_id},
    )

    updated_primary = await db.entities.find_one({"id": pri_id}, {"_id": 0})
    if isinstance(updated_primary.get("created_at"), str):
        updated_primary["created_at"] = datetime.fromisoformat(
            updated_primary["created_at"]
        )

    return {
        "success": True,
        "primary_entity": updated_primary,
        "merged_entity_id": dup_id,
    }


# ===========================================================================
# RELATIONSHIP ROUTES
# ===========================================================================


@router.post(
    "/{investigation_id}/relationships",
    response_model=Relationship,
)
async def create_relationship(
    investigation_id: str,
    input: RelationshipCreate,
    x_api_key: str = Header(None),
):
    await validate_api_key(x_api_key)

    relationship = Relationship(investigation_id=investigation_id, **input.model_dump())

    doc = serialize_datetime(relationship.model_dump())
    await db.relationships.insert_one(doc)

    await create_timeline_event(
        investigation_id,
        "relationship_discovered",
        f"Connection discovered: {relationship.relationship_type}",
    )

    return relationship


@router.get("/{investigation_id}/relationships")
async def get_relationships(
    investigation_id: str,
    x_api_key: str = Header(None),
    skip: int = 0,
    limit: int = 500,
):
    await validate_api_key(x_api_key)
    limit = min(limit, 2000)

    relationships = (
        await db.relationships.find({"investigation_id": investigation_id}, {"_id": 0})
        .skip(skip)
        .limit(limit)
        .to_list(limit)
    )
    for rel in relationships:
        if isinstance(rel.get("created_at"), str):
            rel["created_at"] = datetime.fromisoformat(rel["created_at"])

    return relationships


@router.delete("/{investigation_id}/relationships/{relationship_id}")
async def delete_relationship(
    investigation_id: str,
    relationship_id: str,
    x_api_key: str = Header(None),
):
    await validate_api_key(x_api_key)

    result = await db.relationships.delete_one(
        {"id": relationship_id, "investigation_id": investigation_id}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Relationship not found")

    return {"success": True}


# ===========================================================================
# EVIDENCE ROUTES
# ===========================================================================


@router.post(
    "/{investigation_id}/evidence",
    response_model=Evidence,
)
async def create_evidence(
    investigation_id: str,
    input: EvidenceCreate,
    x_api_key: str = Header(None),
):
    await validate_api_key(x_api_key)

    evidence = Evidence(investigation_id=investigation_id, **input.model_dump())

    doc = serialize_datetime(evidence.model_dump())
    await db.evidence.insert_one(doc)

    await create_timeline_event(
        investigation_id,
        "evidence_added",
        f"Added evidence: {evidence.evidence_type}",
        entity_id=evidence.entity_id,
    )

    return evidence


@router.get("/{investigation_id}/evidence")
async def get_evidence(
    investigation_id: str,
    x_api_key: str = Header(None),
    skip: int = 0,
    limit: int = 500,
):
    await validate_api_key(x_api_key)
    limit = min(limit, 2000)

    evidence = (
        await db.evidence.find({"investigation_id": investigation_id}, {"_id": 0})
        .skip(skip)
        .limit(limit)
        .to_list(limit)
    )
    for ev in evidence:
        if isinstance(ev.get("collected_at"), str):
            ev["collected_at"] = datetime.fromisoformat(ev["collected_at"])

    return evidence


@router.patch(
    "/{investigation_id}/evidence/{evidence_id}",
    response_model=Evidence,
)
async def update_evidence(
    investigation_id: str,
    evidence_id: str,
    input: EvidenceUpdate,
    x_api_key: str = Header(None),
):
    """Partially update an evidence item — notes, tags, verification status, or linked entity."""
    await validate_api_key(x_api_key)

    ev = await db.evidence.find_one(
        {"id": evidence_id, "investigation_id": investigation_id}, {"_id": 0}
    )
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")

    update_data = input.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    await db.evidence.update_one(
        {"id": evidence_id, "investigation_id": investigation_id},
        {"$set": update_data},
    )

    updated = await db.evidence.find_one(
        {"id": evidence_id, "investigation_id": investigation_id}, {"_id": 0}
    )
    if isinstance(updated.get("collected_at"), str):
        updated["collected_at"] = datetime.fromisoformat(updated["collected_at"])

    await create_timeline_event(
        investigation_id,
        "evidence_updated",
        f"Evidence updated: {updated.get('evidence_type', evidence_id)}",
    )

    return updated


@router.delete("/{investigation_id}/evidence/{evidence_id}")
async def delete_evidence(
    investigation_id: str,
    evidence_id: str,
    x_api_key: str = Header(None),
):
    await validate_api_key(x_api_key)

    result = await db.evidence.delete_one(
        {"id": evidence_id, "investigation_id": investigation_id}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Evidence not found")

    return {"success": True}

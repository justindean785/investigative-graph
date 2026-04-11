"""
Graph updater — automatically creates nodes, edges, and maintains provenance.
"""

import logging
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from .models import NormalizedEntity, NormalizedEvidence

logger = logging.getLogger(__name__)


class GraphUpdater:
    """Automatically build and update investigation graph."""
    
    def __init__(self, db):
        """Initialize with database connection."""
        self.db = db
    
    async def add_entity_to_graph(
        self,
        investigation_id: str,
        entity: NormalizedEntity
    ) -> str:
        """
        Add entity to investigation graph.
        
        Returns entity_id from database.
        """
        try:
            now = datetime.now(timezone.utc).isoformat()
            entity_id = str(uuid.uuid4())
            entity_doc = {
                "id": entity_id,
                "investigation_id": investigation_id,
                "entity_type": entity.entity_type,
                "value": entity.value,
                "label": entity.label or entity.value,
                "confidence": entity.confidence,
                "risk_score": entity.risk_score,
                "sources": [
                    {
                        "provider": src.provider,
                        "service": src.service,
                        "found_at": src.found_at.isoformat(),
                        "confidence": src.confidence,
                        "raw_data": src.raw_data
                    }
                    for src in entity.sources
                ],
                "metadata": entity.metadata,
                "tags": entity.tags,
                "created_at": now,
                "updated_at": now
            }
            
            await self.db.entities.insert_one(entity_doc)
            
            logger.info(f"Added entity {entity.entity_type}:{entity.value} with ID {entity_id}")
            
            return entity_id
            
        except Exception as e:
            logger.error(f"Failed to add entity to graph: {e}")
            raise
    
    async def create_relationship(
        self,
        investigation_id: str,
        source_entity_id: str,
        target_entity_id: str,
        relationship_type: str,
        confidence: float = 0.5,
        evidence_ids: Optional[List[str]] = None
    ) -> str:
        """
        Create a relationship between two entities.
        
        Returns relationship_id.
        """
        try:
            relationship_id = str(uuid.uuid4())
            relationship_doc = {
                "id": relationship_id,
                "investigation_id": investigation_id,
                "source_entity_id": source_entity_id,
                "target_entity_id": target_entity_id,
                "relationship_type": relationship_type,
                "confidence": confidence,
                "evidence_ids": evidence_ids or [],
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            await self.db.relationships.insert_one(relationship_doc)
            
            logger.info(f"Created relationship {relationship_type} between {source_entity_id} and {target_entity_id}")
            
            return relationship_id
            
        except Exception as e:
            logger.error(f"Failed to create relationship: {e}")
            raise
    
    async def add_evidence(
        self,
        investigation_id: str,
        evidence: NormalizedEvidence
    ) -> str:
        """
        Add evidence to investigation.
        
        Returns evidence_id.
        """
        try:
            evidence_id = str(uuid.uuid4())
            evidence_doc = {
                "id": evidence_id,
                "investigation_id": investigation_id,
                "evidence_type": evidence.evidence_type,
                "content": evidence.content,
                "source_url": evidence.source_url,
                "sources": [
                    {
                        "provider": src.provider,
                        "service": src.service,
                        "found_at": src.found_at.isoformat(),
                        "confidence": src.confidence
                    }
                    for src in evidence.sources
                ],
                "entity_ids": evidence.linked_entities,
                "verification_status": evidence.verification_status,
                "tags": evidence.tags,
                "metadata": evidence.metadata,
                "collected_at": evidence.collected_at.isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            await self.db.evidence.insert_one(evidence_doc)
            
            logger.info(f"Added evidence {evidence.evidence_type} with ID {evidence_id}")
            
            return evidence_id
            
        except Exception as e:
            logger.error(f"Failed to add evidence: {e}")
            raise
    
    async def link_derived_entity(
        self,
        investigation_id: str,
        parent_entity_id: str,
        child_entity_id: str
    ):
        """Create 'derived_from' relationship between parent and child entity."""
        await self.create_relationship(
            investigation_id=investigation_id,
            source_entity_id=child_entity_id,
            target_entity_id=parent_entity_id,
            relationship_type="derived_from",
            confidence=0.8
        )
    
    async def update_timeline(
        self,
        investigation_id: str,
        event_type: str,
        description: str,
        entity_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Add event to investigation timeline."""
        try:
            timeline_doc = {
                "id": str(uuid.uuid4()),
                "investigation_id": investigation_id,
                "event_type": event_type,
                "description": description,
                "entity_id": entity_id,
                "metadata": metadata or {},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await self.db.timeline.insert_one(timeline_doc)
            
        except Exception as e:
            logger.error(f"Failed to update timeline: {e}")

"""
Main autonomous investigation engine.

Orchestrates entity extraction, enrichment, pivoting, and graph construction.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime
from collections import deque

from .models import (
    NormalizedEntity,
    InvestigationState,
    PivotTask,
    ExecutionEvent
)
from .entity_processor import EntityProcessor
from .pivot_planner import PivotPlanner
from .normalizer import ProviderNormalizer
from .graph_updater import GraphUpdater

logger = logging.getLogger(__name__)


class InvestigationEngine:
    """Autonomous investigation orchestrator."""
    
    def __init__(self, db, osint_search_func):
        """
        Initialize investigation engine.
        
        Args:
            db: Motor database instance
            osint_search_func: Async function for OSINT searches
        """
        self.db = db
        self.entity_processor = EntityProcessor(osint_search_func)
        self.graph_updater = GraphUpdater(db)
        self.normalizer = ProviderNormalizer()
        
        # Active investigations
        self.investigations: Dict[str, InvestigationState] = {}
    
    async def start_investigation(
        self,
        investigation_id: str,
        seed_input: str,
        max_depth: int = 5,
        max_entities: int = 100,
        confidence_threshold: float = 0.3
    ) -> AsyncGenerator[ExecutionEvent, None]:
        """
        Start autonomous investigation from seed input.
        
        Yields ExecutionEvents as the investigation progresses.
        """
        # Initialize investigation state
        state = InvestigationState(
            investigation_id=investigation_id,
            status="running",
            max_depth=max_depth,
            max_entities=max_entities,
            confidence_threshold=confidence_threshold,
            started_at=datetime.utcnow()
        )
        self.investigations[investigation_id] = state
        
        yield ExecutionEvent(
            event_type="investigation_started",
            investigation_id=investigation_id,
            message=f"Starting autonomous investigation (max_depth={max_depth}, max_entities={max_entities})"
        )
        
        try:
            # Extract seed entities from input
            yield ExecutionEvent(
                event_type="entity_discovered",
                investigation_id=investigation_id,
                message="Extracting entities from input..."
            )
            
            seed_entities = EntityProcessor.extract_entities_from_text(seed_input)
            
            if not seed_entities:
                yield ExecutionEvent(
                    event_type="error",
                    investigation_id=investigation_id,
                    message="No entities found in input"
                )
                state.status = "error"
                state.error = "No entities found"
                return
            
            # Convert to NormalizedEntity and add to graph
            for seed_ent in seed_entities:
                entity = NormalizedEntity(
                    entity_type=seed_ent["type"],
                    value=seed_ent["value"],
                    confidence=0.9,  # High confidence for user-provided seeds
                    metadata=seed_ent.get("metadata", {})
                )
                
                # Add to graph
                entity_id = await self.graph_updater.add_entity_to_graph(investigation_id, entity)
                entity.id = entity_id
                
                # Create pivot task
                task = PivotPlanner.create_pivot_task(entity, depth=0)
                state.queue.append(task)
                state.entities_discovered += 1
                
                yield ExecutionEvent(
                    event_type="entity_discovered",
                    investigation_id=investigation_id,
                    message=f"Discovered {entity.entity_type}: {entity.value}",
                    entity_id=entity_id,
                    data={"entity_type": entity.entity_type, "value": entity.value}
                )
            
            # Main investigation loop
            async for event in self._process_investigation_queue(investigation_id):
                yield event
            
            # Mark complete
            state.status = "completed"
            state.completed_at = datetime.utcnow()
            
            yield ExecutionEvent(
                event_type="investigation_completed",
                investigation_id=investigation_id,
                message=f"Investigation complete: processed {state.processed_count} entities, discovered {state.entities_discovered} total",
                data={
                    "processed_count": state.processed_count,
                    "entities_discovered": state.entities_discovered,
                    "max_depth_reached": state.current_depth
                }
            )
            
        except Exception as e:
            logger.error(f"Investigation {investigation_id} failed: {e}", exc_info=True)
            state.status = "error"
            state.error = str(e)
            
            yield ExecutionEvent(
                event_type="error",
                investigation_id=investigation_id,
                message=f"Investigation failed: {str(e)}"
            )
    
    async def _process_investigation_queue(
        self,
        investigation_id: str
    ) -> AsyncGenerator[ExecutionEvent, None]:
        """Process the investigation queue until empty or limits reached."""
        state = self.investigations[investigation_id]
        
        while state.queue and state.status == "running":
            # Check stop conditions
            if state.processed_count >= state.max_entities:
                yield ExecutionEvent(
                    event_type="investigation_paused",
                    investigation_id=investigation_id,
                    message=f"Max entities ({state.max_entities}) reached"
                )
                state.status = "paused"
                break
            
            # Sort queue by priority (highest first)
            state.queue.sort(key=lambda t: t.priority, reverse=True)
            
            # Dequeue next task
            task = state.queue.pop(0)
            
            # Check if already visited
            if task.entity_value.lower() in state.visited_entities:
                logger.debug(f"Skipping already-visited entity: {task.entity_value}")
                continue
            
            # Mark as visited
            state.visited_entities[task.entity_value.lower()] = True
            state.processed_count += 1
            state.current_depth = max(state.current_depth, task.depth)
            
            yield ExecutionEvent(
                event_type="enrichment_started",
                investigation_id=investigation_id,
                message=f"Enriching {task.entity_type}: {task.entity_value} (depth={task.depth}, priority={task.priority:.2f})",
                entity_id=task.entity_id,
                data={"depth": task.depth, "priority": task.priority}
            )
            
            # Enrich the entity
            async for event in self._enrich_and_pivot(investigation_id, task):
                yield event
    
    async def _enrich_and_pivot(
        self,
        investigation_id: str,
        task: PivotTask
    ) -> AsyncGenerator[ExecutionEvent, None]:
        """Enrich an entity and pivot to discovered entities."""
        state = self.investigations[investigation_id]
        
        # Create entity object for enrichment
        entity = NormalizedEntity(
            id=task.entity_id,
            entity_type=task.entity_type,
            value=task.entity_value,
            confidence=0.5
        )
        
        # Enrich entity
        yield ExecutionEvent(
            event_type="provider_queried",
            investigation_id=investigation_id,
            message=f"Querying providers for {entity.entity_type}: {entity.value}",
            entity_id=entity.id
        )
        
        enrichment_result = await self.entity_processor.enrich_entity(entity)
        
        if not enrichment_result["success"]:
            yield ExecutionEvent(
                event_type="error",
                investigation_id=investigation_id,
                message=f"Enrichment failed for {entity.value}: {enrichment_result.get('error')}",
                entity_id=entity.id
            )
            return
        
        # Normalize results
        raw_results = enrichment_result["results"]
        normalized_entities, evidence_list = self.normalizer.normalize_osint_search_results(
            raw_results,
            entity.value,
            entity.entity_type
        )
        
        yield ExecutionEvent(
            event_type="enrichment_completed",
            investigation_id=investigation_id,
            message=f"Found {len(normalized_entities)} new entities and {len(evidence_list)} evidence items",
            entity_id=entity.id,
            data={
                "new_entities": len(normalized_entities),
                "evidence_count": len(evidence_list)
            }
        )
        
        # Add evidence to graph
        for evidence in evidence_list:
            evidence.linked_entities = [entity.id]
            evidence_id = await self.graph_updater.add_evidence(investigation_id, evidence)
            
            yield ExecutionEvent(
                event_type="evidence_added",
                investigation_id=investigation_id,
                message=f"Added evidence: {evidence.evidence_type}",
                data={"evidence_id": evidence_id, "type": evidence.evidence_type}
            )
        
        # Process discovered entities
        for new_entity in normalized_entities:
            # Add to graph
            new_entity.derived_from = entity.id
            new_entity_id = await self.graph_updater.add_entity_to_graph(investigation_id, new_entity)
            new_entity.id = new_entity_id
            
            state.entities_discovered += 1
            
            yield ExecutionEvent(
                event_type="entity_discovered",
                investigation_id=investigation_id,
                message=f"Discovered {new_entity.entity_type}: {new_entity.value} (confidence={new_entity.confidence:.2f})",
                entity_id=new_entity_id,
                confidence=new_entity.confidence,
                data={
                    "entity_type": new_entity.entity_type,
                    "value": new_entity.value,
                    "derived_from": entity.id
                }
            )
            
            # Create derived_from relationship
            await self.graph_updater.link_derived_entity(
                investigation_id,
                parent_entity_id=entity.id,
                child_entity_id=new_entity_id
            )
            
            yield ExecutionEvent(
                event_type="relationship_created",
                investigation_id=investigation_id,
                message=f"Linked {new_entity.value} to {entity.value}",
                data={"parent": entity.id, "child": new_entity_id}
            )
            
            # Decide if we should pivot
            next_depth = task.depth + 1
            if PivotPlanner.should_pivot(new_entity, next_depth, state.max_depth, state.confidence_threshold):
                pivot_task = PivotPlanner.create_pivot_task(
                    new_entity,
                    depth=next_depth,
                    parent_entity_id=entity.id
                )
                state.queue.append(pivot_task)
                
                yield ExecutionEvent(
                    event_type="pivot_selected",
                    investigation_id=investigation_id,
                    message=f"Queued pivot: {new_entity.entity_type}:{new_entity.value} (depth={next_depth}, priority={pivot_task.priority:.2f})",
                    entity_id=new_entity_id,
                    data={"depth": next_depth, "priority": pivot_task.priority}
                )
            else:
                logger.debug(f"Skipping pivot on {new_entity.value}: confidence or depth limit")
    
    async def pause_investigation(self, investigation_id: str):
        """Pause an active investigation."""
        if investigation_id in self.investigations:
            self.investigations[investigation_id].status = "paused"
    
    async def resume_investigation(self, investigation_id: str) -> AsyncGenerator[ExecutionEvent, None]:
        """Resume a paused investigation."""
        if investigation_id in self.investigations:
            state = self.investigations[investigation_id]
            if state.status == "paused":
                state.status = "running"
                async for event in self._process_investigation_queue(investigation_id):
                    yield event
    
    def get_investigation_status(self, investigation_id: str) -> Optional[InvestigationState]:
        """Get current state of an investigation."""
        return self.investigations.get(investigation_id)

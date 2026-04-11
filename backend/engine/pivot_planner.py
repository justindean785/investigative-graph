"""
Pivot planning logic — decides which entities to investigate next and how.
"""

import logging
from typing import List, Dict, Optional

from .models import NormalizedEntity, PivotTask

logger = logging.getLogger(__name__)


class PivotPlanner:
    """Determines pivot strategy for each entity type."""
    
    # Define which provider commands to use for each entity type
    PIVOT_STRATEGIES = {
        "email": [
            ("ghosint", ["leakcheck", "snusbase"]),
            ("swatted", ["leakosint", "snusbase", "breachint", "stealerlogs"]),
            ("bosint", ["email", "darkweb"]),
        ],
        "phone": [
            ("ghosint", ["leakcheck", "snusbase"]),
            ("swatted", ["leakosint", "snusbase"]),
            ("bosint", ["phone"]),
        ],
        "username": [
            ("swatted", ["tiktok", "instagram", "leakosint"]),
            ("bosint", ["username", "darkweb"]),
        ],
        "domain": [
            ("swatted", ["shodan_dns", "infodra"]),
            ("bosint", ["domain"]),
        ],
        "ip": [
            ("ghosint", ["snusbase"]),
            ("swatted", ["shodan", "stealerlogs_ip"]),
            ("bosint", ["ip"]),
        ],
        "wallet": [
            ("swatted", ["crypto"]),
            ("bosint", ["darkweb"]),
        ],
        "name": [
            ("bosint", ["darkweb"]),
        ],
        "address": [
            ("bosint", ["darkweb"]),
        ],
    }
    
    @staticmethod
    def should_pivot(entity: NormalizedEntity, current_depth: int, max_depth: int, confidence_threshold: float) -> bool:
        """Decide if we should pivot from this entity."""
        # Don't pivot if confidence too low
        if entity.confidence < confidence_threshold:
            logger.debug(f"Skipping pivot on {entity.value}: confidence {entity.confidence} < {confidence_threshold}")
            return False
        
        # Don't pivot if already at max depth
        if current_depth >= max_depth:
            logger.debug(f"Skipping pivot on {entity.value}: depth {current_depth} >= {max_depth}")
            return False
        
        # Don't pivot on low-value entity types at deep levels
        if current_depth > 2 and entity.entity_type in ["name", "address"]:
            logger.debug(f"Skipping low-value type {entity.entity_type} at depth {current_depth}")
            return False
        
        return True
    
    @staticmethod
    def calculate_priority(entity: NormalizedEntity, depth: int) -> float:
        """Calculate priority score for entity (higher = process sooner)."""
        # Base priority on confidence and depth (shallower = higher priority)
        priority = entity.confidence * (1.0 / (depth + 1))
        
        # Boost high-value entity types
        type_boost = {
            "email": 1.5,
            "phone": 1.4,
            "username": 1.3,
            "wallet": 1.3,
            "ip": 1.2,
            "domain": 1.2,
            "name": 0.8,
            "address": 0.7,
        }
        priority *= type_boost.get(entity.entity_type, 1.0)
        
        # Boost entities with multiple sources (more corroboration)
        if len(entity.sources) > 1:
            priority *= 1.2
        
        # Boost high-risk entities
        if entity.risk_score > 0.6:
            priority *= 1.3
        
        return min(priority, 1.0)  # Cap at 1.0
    
    @staticmethod
    def create_pivot_task(
        entity: NormalizedEntity,
        depth: int,
        parent_entity_id: Optional[str] = None
    ) -> PivotTask:
        """Create a pivot task for an entity."""
        priority = PivotPlanner.calculate_priority(entity, depth)
        
        return PivotTask(
            entity_id=entity.id,
            entity_type=entity.entity_type,
            entity_value=entity.value,
            priority=priority,
            depth=depth,
            parent_entity_id=parent_entity_id
        )
    
    @staticmethod
    def get_providers_for_entity(entity_type: str) -> List[tuple[str, List[str]]]:
        """Get list of (provider, [services]) to query for an entity type."""
        return PivotPlanner.PIVOT_STRATEGIES.get(entity_type, [])

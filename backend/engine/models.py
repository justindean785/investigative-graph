"""
Normalized data models for autonomous investigation engine.
"""

from typing import List, Dict, Any, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field


class NormalizedSource(BaseModel):
    """Normalized source from any provider (GHOSINT/Swatted/BOSINT)."""
    provider: str  # "ghosint", "swatted", "bosint"
    service: str  # "leakcheck", "snusbase", "email", etc.
    found_at: datetime = Field(default_factory=datetime.utcnow)
    confidence: float = 0.5  # Provider-specific confidence if available
    raw_data: Dict[str, Any] = {}  # Original response data


class NormalizedEntity(BaseModel):
    """Unified entity model extracted from any source."""
    id: Optional[str] = None  # Assigned after DB insert
    entity_type: Literal["email", "phone", "username", "domain", "ip", "wallet", "name", "address"]
    value: str
    label: Optional[str] = None  # Display name
    confidence: float = 0.5  # Aggregated confidence from sources
    risk_score: float = 0.0  # 0.0 to 1.0
    sources: List[NormalizedSource] = []
    derived_from: Optional[str] = None  # Parent entity ID if extracted from another entity
    metadata: Dict[str, Any] = {}  # Type-specific data (e.g., phone carrier, email breach count)
    tags: List[str] = []


class NormalizedEvidence(BaseModel):
    """Evidence extracted from provider results."""
    id: Optional[str] = None
    evidence_type: str  # "breach", "social_profile", "public_record", "infrastructure", etc.
    content: str
    source_url: Optional[str] = None
    sources: List[NormalizedSource] = []
    linked_entities: List[str] = []  # Entity IDs
    verification_status: Literal["unverified", "verified", "disputed"] = "unverified"
    collected_at: datetime = Field(default_factory=datetime.utcnow)
    tags: List[str] = []
    metadata: Dict[str, Any] = {}


class PivotTask(BaseModel):
    """A queued pivot task for investigation."""
    entity_id: str
    entity_type: str
    entity_value: str
    priority: float = 0.5  # Higher = process sooner
    depth: int = 0  # How many hops from seed
    parent_entity_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class InvestigationState(BaseModel):
    """Current state of autonomous investigation."""
    investigation_id: str
    status: Literal["idle", "running", "paused", "completed", "error"] = "idle"
    queue: List[PivotTask] = []
    visited_entities: Dict[str, bool] = {}  # entity_value -> True
    processed_count: int = 0
    entities_discovered: int = 0
    current_depth: int = 0
    max_depth: int = 5
    max_entities: int = 100
    confidence_threshold: float = 0.3
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class ExecutionEvent(BaseModel):
    """Event emitted during investigation for live streaming."""
    event_type: Literal[
        "investigation_started",
        "entity_discovered",
        "enrichment_started",
        "enrichment_completed",
        "provider_queried",
        "pivot_selected",
        "confidence_updated",
        "evidence_added",
        "relationship_created",
        "investigation_paused",
        "investigation_completed",
        "error"
    ]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    investigation_id: str
    message: str
    data: Dict[str, Any] = {}
    entity_id: Optional[str] = None
    confidence: Optional[float] = None

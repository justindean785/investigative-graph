"""
models.py — All Pydantic request/response models and shared constants.

Extracted verbatim from server.py; no business logic lives here.
Every model is importable by any router without circular dependencies.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# Shared validation constants
# ---------------------------------------------------------------------------

VALID_ENTITY_TYPES: set = {
    "person",
    "username",
    "email",
    "phone",
    "domain",
    "ip",
    "company",
    "location",
    "wallet",
    "social",
    "hash",
    "url",
}

VALID_VERIFICATION_STATUSES: set = {"verified", "unverified", "disputed"}

# ---------------------------------------------------------------------------
# Investigation models
# ---------------------------------------------------------------------------


class Investigation(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    case_id: str = Field(default_factory=lambda: f"CASE-{uuid.uuid4().hex[:8].upper()}")
    name: str
    description: str = ""
    notes: str = ""
    tags: List[str] = []
    status: str = "active"  # active, archived
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class InvestigationCreate(BaseModel):
    name: str
    description: str = ""
    tags: List[str] = []


class InvestigationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    status: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v is not None and v not in ("active", "archived"):
            raise ValueError("status must be 'active' or 'archived'")
        return v


# ---------------------------------------------------------------------------
# Entity models
# ---------------------------------------------------------------------------


class Entity(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    investigation_id: str
    entity_type: str
    value: str
    label: Optional[str] = None
    metadata: Dict[str, Any] = {}
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    risk_score: float = Field(default=0.0, ge=0.0, le=1.0)
    sources: List[str] = []
    notes: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EntityCreate(BaseModel):
    entity_type: str
    value: str
    label: Optional[str] = None
    metadata: Dict[str, Any] = {}
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    risk_score: float = Field(default=0.0, ge=0.0, le=1.0)
    sources: List[str] = []
    notes: str = ""

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, v):
        if v not in VALID_ENTITY_TYPES:
            raise ValueError(
                f"entity_type must be one of: {', '.join(sorted(VALID_ENTITY_TYPES))}"
            )
        return v


class EntityUpdate(BaseModel):
    """Partial update model for entities — all fields optional."""

    value: Optional[str] = None
    label: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    confidence: Optional[float] = None
    risk_score: Optional[float] = None
    sources: Optional[List[str]] = None
    notes: Optional[str] = None


class EntityMergeRequest(BaseModel):
    """Request to merge two entity records into one, keeping the primary entity."""

    primary_entity_id: str  # Entity to keep
    duplicate_entity_id: str  # Entity to remove; relationships re-parented to primary


# ---------------------------------------------------------------------------
# Relationship models
# ---------------------------------------------------------------------------


class Relationship(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    investigation_id: str
    source_entity_id: str
    target_entity_id: str
    relationship_type: (
        str  # owns, registered, resolves_to, used_on, interacts_with, linked_to
    )
    label: str = ""
    metadata: Dict[str, Any] = {}
    confidence: float = 0.5
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RelationshipCreate(BaseModel):
    source_entity_id: str
    target_entity_id: str
    relationship_type: str
    label: str = ""
    metadata: Dict[str, Any] = {}
    confidence: float = 0.5


# ---------------------------------------------------------------------------
# Timeline models
# ---------------------------------------------------------------------------


class TimelineEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    investigation_id: str
    event_type: str  # entity_added, evidence_added, relationship_discovered, enrichment_run, ai_suggestion
    entity_id: Optional[str] = None
    description: str
    metadata: Dict[str, Any] = {}
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Evidence models
# ---------------------------------------------------------------------------


class Evidence(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    investigation_id: str
    entity_id: Optional[str] = None
    evidence_type: str  # screenshot, document, social_post, web_archive, metadata
    source_url: str = ""
    content: str = ""
    notes: str = ""
    tags: List[str] = []  # Analyst-defined tags for annotation and filtering
    verification_status: str = "unverified"  # verified, unverified, disputed
    collected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EvidenceCreate(BaseModel):
    entity_id: Optional[str] = None
    evidence_type: str
    source_url: str = ""
    content: str = ""
    notes: str = ""
    tags: List[str] = []
    verification_status: str = "unverified"

    @field_validator("verification_status")
    @classmethod
    def validate_verification_status(cls, v):
        if v not in VALID_VERIFICATION_STATUSES:
            raise ValueError(
                f"verification_status must be one of: {', '.join(sorted(VALID_VERIFICATION_STATUSES))}"
            )
        return v


class EvidenceUpdate(BaseModel):
    """Partial update model for evidence — all fields optional."""

    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    verification_status: Optional[str] = None
    entity_id: Optional[str] = None

    @field_validator("verification_status")
    @classmethod
    def validate_verification_status(cls, v):
        if v is not None and v not in VALID_VERIFICATION_STATUSES:
            raise ValueError(
                f"verification_status must be one of: {', '.join(sorted(VALID_VERIFICATION_STATUSES))}"
            )
        return v


# ---------------------------------------------------------------------------
# AI models
# ---------------------------------------------------------------------------


class AISuggestion(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    investigation_id: str
    suggestion_type: str  # connection, lead, pattern, enrichment
    title: str
    description: str
    action_data: Dict[str, Any] = {}  # Data needed to execute the suggestion
    status: str = "pending"  # pending, accepted, dismissed
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AIAnalysisRequest(BaseModel):
    investigation_id: str
    mode: str = "flash"  # flash or pro
    context: Optional[str] = None


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    investigation_id: str
    session_id: str
    role: str  # user, assistant
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class GrokEnrichRequest(BaseModel):
    entity_type: str
    value: str
    investigation_id: str
    context: Optional[str] = None


# ---------------------------------------------------------------------------
# OSINT / enrichment models
# ---------------------------------------------------------------------------


class OSINTSearchRequest(BaseModel):
    query: str
    search_type: str  # email, username, domain, ip, phone, wallet


class EntityExtractionRequest(BaseModel):
    text: str
    source_evidence_id: Optional[str] = None


class EnrichmentRequest(BaseModel):
    entity_id: str
    entity_type: str
    entity_value: str


# ---------------------------------------------------------------------------
# Graph models
# ---------------------------------------------------------------------------


class GraphAnalysisRequest(BaseModel):
    investigation_id: str
    analysis_type: str = "full"  # full, clusters, centrality, paths


# ---------------------------------------------------------------------------
# Investigation lead models
# ---------------------------------------------------------------------------


class InvestigationLead(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    investigation_id: str
    lead_type: str  # alias_cluster, shared_infrastructure, wallet_cluster, username_reuse, timing_anomaly, high_risk_connection
    title: str
    description: str
    confidence: float = 0.5  # 0-1
    severity: str = "medium"  # low, medium, high, critical
    affected_entities: List[str] = []
    evidence_ids: List[str] = []
    suggested_actions: List[Dict[str, Any]] = []
    status: str = "new"  # new, investigating, confirmed, dismissed
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Ingest models
# ---------------------------------------------------------------------------


class URLIngestRequest(BaseModel):
    url: str
    evidence_type: str = "webpage"
    notes: str = ""


class RawTextIngestRequest(BaseModel):
    content: str
    title: str = ""
    evidence_type: str = "raw_text"
    notes: str = ""


# ---------------------------------------------------------------------------
# Autonomous investigation models
# ---------------------------------------------------------------------------


class AutoInvestigateRequest(BaseModel):
    seed_input: str = Field(
        ..., description="Raw input text to start investigation from"
    )
    max_depth: int = Field(default=5, ge=1, le=10)
    max_entities: int = Field(default=100, ge=10, le=500)
    confidence_threshold: float = Field(default=0.3, ge=0.0, le=1.0)

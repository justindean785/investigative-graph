from fastapi import FastAPI, APIRouter, HTTPException, Header
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
from emergentintegrations.llm.chat import LlmChat, UserMessage
import json

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

API_KEY = os.environ.get('API_KEY', 'trace-analyst-secret-2026')
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============= API KEY VALIDATION =============
async def validate_api_key(x_api_key: Optional[str] = Header(None)):
    if not x_api_key or x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return True

# ============= MODELS =============

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

class Entity(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    investigation_id: str
    entity_type: str  # person, username, email, phone, domain, ip, company, location, wallet, social, hash, url
    value: str
    label: Optional[str] = None
    metadata: Dict[str, Any] = {}
    confidence: float = 0.5  # 0-1
    risk_score: float = 0.0  # 0-1
    sources: List[str] = []
    notes: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class EntityCreate(BaseModel):
    entity_type: str
    value: str
    label: Optional[str] = None
    metadata: Dict[str, Any] = {}
    confidence: float = 0.5
    risk_score: float = 0.0
    sources: List[str] = []
    notes: str = ""

class Relationship(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    investigation_id: str
    source_entity_id: str
    target_entity_id: str
    relationship_type: str  # owns, registered, resolves_to, used_on, interacts_with, linked_to
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

class TimelineEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    investigation_id: str
    event_type: str  # entity_added, evidence_added, relationship_discovered, enrichment_run, ai_suggestion
    entity_id: Optional[str] = None
    description: str
    metadata: Dict[str, Any] = {}
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Evidence(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    investigation_id: str
    entity_id: Optional[str] = None
    evidence_type: str  # screenshot, document, social_post, web_archive, metadata
    source_url: str = ""
    content: str = ""
    notes: str = ""
    verification_status: str = "unverified"  # verified, unverified, disputed
    collected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class EvidenceCreate(BaseModel):
    entity_id: Optional[str] = None
    evidence_type: str
    source_url: str = ""
    content: str = ""
    notes: str = ""
    verification_status: str = "unverified"

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

class OSINTSearchRequest(BaseModel):
    query: str
    search_type: str  # email, username, domain, ip, phone, wallet

# ============= MOCK OSINT DATA =============
MOCK_OSINT_DATA = {
    "email": [
        {"source": "breach_db", "data": "Found in 3 data breaches", "risk": 0.7},
        {"source": "domain_whois", "data": "Registered 5 domains", "risk": 0.4}
    ],
    "username": [
        {"source": "social_media", "data": "Active on Twitter, GitHub, Reddit", "risk": 0.2},
        {"source": "forum_posts", "data": "12 posts on security forums", "risk": 0.3}
    ],
    "domain": [
        {"source": "whois", "data": "Registered 2 years ago, Privacy protected", "risk": 0.5},
        {"source": "dns", "data": "Resolves to 185.199.108.153", "risk": 0.3}
    ],
    "ip": [
        {"source": "geolocation", "data": "Located in US-East, AWS infrastructure", "risk": 0.2},
        {"source": "reputation", "data": "Clean reputation, no malicious activity", "risk": 0.1}
    ],
    "phone": [
        {"source": "carrier_lookup", "data": "T-Mobile USA, Active", "risk": 0.3},
        {"source": "breach_db", "data": "Found in 1 data breach", "risk": 0.6}
    ],
    "wallet": [
        {"source": "blockchain", "data": "42 transactions, $12.5K total volume", "risk": 0.4},
        {"source": "mixer_check", "data": "No mixer usage detected", "risk": 0.2}
    ]
}

# ============= HELPER FUNCTIONS =============

async def create_timeline_event(investigation_id: str, event_type: str, description: str, entity_id: Optional[str] = None, metadata: Dict = {}):
    event = TimelineEvent(
        investigation_id=investigation_id,
        event_type=event_type,
        description=description,
        entity_id=entity_id,
        metadata=metadata
    )
    doc = event.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    await db.timeline_events.insert_one(doc)
    return event

def serialize_datetime(obj):
    if isinstance(obj, dict):
        return {k: serialize_datetime(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize_datetime(item) for item in obj]
    elif isinstance(obj, datetime):
        return obj.isoformat()
    return obj

# ============= ROUTES =============

@api_router.get("/")
async def root():
    return {"message": "Trace Analyst API v1.0", "status": "operational"}

@api_router.post("/auth/validate")
async def validate_key(x_api_key: str = Header(None)):
    if x_api_key == API_KEY:
        return {"valid": True, "message": "API key is valid"}
    return {"valid": False, "message": "Invalid API key"}

# ============= INVESTIGATIONS =============

@api_router.post("/investigations", response_model=Investigation)
async def create_investigation(input: InvestigationCreate, x_api_key: str = Header(None)):
    await validate_api_key(x_api_key)
    
    investigation = Investigation(
        name=input.name,
        description=input.description,
        tags=input.tags
    )
    
    doc = serialize_datetime(investigation.model_dump())
    await db.investigations.insert_one(doc)
    
    await create_timeline_event(
        investigation.id,
        "investigation_created",
        f"Investigation '{investigation.name}' created"
    )
    
    return investigation

@api_router.get("/investigations", response_model=List[Investigation])
async def get_investigations(x_api_key: str = Header(None)):
    await validate_api_key(x_api_key)
    
    investigations = await db.investigations.find({}, {"_id": 0}).to_list(1000)
    for inv in investigations:
        if isinstance(inv.get('created_at'), str):
            inv['created_at'] = datetime.fromisoformat(inv['created_at'])
        if isinstance(inv.get('updated_at'), str):
            inv['updated_at'] = datetime.fromisoformat(inv['updated_at'])
    
    return investigations

@api_router.get("/investigations/{investigation_id}", response_model=Investigation)
async def get_investigation(investigation_id: str, x_api_key: str = Header(None)):
    await validate_api_key(x_api_key)
    
    investigation = await db.investigations.find_one({"id": investigation_id}, {"_id": 0})
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")
    
    if isinstance(investigation.get('created_at'), str):
        investigation['created_at'] = datetime.fromisoformat(investigation['created_at'])
    if isinstance(investigation.get('updated_at'), str):
        investigation['updated_at'] = datetime.fromisoformat(investigation['updated_at'])
    
    return investigation

@api_router.patch("/investigations/{investigation_id}", response_model=Investigation)
async def update_investigation(investigation_id: str, input: InvestigationUpdate, x_api_key: str = Header(None)):
    await validate_api_key(x_api_key)
    
    investigation = await db.investigations.find_one({"id": investigation_id}, {"_id": 0})
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")
    
    update_data = input.model_dump(exclude_unset=True)
    update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    await db.investigations.update_one(
        {"id": investigation_id},
        {"$set": update_data}
    )
    
    updated_inv = await db.investigations.find_one({"id": investigation_id}, {"_id": 0})
    if isinstance(updated_inv.get('created_at'), str):
        updated_inv['created_at'] = datetime.fromisoformat(updated_inv['created_at'])
    if isinstance(updated_inv.get('updated_at'), str):
        updated_inv['updated_at'] = datetime.fromisoformat(updated_inv['updated_at'])
    
    return updated_inv

@api_router.delete("/investigations/{investigation_id}")
async def delete_investigation(investigation_id: str, x_api_key: str = Header(None)):
    await validate_api_key(x_api_key)
    
    result = await db.investigations.delete_one({"id": investigation_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Investigation not found")
    
    # Clean up related data
    await db.entities.delete_many({"investigation_id": investigation_id})
    await db.relationships.delete_many({"investigation_id": investigation_id})
    await db.timeline_events.delete_many({"investigation_id": investigation_id})
    await db.evidence.delete_many({"investigation_id": investigation_id})
    await db.ai_suggestions.delete_many({"investigation_id": investigation_id})
    
    return {"success": True, "message": "Investigation and all related data deleted"}

# ============= ENTITIES =============

@api_router.post("/investigations/{investigation_id}/entities", response_model=Entity)
async def create_entity(investigation_id: str, input: EntityCreate, x_api_key: str = Header(None)):
    await validate_api_key(x_api_key)
    
    entity = Entity(
        investigation_id=investigation_id,
        **input.model_dump()
    )
    
    doc = serialize_datetime(entity.model_dump())
    await db.entities.insert_one(doc)
    
    await create_timeline_event(
        investigation_id,
        "entity_added",
        f"Added {entity.entity_type}: {entity.value}",
        entity_id=entity.id
    )
    
    return entity

@api_router.get("/investigations/{investigation_id}/entities", response_model=List[Entity])
async def get_entities(investigation_id: str, x_api_key: str = Header(None)):
    await validate_api_key(x_api_key)
    
    entities = await db.entities.find({"investigation_id": investigation_id}, {"_id": 0}).to_list(1000)
    for ent in entities:
        if isinstance(ent.get('created_at'), str):
            ent['created_at'] = datetime.fromisoformat(ent['created_at'])
    
    return entities

@api_router.delete("/investigations/{investigation_id}/entities/{entity_id}")
async def delete_entity(investigation_id: str, entity_id: str, x_api_key: str = Header(None)):
    await validate_api_key(x_api_key)
    
    result = await db.entities.delete_one({"id": entity_id, "investigation_id": investigation_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    # Delete related relationships
    await db.relationships.delete_many({
        "investigation_id": investigation_id,
        "$or": [{"source_entity_id": entity_id}, {"target_entity_id": entity_id}]
    })
    
    await create_timeline_event(
        investigation_id,
        "entity_removed",
        f"Removed entity",
        entity_id=entity_id
    )
    
    return {"success": True}

# ============= RELATIONSHIPS =============

@api_router.post("/investigations/{investigation_id}/relationships", response_model=Relationship)
async def create_relationship(investigation_id: str, input: RelationshipCreate, x_api_key: str = Header(None)):
    await validate_api_key(x_api_key)
    
    relationship = Relationship(
        investigation_id=investigation_id,
        **input.model_dump()
    )
    
    doc = serialize_datetime(relationship.model_dump())
    await db.relationships.insert_one(doc)
    
    await create_timeline_event(
        investigation_id,
        "relationship_discovered",
        f"Connection discovered: {relationship.relationship_type}"
    )
    
    return relationship

@api_router.get("/investigations/{investigation_id}/relationships", response_model=List[Relationship])
async def get_relationships(investigation_id: str, x_api_key: str = Header(None)):
    await validate_api_key(x_api_key)
    
    relationships = await db.relationships.find({"investigation_id": investigation_id}, {"_id": 0}).to_list(1000)
    for rel in relationships:
        if isinstance(rel.get('created_at'), str):
            rel['created_at'] = datetime.fromisoformat(rel['created_at'])
    
    return relationships

@api_router.delete("/investigations/{investigation_id}/relationships/{relationship_id}")
async def delete_relationship(investigation_id: str, relationship_id: str, x_api_key: str = Header(None)):
    await validate_api_key(x_api_key)
    
    result = await db.relationships.delete_one({"id": relationship_id, "investigation_id": investigation_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Relationship not found")
    
    return {"success": True}

# ============= TIMELINE =============

@api_router.get("/investigations/{investigation_id}/timeline", response_model=List[TimelineEvent])
async def get_timeline(investigation_id: str, x_api_key: str = Header(None)):
    await validate_api_key(x_api_key)
    
    events = await db.timeline_events.find(
        {"investigation_id": investigation_id},
        {"_id": 0}
    ).sort("timestamp", -1).to_list(1000)
    
    for event in events:
        if isinstance(event.get('timestamp'), str):
            event['timestamp'] = datetime.fromisoformat(event['timestamp'])
    
    return events

# ============= EVIDENCE =============

@api_router.post("/investigations/{investigation_id}/evidence", response_model=Evidence)
async def create_evidence(investigation_id: str, input: EvidenceCreate, x_api_key: str = Header(None)):
    await validate_api_key(x_api_key)
    
    evidence = Evidence(
        investigation_id=investigation_id,
        **input.model_dump()
    )
    
    doc = serialize_datetime(evidence.model_dump())
    await db.evidence.insert_one(doc)
    
    await create_timeline_event(
        investigation_id,
        "evidence_added",
        f"Added evidence: {evidence.evidence_type}",
        entity_id=evidence.entity_id
    )
    
    return evidence

@api_router.get("/investigations/{investigation_id}/evidence", response_model=List[Evidence])
async def get_evidence(investigation_id: str, x_api_key: str = Header(None)):
    await validate_api_key(x_api_key)
    
    evidence = await db.evidence.find({"investigation_id": investigation_id}, {"_id": 0}).to_list(1000)
    for ev in evidence:
        if isinstance(ev.get('collected_at'), str):
            ev['collected_at'] = datetime.fromisoformat(ev['collected_at'])
    
    return evidence

@api_router.delete("/investigations/{investigation_id}/evidence/{evidence_id}")
async def delete_evidence(investigation_id: str, evidence_id: str, x_api_key: str = Header(None)):
    await validate_api_key(x_api_key)
    
    result = await db.evidence.delete_one({"id": evidence_id, "investigation_id": investigation_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Evidence not found")
    
    return {"success": True}

# ============= AI SUGGESTIONS =============

@api_router.get("/investigations/{investigation_id}/suggestions", response_model=List[AISuggestion])
async def get_suggestions(investigation_id: str, x_api_key: str = Header(None)):
    await validate_api_key(x_api_key)
    
    suggestions = await db.ai_suggestions.find(
        {"investigation_id": investigation_id, "status": "pending"},
        {"_id": 0}
    ).to_list(1000)
    
    for sug in suggestions:
        if isinstance(sug.get('created_at'), str):
            sug['created_at'] = datetime.fromisoformat(sug['created_at'])
    
    return suggestions

@api_router.patch("/investigations/{investigation_id}/suggestions/{suggestion_id}")
async def update_suggestion_status(investigation_id: str, suggestion_id: str, status: str, x_api_key: str = Header(None)):
    await validate_api_key(x_api_key)
    
    await db.ai_suggestions.update_one(
        {"id": suggestion_id, "investigation_id": investigation_id},
        {"$set": {"status": status}}
    )
    
    return {"success": True}

# ============= OSINT SEARCH =============

@api_router.post("/osint/search")
async def osint_search(input: OSINTSearchRequest, x_api_key: str = Header(None)):
    await validate_api_key(x_api_key)
    
    # Mock OSINT results
    results = MOCK_OSINT_DATA.get(input.search_type, [
        {"source": "general", "data": f"Mock data for {input.query}", "risk": 0.3}
    ])
    
    return {
        "query": input.query,
        "search_type": input.search_type,
        "results": results,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# ============= AI ANALYSIS =============

@api_router.post("/ai/analyze")
async def ai_analyze(input: AIAnalysisRequest, x_api_key: str = Header(None)):
    await validate_api_key(x_api_key)
    
    try:
        # Fetch investigation data
        entities = await db.entities.find({"investigation_id": input.investigation_id}, {"_id": 0}).to_list(1000)
        relationships = await db.relationships.find({"investigation_id": input.investigation_id}, {"_id": 0}).to_list(1000)
        
        # Build context for AI
        context = f"""
You are an OSINT investigation assistant analyzing a case.

Entities in investigation: {len(entities)}
"""
        
        if entities:
            context += "\n\nKey entities:\n"
            for ent in entities[:10]:  # Limit to first 10
                context += f"- {ent['entity_type']}: {ent['value']}\n"
        
        if relationships:
            context += f"\n\nRelationships: {len(relationships)} connections discovered\n"
        
        if input.context:
            context += f"\n\nAdditional context: {input.context}\n"
        
        context += """
\nProvide 3-5 investigative suggestions. For each suggestion, provide:
1. A clear title
2. A brief description
3. The suggestion type (one of: connection, lead, pattern, enrichment)
4. Action data (structured data for executing the suggestion)

Format as JSON array with structure:
[
  {
    "title": "...",
    "description": "...",
    "suggestion_type": "...",
    "action_data": {...}
  }
]
"""
        
        # Choose model based on mode
        model = "gemini-3-flash-preview" if input.mode == "flash" else "gemini-3-pro-preview"
        
        # Call Gemini
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"analysis-{input.investigation_id}",
            system_message="You are an expert OSINT investigator providing actionable intelligence suggestions."
        ).with_model("gemini", model)
        
        user_message = UserMessage(text=context)
        response = await chat.send_message(user_message)
        
        # Parse AI response
        try:
            # Extract JSON from response
            response_text = response.strip()
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            suggestions_data = json.loads(response_text)
            
            # Store suggestions in database
            for sug_data in suggestions_data:
                suggestion = AISuggestion(
                    investigation_id=input.investigation_id,
                    suggestion_type=sug_data.get("suggestion_type", "lead"),
                    title=sug_data.get("title", "Suggestion"),
                    description=sug_data.get("description", ""),
                    action_data=sug_data.get("action_data", {})
                )
                doc = serialize_datetime(suggestion.model_dump())
                await db.ai_suggestions.insert_one(doc)
            
            await create_timeline_event(
                input.investigation_id,
                "ai_analysis",
                f"AI analysis completed using {model} - {len(suggestions_data)} suggestions generated"
            )
            
            return {
                "success": True,
                "model_used": model,
                "suggestions_count": len(suggestions_data),
                "suggestions": suggestions_data
            }
        except json.JSONDecodeError:
            # Fallback: create generic suggestion
            suggestion = AISuggestion(
                investigation_id=input.investigation_id,
                suggestion_type="lead",
                title="AI Analysis Result",
                description=response[:500],
                action_data={}
            )
            doc = serialize_datetime(suggestion.model_dump())
            await db.ai_suggestions.insert_one(doc)
            
            return {
                "success": True,
                "model_used": model,
                "suggestions_count": 1,
                "raw_response": response
            }
    
    except Exception as e:
        logger.error(f"AI analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI analysis failed: {str(e)}")

# ============= REPORTS =============

@api_router.get("/investigations/{investigation_id}/report")
async def generate_report(investigation_id: str, x_api_key: str = Header(None)):
    await validate_api_key(x_api_key)
    
    # Fetch all data
    investigation = await db.investigations.find_one({"id": investigation_id}, {"_id": 0})
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")
    
    entities = await db.entities.find({"investigation_id": investigation_id}, {"_id": 0}).to_list(1000)
    relationships = await db.relationships.find({"investigation_id": investigation_id}, {"_id": 0}).to_list(1000)
    evidence = await db.evidence.find({"investigation_id": investigation_id}, {"_id": 0}).to_list(1000)
    timeline = await db.timeline_events.find({"investigation_id": investigation_id}, {"_id": 0}).sort("timestamp", -1).to_list(1000)
    
    return {
        "investigation": investigation,
        "statistics": {
            "total_entities": len(entities),
            "total_relationships": len(relationships),
            "total_evidence": len(evidence),
            "timeline_events": len(timeline)
        },
        "entities": entities,
        "relationships": relationships,
        "evidence": evidence,
        "timeline": timeline[:50]  # Latest 50 events
    }

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

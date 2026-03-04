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

class EntityExtractionRequest(BaseModel):
    text: str
    source_evidence_id: Optional[str] = None

class EnrichmentRequest(BaseModel):
    entity_id: str
    entity_type: str
    entity_value: str

class GraphAnalysisRequest(BaseModel):
    investigation_id: str
    analysis_type: str = "full"  # full, clusters, centrality, paths

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

# ============= ENTITY EXTRACTION PATTERNS =============
import re

ENTITY_PATTERNS = {
    "email": {
        "pattern": r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}',
        "label": "Email Address"
    },
    "domain": {
        "pattern": r'(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+(?:onion|com|net|org|io|co|info|biz|gov|edu|mil|int|xyz|online|site|tech|dev|app|cloud)',
        "label": "Domain"
    },
    "ip": {
        "pattern": r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b',
        "label": "IP Address"
    },
    "wallet_eth": {
        "pattern": r'0x[a-fA-F0-9]{40}',
        "label": "Ethereum Wallet"
    },
    "wallet_btc": {
        "pattern": r'(?:bc1|[13])[a-zA-HJ-NP-Z0-9]{25,39}',
        "label": "Bitcoin Wallet"
    },
    "phone": {
        "pattern": r'(?:\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
        "label": "Phone Number"
    },
    "username": {
        "pattern": r'@[A-Za-z0-9_]{3,30}',
        "label": "Username/Handle"
    },
    "url": {
        "pattern": r'https?://[^\s<>"{}|\\^`\[\]]+',
        "label": "URL"
    }
}

# ============= MOCK ENRICHMENT DATA =============
def generate_mock_enrichment(entity_type: str, entity_value: str) -> Dict[str, Any]:
    """Generate realistic mock enrichment data based on entity type"""
    import hashlib
    import random
    
    # Use hash for deterministic but varied results
    seed = int(hashlib.md5(entity_value.encode()).hexdigest()[:8], 16)
    random.seed(seed)
    
    base_enrichment = {
        "entity_value": entity_value,
        "entity_type": entity_type,
        "enriched_at": datetime.now(timezone.utc).isoformat(),
        "sources_checked": [],
        "intelligence": {},
        "risk_assessment": {}
    }
    
    if entity_type == "email":
        breach_count = random.randint(0, 7)
        base_enrichment["sources_checked"] = ["HaveIBeenPwned", "DeHashed", "IntelX", "Snusbase"]
        base_enrichment["intelligence"] = {
            "breach_exposure": {
                "total_breaches": breach_count,
                "breaches": [
                    {"name": "LinkedIn 2021", "date": "2021-06-22", "exposed_data": ["email", "password_hash"]},
                    {"name": "Collection #1", "date": "2019-01-17", "exposed_data": ["email", "password"]},
                    {"name": "Apollo", "date": "2018-07-23", "exposed_data": ["email", "employer", "title"]}
                ][:breach_count] if breach_count > 0 else []
            },
            "associated_usernames": [f"user_{random.randint(100,999)}", f"admin_{random.randint(10,99)}"] if random.random() > 0.5 else [],
            "associated_domains": [entity_value.split("@")[1]] if "@" in entity_value else [],
            "first_seen": f"20{random.randint(15,23)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
            "last_activity": f"2024-{random.randint(1,12):02d}-{random.randint(1,28):02d}"
        }
        base_enrichment["risk_assessment"] = {
            "score": min(0.9, breach_count * 0.15 + random.uniform(0.1, 0.3)),
            "level": "HIGH" if breach_count > 3 else "MEDIUM" if breach_count > 0 else "LOW",
            "factors": [
                "Multiple breach exposures" if breach_count > 1 else None,
                "Password potentially compromised" if breach_count > 0 else None,
                "Associated with suspicious domains" if random.random() > 0.7 else None
            ]
        }
        base_enrichment["risk_assessment"]["factors"] = [f for f in base_enrichment["risk_assessment"]["factors"] if f]
        
    elif entity_type == "domain":
        is_onion = ".onion" in entity_value
        base_enrichment["sources_checked"] = ["WHOIS", "SecurityTrails", "VirusTotal", "URLScan"]
        base_enrichment["intelligence"] = {
            "whois": {
                "registrar": "Namecheap" if not is_onion else "N/A (Tor Hidden Service)",
                "registration_date": f"20{random.randint(18,23)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
                "expiration_date": f"20{random.randint(25,28)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
                "privacy_protected": random.random() > 0.3,
                "registrant_country": random.choice(["RU", "US", "CN", "DE", "NL", "RO"]) if not is_onion else "Unknown"
            },
            "dns_records": {
                "a_records": [f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"],
                "mx_records": [f"mail.{entity_value}"] if random.random() > 0.5 else [],
                "nameservers": [f"ns1.{entity_value}", f"ns2.{entity_value}"]
            },
            "hosting": {
                "asn": f"AS{random.randint(1000, 65000)}",
                "organization": random.choice(["Cloudflare", "Amazon AWS", "DigitalOcean", "OVH", "M247", "Bulletproof Host"]),
                "country": random.choice(["US", "NL", "RO", "RU", "DE"])
            },
            "threat_intelligence": {
                "malware_detected": random.random() > 0.8,
                "phishing_detected": random.random() > 0.85,
                "category": random.choice(["uncategorized", "technology", "finance", "suspicious", "malware"]) if is_onion else "uncategorized"
            }
        }
        base_enrichment["risk_assessment"] = {
            "score": 0.85 if is_onion else random.uniform(0.2, 0.6),
            "level": "HIGH" if is_onion else random.choice(["LOW", "MEDIUM"]),
            "factors": [
                "Tor hidden service (.onion)" if is_onion else None,
                "Privacy-protected WHOIS" if base_enrichment["intelligence"]["whois"]["privacy_protected"] else None,
                "Hosted on bulletproof infrastructure" if "Bulletproof" in base_enrichment["intelligence"]["hosting"]["organization"] else None
            ]
        }
        base_enrichment["risk_assessment"]["factors"] = [f for f in base_enrichment["risk_assessment"]["factors"] if f]
        
    elif entity_type == "wallet":
        is_eth = entity_value.startswith("0x")
        tx_count = random.randint(5, 200)
        base_enrichment["sources_checked"] = ["Etherscan" if is_eth else "Blockchain.com", "Chainalysis", "Crystal"]
        base_enrichment["intelligence"] = {
            "blockchain": "Ethereum" if is_eth else "Bitcoin",
            "balance": {
                "amount": round(random.uniform(0.01, 50), 4),
                "currency": "ETH" if is_eth else "BTC",
                "usd_value": round(random.uniform(100, 150000), 2)
            },
            "transactions": {
                "total_count": tx_count,
                "incoming": random.randint(1, tx_count),
                "outgoing": tx_count - random.randint(1, tx_count // 2),
                "first_transaction": f"20{random.randint(17,22)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
                "last_transaction": f"2024-{random.randint(1,12):02d}-{random.randint(1,28):02d}"
            },
            "exchange_interactions": {
                "binance": random.random() > 0.5,
                "coinbase": random.random() > 0.6,
                "kraken": random.random() > 0.7,
                "unknown_exchange": random.random() > 0.4
            },
            "risk_indicators": {
                "mixer_usage": random.random() > 0.85,
                "darknet_association": random.random() > 0.8,
                "sanctioned_entity": random.random() > 0.95
            }
        }
        risk_score = 0.3
        if base_enrichment["intelligence"]["risk_indicators"]["mixer_usage"]:
            risk_score += 0.3
        if base_enrichment["intelligence"]["risk_indicators"]["darknet_association"]:
            risk_score += 0.25
        if base_enrichment["intelligence"]["risk_indicators"]["sanctioned_entity"]:
            risk_score += 0.35
        base_enrichment["risk_assessment"] = {
            "score": min(0.95, risk_score),
            "level": "HIGH" if risk_score > 0.6 else "MEDIUM" if risk_score > 0.35 else "LOW",
            "factors": [
                "Mixer/tumbler usage detected" if base_enrichment["intelligence"]["risk_indicators"]["mixer_usage"] else None,
                "Darknet marketplace association" if base_enrichment["intelligence"]["risk_indicators"]["darknet_association"] else None,
                "Interaction with sanctioned entity" if base_enrichment["intelligence"]["risk_indicators"]["sanctioned_entity"] else None,
                f"High transaction volume ({tx_count} txs)" if tx_count > 100 else None
            ]
        }
        base_enrichment["risk_assessment"]["factors"] = [f for f in base_enrichment["risk_assessment"]["factors"] if f]
        
    elif entity_type == "ip":
        base_enrichment["sources_checked"] = ["IPInfo", "AbuseIPDB", "Shodan", "VirusTotal"]
        base_enrichment["intelligence"] = {
            "geolocation": {
                "country": random.choice(["US", "RU", "CN", "DE", "NL", "RO", "UA"]),
                "city": random.choice(["New York", "Moscow", "Beijing", "Berlin", "Amsterdam", "Bucharest"]),
                "isp": random.choice(["Amazon AWS", "Google Cloud", "DigitalOcean", "OVH", "Rostelecom", "China Telecom"])
            },
            "hosting": {
                "asn": f"AS{random.randint(1000, 65000)}",
                "is_datacenter": random.random() > 0.3,
                "is_vpn": random.random() > 0.7,
                "is_tor_exit": random.random() > 0.9
            },
            "reputation": {
                "abuse_reports": random.randint(0, 50),
                "malicious_activity": random.random() > 0.7,
                "last_reported": f"2024-{random.randint(1,12):02d}-{random.randint(1,28):02d}" if random.random() > 0.5 else None
            },
            "open_ports": [22, 80, 443] + ([3389] if random.random() > 0.7 else []) + ([8080] if random.random() > 0.6 else [])
        }
        abuse_count = base_enrichment["intelligence"]["reputation"]["abuse_reports"]
        base_enrichment["risk_assessment"] = {
            "score": min(0.9, abuse_count * 0.02 + (0.3 if base_enrichment["intelligence"]["hosting"]["is_tor_exit"] else 0)),
            "level": "HIGH" if abuse_count > 20 else "MEDIUM" if abuse_count > 5 else "LOW",
            "factors": [
                f"{abuse_count} abuse reports" if abuse_count > 0 else None,
                "Tor exit node" if base_enrichment["intelligence"]["hosting"]["is_tor_exit"] else None,
                "VPN/Proxy detected" if base_enrichment["intelligence"]["hosting"]["is_vpn"] else None
            ]
        }
        base_enrichment["risk_assessment"]["factors"] = [f for f in base_enrichment["risk_assessment"]["factors"] if f]
    
    elif entity_type == "person":
        base_enrichment["sources_checked"] = ["Social Media", "Public Records", "News Archives"]
        base_enrichment["intelligence"] = {
            "social_presence": {
                "linkedin": random.random() > 0.4,
                "twitter": random.random() > 0.5,
                "facebook": random.random() > 0.6,
                "github": random.random() > 0.7
            },
            "associated_entities": {
                "emails": [f"{entity_value.lower().replace(' ', '.')}@example.com"] if random.random() > 0.5 else [],
                "organizations": [random.choice(["TechCorp", "FinanceInc", "Unknown LLC"])] if random.random() > 0.6 else []
            }
        }
        base_enrichment["risk_assessment"] = {
            "score": random.uniform(0.1, 0.5),
            "level": "LOW",
            "factors": []
        }
    
    else:
        base_enrichment["intelligence"] = {"note": "Limited enrichment available for this entity type"}
        base_enrichment["risk_assessment"] = {"score": 0.3, "level": "UNKNOWN", "factors": []}
    
    return base_enrichment


def analyze_graph_intelligence(entities: List[Dict], relationships: List[Dict]) -> Dict[str, Any]:
    """Perform graph analysis to detect clusters, central nodes, and suspicious patterns"""
    if not entities:
        return {
            "clusters": [],
            "central_nodes": [],
            "suspicious_patterns": [],
            "shortest_paths": [],
            "summary": "No entities to analyze"
        }
    
    # Build adjacency list
    entity_map = {e["id"]: e for e in entities}
    adjacency = {e["id"]: [] for e in entities}
    
    for rel in relationships:
        source = rel.get("source_entity_id")
        target = rel.get("target_entity_id")
        if source in adjacency and target in adjacency:
            adjacency[source].append(target)
            adjacency[target].append(source)
    
    # Calculate degree centrality
    centrality_scores = {}
    for entity_id, connections in adjacency.items():
        centrality_scores[entity_id] = len(connections)
    
    # Find central nodes (top 3 by connections)
    central_nodes = []
    sorted_by_centrality = sorted(centrality_scores.items(), key=lambda x: x[1], reverse=True)
    for entity_id, degree in sorted_by_centrality[:3]:
        if degree > 0 and entity_id in entity_map:
            entity = entity_map[entity_id]
            central_nodes.append({
                "entity_id": entity_id,
                "label": entity.get("label") or entity.get("value"),
                "type": entity.get("entity_type"),
                "connection_count": degree,
                "importance": "high" if degree >= 3 else "medium"
            })
    
    # Detect clusters using simple connected components
    visited = set()
    clusters = []
    
    def dfs(node, cluster):
        if node in visited:
            return
        visited.add(node)
        cluster.append(node)
        for neighbor in adjacency.get(node, []):
            dfs(neighbor, cluster)
    
    for entity_id in adjacency:
        if entity_id not in visited:
            cluster = []
            dfs(entity_id, cluster)
            if len(cluster) > 1:  # Only report clusters with multiple nodes
                cluster_entities = [entity_map[eid] for eid in cluster if eid in entity_map]
                clusters.append({
                    "id": f"cluster_{len(clusters)+1}",
                    "size": len(cluster),
                    "entity_types": list(set(e.get("entity_type") for e in cluster_entities)),
                    "entities": [
                        {
                            "id": e["id"],
                            "label": e.get("label") or e.get("value"),
                            "type": e.get("entity_type")
                        }
                        for e in cluster_entities
                    ],
                    "cohesion": "tight" if len(cluster) <= 4 else "loose"
                })
    
    # Detect suspicious patterns
    suspicious_patterns = []
    
    # Pattern 1: High-risk entity clusters
    for cluster in clusters:
        high_risk_types = {"wallet", "domain"}
        cluster_types = set(cluster["entity_types"])
        if cluster_types & high_risk_types:
            suspicious_patterns.append({
                "type": "high_risk_cluster",
                "severity": "high",
                "description": f"Cluster contains {', '.join(cluster_types & high_risk_types)} entities that may indicate financial or infrastructure connections",
                "affected_entities": [e["id"] for e in cluster["entities"]]
            })
    
    # Pattern 2: Hub entities (many connections)
    for entity_id, degree in centrality_scores.items():
        if degree >= 3 and entity_id in entity_map:
            entity = entity_map[entity_id]
            if entity.get("entity_type") in ["email", "wallet", "domain"]:
                suspicious_patterns.append({
                    "type": "hub_entity",
                    "severity": "medium",
                    "description": f"Entity '{entity.get('label') or entity.get('value')}' connects multiple entities - potential key actor or infrastructure",
                    "affected_entities": [entity_id] + adjacency[entity_id]
                })
    
    # Find interesting paths (between high-risk entities)
    shortest_paths = []
    high_risk_entities = [e for e in entities if e.get("entity_type") in ["wallet", "person"]]
    if len(high_risk_entities) >= 2:
        # BFS for shortest path
        def find_path(start, end):
            if start == end:
                return [start]
            queue = [[start]]
            visited_paths = {start}
            while queue:
                path = queue.pop(0)
                node = path[-1]
                for neighbor in adjacency.get(node, []):
                    if neighbor == end:
                        return path + [neighbor]
                    if neighbor not in visited_paths:
                        visited_paths.add(neighbor)
                        queue.append(path + [neighbor])
            return None
        
        for i, e1 in enumerate(high_risk_entities[:3]):
            for e2 in high_risk_entities[i+1:3]:
                path = find_path(e1["id"], e2["id"])
                if path and len(path) > 1:
                    path_entities = [entity_map.get(eid) for eid in path if eid in entity_map]
                    shortest_paths.append({
                        "from": e1.get("label") or e1.get("value"),
                        "to": e2.get("label") or e2.get("value"),
                        "length": len(path) - 1,
                        "path": [
                            {"id": e["id"], "label": e.get("label") or e.get("value"), "type": e.get("entity_type")}
                            for e in path_entities if e
                        ]
                    })
    
    return {
        "clusters": clusters,
        "central_nodes": central_nodes,
        "suspicious_patterns": suspicious_patterns,
        "shortest_paths": shortest_paths,
        "summary": f"Found {len(clusters)} cluster(s), {len(central_nodes)} central node(s), {len(suspicious_patterns)} suspicious pattern(s)",
        "graph_stats": {
            "total_entities": len(entities),
            "total_relationships": len(relationships),
            "avg_connections": sum(centrality_scores.values()) / len(entities) if entities else 0
        }
    }


# ============= INVESTIGATION LEAD ENGINE =============

def generate_investigation_leads(entities: List[Dict], relationships: List[Dict], evidence: List[Dict], timeline: List[Dict]) -> List[Dict]:
    """
    Automated hypothesis generation engine that analyzes investigation data
    and produces actionable investigative leads.
    """
    import hashlib
    import random
    from collections import defaultdict
    
    leads = []
    
    if not entities:
        return leads
    
    # Build lookup structures
    entity_map = {e["id"]: e for e in entities}
    entities_by_type = defaultdict(list)
    for e in entities:
        entities_by_type[e.get("entity_type", "unknown")].append(e)
    
    # Build adjacency for relationship analysis
    adjacency = defaultdict(list)
    relationship_map = defaultdict(list)
    for rel in relationships:
        source = rel.get("source_entity_id")
        target = rel.get("target_entity_id")
        if source and target:
            adjacency[source].append(target)
            adjacency[target].append(source)
            relationship_map[source].append(rel)
            relationship_map[target].append(rel)
    
    # ============= PATTERN 1: Shared Domain Cluster =============
    # If multiple emails connect to the same domain
    emails = entities_by_type.get("email", [])
    domains = entities_by_type.get("domain", [])
    
    if emails and domains:
        for domain in domains:
            domain_value = domain.get("value", "")
            connected_emails = []
            
            for email in emails:
                email_value = email.get("value", "")
                # Check if email domain matches
                if "@" in email_value and email_value.split("@")[1].lower() == domain_value.lower():
                    connected_emails.append(email)
                # Check if connected via relationship
                elif email["id"] in adjacency.get(domain["id"], []):
                    connected_emails.append(email)
            
            if len(connected_emails) >= 2:
                leads.append({
                    "id": f"lead_{uuid.uuid4().hex[:12]}",
                    "lead_type": "alias_cluster",
                    "title": "Possible Operator Cluster Detected",
                    "description": f"Multiple email addresses ({len(connected_emails)}) are associated with the domain {domain_value}. This may indicate a single operator using multiple aliases or an organized group.",
                    "confidence": min(0.95, 0.5 + len(connected_emails) * 0.15),
                    "severity": "high" if len(connected_emails) >= 3 else "medium",
                    "affected_entities": [e["id"] for e in connected_emails] + [domain["id"]],
                    "evidence_ids": [],
                    "suggested_actions": [
                        {"type": "investigate", "label": "Cross-reference email registration dates", "action": "enrich_emails"},
                        {"type": "search", "label": "Search for username patterns", "action": "username_search"},
                        {"type": "connect", "label": "Link emails to domain operator", "action": "create_relationship"}
                    ],
                    "metadata": {
                        "pattern": "shared_domain",
                        "domain": domain_value,
                        "email_count": len(connected_emails)
                    }
                })
    
    # ============= PATTERN 2: Wallet Cluster Analysis =============
    # Wallets that interact with the same exchanges or each other
    wallets = entities_by_type.get("wallet", [])
    
    if len(wallets) >= 2:
        # Find wallets connected through common entities
        wallet_connections = defaultdict(set)
        for wallet in wallets:
            for connected_id in adjacency.get(wallet["id"], []):
                connected_entity = entity_map.get(connected_id)
                if connected_entity:
                    wallet_connections[wallet["id"]].add(connected_id)
        
        # Find wallet pairs with shared connections
        wallet_list = list(wallets)
        for i, w1 in enumerate(wallet_list):
            for w2 in wallet_list[i+1:]:
                shared = wallet_connections[w1["id"]] & wallet_connections[w2["id"]]
                if shared:
                    shared_entities = [entity_map[eid] for eid in shared if eid in entity_map]
                    leads.append({
                        "id": f"lead_{uuid.uuid4().hex[:12]}",
                        "lead_type": "wallet_cluster",
                        "title": "Wallet Cluster Detected",
                        "description": f"Wallets '{w1.get('label') or w1.get('value')[:12]}...' and '{w2.get('label') or w2.get('value')[:12]}...' share {len(shared)} common connection(s). This may indicate fund movement coordination or common ownership.",
                        "confidence": min(0.90, 0.6 + len(shared) * 0.1),
                        "severity": "high",
                        "affected_entities": [w1["id"], w2["id"]] + list(shared),
                        "evidence_ids": [],
                        "suggested_actions": [
                            {"type": "investigate", "label": "Trace transaction history", "action": "blockchain_trace"},
                            {"type": "enrich", "label": "Check exchange withdrawals", "action": "exchange_check"},
                            {"type": "connect", "label": "Link wallets as cluster", "action": "create_cluster_relationship"}
                        ],
                        "metadata": {
                            "wallet_1": w1.get("value"),
                            "wallet_2": w2.get("value"),
                            "shared_connections": [e.get("value") for e in shared_entities]
                        }
                    })
    
    # ============= PATTERN 3: Infrastructure Correlation =============
    # Domains sharing hosting or registration patterns
    if len(domains) >= 2:
        # Simulate infrastructure analysis (in real system, would use enrichment data)
        domain_list = list(domains)
        for i, d1 in enumerate(domain_list):
            for d2 in domain_list[i+1:]:
                # Check if domains are connected to same entities
                d1_connections = set(adjacency.get(d1["id"], []))
                d2_connections = set(adjacency.get(d2["id"], []))
                shared_infra = d1_connections & d2_connections
                
                # Check for .onion domains (high risk)
                both_onion = ".onion" in d1.get("value", "") and ".onion" in d2.get("value", "")
                
                if shared_infra or both_onion:
                    leads.append({
                        "id": f"lead_{uuid.uuid4().hex[:12]}",
                        "lead_type": "shared_infrastructure",
                        "title": "Shared Infrastructure Pattern",
                        "description": f"Domains '{d1.get('value')}' and '{d2.get('value')}' appear to share infrastructure or operator connections. {'Both are Tor hidden services.' if both_onion else ''}",
                        "confidence": 0.75 if both_onion else 0.65,
                        "severity": "high" if both_onion else "medium",
                        "affected_entities": [d1["id"], d2["id"]],
                        "evidence_ids": [],
                        "suggested_actions": [
                            {"type": "enrich", "label": "Compare WHOIS/DNS records", "action": "domain_compare"},
                            {"type": "investigate", "label": "Check hosting ASN overlap", "action": "asn_analysis"},
                            {"type": "search", "label": "Search for related domains", "action": "domain_search"}
                        ],
                        "metadata": {
                            "domain_1": d1.get("value"),
                            "domain_2": d2.get("value"),
                            "both_onion": both_onion
                        }
                    })
    
    # ============= PATTERN 4: Username/Alias Reuse =============
    # Same or similar usernames across entities
    usernames = entities_by_type.get("username", [])
    persons = entities_by_type.get("person", [])
    
    # Extract potential usernames from emails
    email_usernames = []
    for email in emails:
        if "@" in email.get("value", ""):
            username_part = email["value"].split("@")[0].lower()
            email_usernames.append({"username": username_part, "source": email})
    
    # Check for reuse patterns
    username_values = [u.get("value", "").lower() for u in usernames]
    for eu in email_usernames:
        if eu["username"] in username_values or any(eu["username"] in uv or uv in eu["username"] for uv in username_values if len(uv) > 3):
            matching_username = next((u for u in usernames if eu["username"] in u.get("value", "").lower()), None)
            if matching_username:
                leads.append({
                    "id": f"lead_{uuid.uuid4().hex[:12]}",
                    "lead_type": "username_reuse",
                    "title": "Username Reuse Pattern Detected",
                    "description": f"The username pattern '{eu['username']}' appears in both email '{eu['source'].get('value')}' and social handle '{matching_username.get('value')}'. This strongly suggests the same individual.",
                    "confidence": 0.85,
                    "severity": "medium",
                    "affected_entities": [eu["source"]["id"], matching_username["id"]],
                    "evidence_ids": [],
                    "suggested_actions": [
                        {"type": "search", "label": "Search username across platforms", "action": "osint_username_search"},
                        {"type": "connect", "label": "Link as alias", "action": "create_alias_relationship"},
                        {"type": "investigate", "label": "Profile social media activity", "action": "social_profile"}
                    ],
                    "metadata": {
                        "username_pattern": eu["username"],
                        "email": eu["source"].get("value"),
                        "social_handle": matching_username.get("value")
                    }
                })
    
    # ============= PATTERN 5: High-Risk Entity Connections =============
    # Person connected to multiple high-risk entities
    for person in persons:
        person_connections = adjacency.get(person["id"], [])
        high_risk_connections = []
        
        for conn_id in person_connections:
            connected = entity_map.get(conn_id)
            if connected and connected.get("entity_type") in ["wallet", "domain"]:
                # Check if it's a suspicious entity
                value = connected.get("value", "")
                if ".onion" in value or connected.get("entity_type") == "wallet":
                    high_risk_connections.append(connected)
        
        if len(high_risk_connections) >= 2:
            leads.append({
                "id": f"lead_{uuid.uuid4().hex[:12]}",
                "lead_type": "high_risk_connection",
                "title": "High-Risk Entity Network",
                "description": f"Individual '{person.get('label') or person.get('value')}' is connected to {len(high_risk_connections)} high-risk entities including wallets and/or dark web domains. This may indicate involvement in suspicious activities.",
                "confidence": min(0.90, 0.55 + len(high_risk_connections) * 0.15),
                "severity": "critical" if len(high_risk_connections) >= 3 else "high",
                "affected_entities": [person["id"]] + [e["id"] for e in high_risk_connections],
                "evidence_ids": [],
                "suggested_actions": [
                    {"type": "investigate", "label": "Deep profile investigation", "action": "profile_deep_dive"},
                    {"type": "enrich", "label": "Check all connected entities", "action": "bulk_enrich"},
                    {"type": "report", "label": "Flag for priority review", "action": "priority_flag"}
                ],
                "metadata": {
                    "person": person.get("value"),
                    "high_risk_count": len(high_risk_connections),
                    "high_risk_types": list(set(e.get("entity_type") for e in high_risk_connections))
                }
            })
    
    # ============= PATTERN 6: Timing Anomaly Detection =============
    # Evidence/entities added in suspicious patterns
    if len(timeline) >= 3:
        # Look for burst activity
        timestamps = []
        for event in timeline:
            ts = event.get("timestamp")
            if isinstance(ts, str):
                try:
                    timestamps.append(datetime.fromisoformat(ts.replace("Z", "+00:00")))
                except:
                    pass
            elif isinstance(ts, datetime):
                timestamps.append(ts)
        
        if len(timestamps) >= 3:
            timestamps.sort()
            # Check for rapid succession (within 5 minutes)
            burst_events = []
            for i in range(1, len(timestamps)):
                diff = (timestamps[i] - timestamps[i-1]).total_seconds()
                if diff < 300:  # 5 minutes
                    burst_events.append(i)
            
            if len(burst_events) >= 3:
                leads.append({
                    "id": f"lead_{uuid.uuid4().hex[:12]}",
                    "lead_type": "timing_anomaly",
                    "title": "Activity Burst Detected",
                    "description": f"Multiple investigation events ({len(burst_events)+1}) occurred in rapid succession. This may indicate automated data dumps, coordinated activity, or a significant event window worth focusing on.",
                    "confidence": 0.70,
                    "severity": "medium",
                    "affected_entities": [],
                    "evidence_ids": [],
                    "suggested_actions": [
                        {"type": "investigate", "label": "Review burst period evidence", "action": "timeline_focus"},
                        {"type": "search", "label": "Search for related external events", "action": "news_search"}
                    ],
                    "metadata": {
                        "burst_count": len(burst_events) + 1,
                        "time_window": "5 minutes"
                    }
                })
    
    # ============= PATTERN 7: Missing Connection Hypothesis =============
    # Suggest connections that might exist based on entity proximity
    unconnected_pairs = []
    entity_list = list(entities)
    for i, e1 in enumerate(entity_list):
        for e2 in entity_list[i+1:]:
            # Skip if already connected
            if e2["id"] in adjacency.get(e1["id"], []):
                continue
            
            # Check if they share a common neighbor
            e1_neighbors = set(adjacency.get(e1["id"], []))
            e2_neighbors = set(adjacency.get(e2["id"], []))
            common_neighbors = e1_neighbors & e2_neighbors
            
            if common_neighbors and len(common_neighbors) >= 1:
                # They're two hops apart - suggest investigation
                common_entities = [entity_map.get(n) for n in common_neighbors if n in entity_map]
                if common_entities:
                    unconnected_pairs.append({
                        "e1": e1,
                        "e2": e2,
                        "via": common_entities[0]
                    })
    
    # Generate leads for most interesting unconnected pairs
    for pair in unconnected_pairs[:2]:  # Limit to top 2
        leads.append({
            "id": f"lead_{uuid.uuid4().hex[:12]}",
            "lead_type": "missing_connection",
            "title": "Potential Hidden Connection",
            "description": f"'{pair['e1'].get('label') or pair['e1'].get('value')}' and '{pair['e2'].get('label') or pair['e2'].get('value')}' are both connected to '{pair['via'].get('label') or pair['via'].get('value')}' but not to each other. Investigate whether a direct relationship exists.",
            "confidence": 0.55,
            "severity": "low",
            "affected_entities": [pair["e1"]["id"], pair["e2"]["id"], pair["via"]["id"]],
            "evidence_ids": [],
            "suggested_actions": [
                {"type": "investigate", "label": "Research direct connection", "action": "connection_research"},
                {"type": "connect", "label": "Create relationship if confirmed", "action": "create_relationship"}
            ],
            "metadata": {
                "entity_1": pair["e1"].get("value"),
                "entity_2": pair["e2"].get("value"),
                "connecting_entity": pair["via"].get("value")
            }
        })
    
    # Sort leads by confidence and severity
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    leads.sort(key=lambda x: (severity_order.get(x["severity"], 4), -x["confidence"]))
    
    # Add default status to all leads
    for lead in leads:
        lead["status"] = "new"
    
    return leads

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

# ============= ENTITY EXTRACTION =============

@api_router.post("/extract/entities")
async def extract_entities_from_text(
    request: EntityExtractionRequest,
    x_api_key: Optional[str] = Header(None)
):
    """Extract potential entities from text content"""
    await validate_api_key(x_api_key)
    
    extracted = []
    text = request.text
    
    for entity_type, config in ENTITY_PATTERNS.items():
        matches = re.findall(config["pattern"], text, re.IGNORECASE)
        unique_matches = list(set(matches))
        
        for match in unique_matches:
            # Clean up match
            clean_value = match.strip()
            if not clean_value:
                continue
                
            # Determine entity type from pattern name
            actual_type = entity_type
            if entity_type.startswith("wallet_"):
                actual_type = "wallet"
            
            extracted.append({
                "type": actual_type,
                "value": clean_value,
                "label": config["label"],
                "confidence": 0.85,  # Pattern match confidence
                "source_evidence_id": request.source_evidence_id
            })
    
    return {
        "success": True,
        "extracted_count": len(extracted),
        "entities": extracted,
        "patterns_checked": list(ENTITY_PATTERNS.keys())
    }

# ============= ENTITY ENRICHMENT =============

@api_router.post("/enrich/entity")
async def enrich_entity(
    request: EnrichmentRequest,
    x_api_key: Optional[str] = Header(None)
):
    """Enrich an entity with intelligence data"""
    await validate_api_key(x_api_key)
    
    enrichment_data = generate_mock_enrichment(
        request.entity_type,
        request.entity_value
    )
    
    return {
        "success": True,
        "entity_id": request.entity_id,
        "enrichment": enrichment_data
    }

@api_router.get("/investigations/{investigation_id}/entities/{entity_id}/enrichment")
async def get_entity_enrichment(
    investigation_id: str,
    entity_id: str,
    x_api_key: Optional[str] = Header(None)
):
    """Get enrichment data for a specific entity"""
    await validate_api_key(x_api_key)
    
    entity = await db.entities.find_one(
        {"id": entity_id, "investigation_id": investigation_id},
        {"_id": 0}
    )
    
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    enrichment_data = generate_mock_enrichment(
        entity["entity_type"],
        entity["value"]
    )
    
    return {
        "success": True,
        "entity": entity,
        "enrichment": enrichment_data
    }

# ============= GRAPH INTELLIGENCE =============

@api_router.post("/investigations/{investigation_id}/graph/analyze")
async def analyze_investigation_graph(
    investigation_id: str,
    x_api_key: Optional[str] = Header(None)
):
    """Perform graph intelligence analysis on investigation data"""
    await validate_api_key(x_api_key)
    
    # Fetch entities and relationships
    entities = await db.entities.find(
        {"investigation_id": investigation_id},
        {"_id": 0}
    ).to_list(1000)
    
    relationships = await db.relationships.find(
        {"investigation_id": investigation_id},
        {"_id": 0}
    ).to_list(1000)
    
    # Perform analysis
    analysis = analyze_graph_intelligence(entities, relationships)
    
    # Create timeline event
    await create_timeline_event(
        investigation_id=investigation_id,
        event_type="graph_analysis",
        description=f"Graph analysis performed: {analysis['summary']}",
        metadata={"clusters_found": len(analysis["clusters"]), "patterns_found": len(analysis["suspicious_patterns"])}
    )
    
    return {
        "success": True,
        "investigation_id": investigation_id,
        "analysis": analysis
    }

@api_router.get("/investigations/{investigation_id}/graph/clusters")
async def get_graph_clusters(
    investigation_id: str,
    x_api_key: Optional[str] = Header(None)
):
    """Get detected clusters in the investigation graph"""
    await validate_api_key(x_api_key)
    
    entities = await db.entities.find(
        {"investigation_id": investigation_id},
        {"_id": 0}
    ).to_list(1000)
    
    relationships = await db.relationships.find(
        {"investigation_id": investigation_id},
        {"_id": 0}
    ).to_list(1000)
    
    analysis = analyze_graph_intelligence(entities, relationships)
    
    return {
        "success": True,
        "clusters": analysis["clusters"],
        "central_nodes": analysis["central_nodes"]
    }

@api_router.get("/investigations/{investigation_id}/graph/suspicious-patterns")
async def get_suspicious_patterns(
    investigation_id: str,
    x_api_key: Optional[str] = Header(None)
):
    """Get detected suspicious patterns in the investigation"""
    await validate_api_key(x_api_key)
    
    entities = await db.entities.find(
        {"investigation_id": investigation_id},
        {"_id": 0}
    ).to_list(1000)
    
    relationships = await db.relationships.find(
        {"investigation_id": investigation_id},
        {"_id": 0}
    ).to_list(1000)
    
    analysis = analyze_graph_intelligence(entities, relationships)
    
    return {
        "success": True,
        "patterns": analysis["suspicious_patterns"],
        "paths": analysis["shortest_paths"]
    }

# ============= INVESTIGATION LEADS =============

@api_router.post("/investigations/{investigation_id}/leads/generate")
async def generate_leads(
    investigation_id: str,
    x_api_key: Optional[str] = Header(None)
):
    """Generate investigation leads using the automated hypothesis engine"""
    await validate_api_key(x_api_key)
    
    # Fetch all investigation data
    entities = await db.entities.find(
        {"investigation_id": investigation_id},
        {"_id": 0}
    ).to_list(1000)
    
    relationships = await db.relationships.find(
        {"investigation_id": investigation_id},
        {"_id": 0}
    ).to_list(1000)
    
    evidence = await db.evidence.find(
        {"investigation_id": investigation_id},
        {"_id": 0}
    ).to_list(1000)
    
    timeline = await db.timeline_events.find(
        {"investigation_id": investigation_id},
        {"_id": 0}
    ).sort("timestamp", -1).to_list(100)
    
    # Generate leads
    leads = generate_investigation_leads(entities, relationships, evidence, timeline)
    
    # Store leads in database
    for lead in leads:
        lead["investigation_id"] = investigation_id
        lead["created_at"] = datetime.now(timezone.utc).isoformat()
        await db.investigation_leads.update_one(
            {"id": lead["id"]},
            {"$set": lead},
            upsert=True
        )
    
    # Create timeline event
    await create_timeline_event(
        investigation_id=investigation_id,
        event_type="leads_generated",
        description=f"Lead engine generated {len(leads)} investigation leads",
        metadata={"lead_count": len(leads), "lead_types": list(set(l["lead_type"] for l in leads))}
    )
    
    return {
        "success": True,
        "leads_generated": len(leads),
        "leads": leads
    }

@api_router.get("/investigations/{investigation_id}/leads")
async def get_investigation_leads(
    investigation_id: str,
    status: Optional[str] = None,
    x_api_key: Optional[str] = Header(None)
):
    """Get all leads for an investigation"""
    await validate_api_key(x_api_key)
    
    query = {"investigation_id": investigation_id}
    if status:
        query["status"] = status
    
    leads = await db.investigation_leads.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    
    return {
        "success": True,
        "total": len(leads),
        "leads": leads
    }

@api_router.patch("/investigations/{investigation_id}/leads/{lead_id}")
async def update_lead_status(
    investigation_id: str,
    lead_id: str,
    status: str,
    x_api_key: Optional[str] = Header(None)
):
    """Update the status of an investigation lead"""
    await validate_api_key(x_api_key)
    
    if status not in ["new", "investigating", "confirmed", "dismissed"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    result = await db.investigation_leads.update_one(
        {"id": lead_id, "investigation_id": investigation_id},
        {"$set": {"status": status, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Create timeline event
    await create_timeline_event(
        investigation_id=investigation_id,
        event_type="lead_status_updated",
        description=f"Lead status updated to: {status}",
        metadata={"lead_id": lead_id, "new_status": status}
    )
    
    return {"success": True, "lead_id": lead_id, "status": status}

@api_router.delete("/investigations/{investigation_id}/leads/{lead_id}")
async def delete_lead(
    investigation_id: str,
    lead_id: str,
    x_api_key: Optional[str] = Header(None)
):
    """Delete an investigation lead"""
    await validate_api_key(x_api_key)
    
    result = await db.investigation_leads.delete_one(
        {"id": lead_id, "investigation_id": investigation_id}
    )
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    return {"success": True}

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

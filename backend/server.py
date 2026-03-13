from fastapi import FastAPI, APIRouter, HTTPException, Header, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any, AsyncGenerator
import uuid
from datetime import datetime, timezone
import asyncio
try:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    EMERGENT_AVAILABLE = True
except Exception:
    EMERGENT_AVAILABLE = False
import json
import re
import collections
import httpx
import base64
from io import BytesIO

try:
    from google import genai as google_genai
    from google.genai import types as genai_types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Optional OCR/PDF imports
try:
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

try:
    from PyPDF2 import PdfReader
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

API_KEY = os.environ.get('API_KEY', 'trace-analyst-secret-2026')
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')

# AI Engine API keys
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
SWATTED_API_KEY = os.environ.get('SWATTED_API_KEY')
SWATTED_API_URL = os.environ.get('SWATTED_API_URL', 'https://swattedw.tf/api/v1')
PERPLEXITY_API_KEY = os.environ.get('PERPLEXITY_API_KEY')
BOSINT_API_KEY = os.environ.get('BOSINT_API_KEY')
BOSINT_BASE_URL = os.environ.get('BOSINT_API_URL', 'https://app.bosint.gg/bosintapi')

# Configure Gemini client
_gemini_client = None
if GENAI_AVAILABLE and GEMINI_API_KEY:
    _gemini_client = google_genai.Client(api_key=GEMINI_API_KEY)

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

# ============= AI CHAT MODELS =============

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

class URLIngestRequest(BaseModel):
    url: str
    evidence_type: str = "webpage"
    notes: str = ""

class RawTextIngestRequest(BaseModel):
    content: str
    title: str = ""
    evidence_type: str = "raw_text"
    notes: str = ""

class AIInvestigateRequest(BaseModel):
    input_text: str
    auto_expand: bool = True
    scan_depth: str = "standard"  # quick, standard, deep

class ScanRequest(BaseModel):
    query: str
    entity_id: Optional[str] = None
    save_results: bool = True

# ============= EXPANDED EVIDENCE CATEGORIES =============

EVIDENCE_CATEGORIES = {
    "web": {
        "label": "Web Evidence",
        "types": [
            {"value": "webpage", "label": "Web Page", "icon": "globe"},
            {"value": "screenshot", "label": "Website Screenshot", "icon": "image"},
            {"value": "url", "label": "URL", "icon": "link"},
            {"value": "forum_post", "label": "Forum Post", "icon": "message-square"},
            {"value": "blog_article", "label": "Blog Article", "icon": "file-text"},
            {"value": "paste_site", "label": "Paste Site Content", "icon": "clipboard"},
        ]
    },
    "social": {
        "label": "Social Media Evidence",
        "types": [
            {"value": "social_profile", "label": "Social Media Profile", "icon": "user"},
            {"value": "social_post", "label": "Social Media Post", "icon": "message-circle"},
            {"value": "social_comment", "label": "Social Media Comment", "icon": "message-square"},
            {"value": "thread", "label": "Thread", "icon": "git-branch"},
            {"value": "video_post", "label": "Video Post", "icon": "video"},
        ]
    },
    "identity": {
        "label": "Identity Evidence",
        "types": [
            {"value": "email_evidence", "label": "Email Address", "icon": "mail"},
            {"value": "username_evidence", "label": "Username", "icon": "at-sign"},
            {"value": "phone_evidence", "label": "Phone Number", "icon": "phone"},
            {"value": "alias", "label": "Alias", "icon": "users"},
            {"value": "real_name", "label": "Real Name", "icon": "user-check"},
        ]
    },
    "crypto": {
        "label": "Crypto / Financial Evidence",
        "types": [
            {"value": "crypto_wallet", "label": "Crypto Wallet", "icon": "wallet"},
            {"value": "blockchain_tx", "label": "Blockchain Transaction", "icon": "activity"},
            {"value": "exchange_account", "label": "Exchange Account", "icon": "database"},
            {"value": "payment_screenshot", "label": "Payment Screenshot", "icon": "credit-card"},
        ]
    },
    "infrastructure": {
        "label": "Infrastructure Evidence",
        "types": [
            {"value": "domain_evidence", "label": "Domain", "icon": "globe"},
            {"value": "subdomain", "label": "Subdomain", "icon": "git-merge"},
            {"value": "ip_evidence", "label": "IP Address", "icon": "server"},
            {"value": "server", "label": "Server", "icon": "hard-drive"},
            {"value": "dns_record", "label": "DNS Record", "icon": "list"},
            {"value": "whois_record", "label": "WHOIS Record", "icon": "file-text"},
        ]
    },
    "files": {
        "label": "Files and Media",
        "types": [
            {"value": "document", "label": "Document", "icon": "file-text"},
            {"value": "screenshot", "label": "Screenshot", "icon": "image"},
            {"value": "photo", "label": "Photo", "icon": "camera"},
            {"value": "video", "label": "Video", "icon": "video"},
            {"value": "audio", "label": "Audio", "icon": "volume-2"},
            {"value": "pdf", "label": "PDF", "icon": "file"},
            {"value": "spreadsheet", "label": "Spreadsheet", "icon": "table"},
        ]
    },
    "communication": {
        "label": "Communication Evidence",
        "types": [
            {"value": "email_message", "label": "Email Message", "icon": "mail"},
            {"value": "chat_log", "label": "Chat Log", "icon": "message-square"},
            {"value": "sms_message", "label": "SMS Message", "icon": "smartphone"},
            {"value": "telegram_chat", "label": "Telegram Chat", "icon": "send"},
            {"value": "discord_message", "label": "Discord Message", "icon": "hash"},
        ]
    },
    "forensics": {
        "label": "Technical Forensics",
        "types": [
            {"value": "metadata_dump", "label": "Metadata Dump", "icon": "code"},
            {"value": "exif_data", "label": "EXIF Data", "icon": "info"},
            {"value": "log_file", "label": "Log File", "icon": "file-code"},
            {"value": "hash_value", "label": "Hash Value", "icon": "hash"},
        ]
    },
    "notes": {
        "label": "Investigator Notes",
        "types": [
            {"value": "analyst_note", "label": "Analyst Note", "icon": "edit"},
            {"value": "observation", "label": "Observation", "icon": "eye"},
            {"value": "hypothesis", "label": "Hypothesis", "icon": "help-circle"},
            {"value": "lead_note", "label": "Lead", "icon": "lightbulb"},
        ]
    }
}

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
# Enhanced patterns for comprehensive indicator detection

ENTITY_PATTERNS = {
    "email": {
        "compiled": re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', re.IGNORECASE),
        "label": "Email Address",
        "entity_type": "email",
        "risk_base": 0.3
    },
    "domain": {
        "compiled": re.compile(r'(?<![/@])(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+(?:onion|com|net|org|io|co|info|biz|gov|edu|mil|int|xyz|online|site|tech|dev|app|cloud|ru|cn|uk|de|fr|jp|br|in|au|nl|se|ch|es|it|pl|cz|ro|hu|bg|ua|kz|by)', re.IGNORECASE),
        "label": "Domain",
        "entity_type": "domain",
        "risk_base": 0.4
    },
    "onion_domain": {
        "compiled": re.compile(r'[a-z2-7]{16,56}\.onion', re.IGNORECASE),
        "label": "Tor Hidden Service",
        "entity_type": "domain",
        "risk_base": 0.8
    },
    "ip_v4": {
        "compiled": re.compile(r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b', re.IGNORECASE),
        "label": "IPv4 Address",
        "entity_type": "ip",
        "risk_base": 0.3
    },
    "ip_v6": {
        "compiled": re.compile(r'(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}|(?:[0-9a-fA-F]{1,4}:){1,7}:|(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}', re.IGNORECASE),
        "label": "IPv6 Address",
        "entity_type": "ip",
        "risk_base": 0.3
    },
    "wallet_eth": {
        "compiled": re.compile(r'0x[a-fA-F0-9]{40}', re.IGNORECASE),
        "label": "Ethereum Wallet",
        "entity_type": "wallet",
        "risk_base": 0.5
    },
    "wallet_btc": {
        "compiled": re.compile(r'(?:bc1|[13])[a-zA-HJ-NP-Z0-9]{25,39}', re.IGNORECASE),
        "label": "Bitcoin Wallet",
        "entity_type": "wallet",
        "risk_base": 0.5
    },
    "wallet_monero": {
        "compiled": re.compile(r'4[0-9AB][1-9A-HJ-NP-Za-km-z]{93}', re.IGNORECASE),
        "label": "Monero Wallet",
        "entity_type": "wallet",
        "risk_base": 0.7
    },
    "phone_intl": {
        "compiled": re.compile(r'\+[1-9]\d{1,14}', re.IGNORECASE),
        "label": "International Phone",
        "entity_type": "phone",
        "risk_base": 0.2
    },
    "phone_us": {
        "compiled": re.compile(r'(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', re.IGNORECASE),
        "label": "US Phone Number",
        "entity_type": "phone",
        "risk_base": 0.2
    },
    "username_twitter": {
        "compiled": re.compile(r'(?:twitter\.com/|@)([A-Za-z0-9_]{1,15})', re.IGNORECASE),
        "label": "Twitter Handle",
        "entity_type": "username",
        "risk_base": 0.1
    },
    "username_telegram": {
        "compiled": re.compile(r'(?:t\.me/|@)([A-Za-z0-9_]{5,32})', re.IGNORECASE),
        "label": "Telegram Handle",
        "entity_type": "username",
        "risk_base": 0.2
    },
    "username_generic": {
        "compiled": re.compile(r'@[A-Za-z0-9_]{3,30}', re.IGNORECASE),
        "label": "Username/Handle",
        "entity_type": "username",
        "risk_base": 0.1
    },
    "url": {
        "compiled": re.compile(r'https?://[^\s<>"\'{}|\\^`\[\]]+', re.IGNORECASE),
        "label": "URL",
        "entity_type": "url",
        "risk_base": 0.2
    },
    "social_profile": {
        "compiled": re.compile(r'(?:facebook\.com|instagram\.com|linkedin\.com|github\.com|reddit\.com)/[A-Za-z0-9._-]+', re.IGNORECASE),
        "label": "Social Profile URL",
        "entity_type": "social",
        "risk_base": 0.1
    },
    "hash_md5": {
        "compiled": re.compile(r'\b[a-fA-F0-9]{32}\b', re.IGNORECASE),
        "label": "MD5 Hash",
        "entity_type": "hash",
        "risk_base": 0.3
    },
    "hash_sha256": {
        "compiled": re.compile(r'\b[a-fA-F0-9]{64}\b', re.IGNORECASE),
        "label": "SHA256 Hash",
        "entity_type": "hash",
        "risk_base": 0.3
    }
}

# ============= CONTENT EXTRACTION FUNCTIONS =============

async def fetch_url_content(url: str) -> Dict[str, Any]:
    """Fetch and parse content from a URL"""
    result = {
        "success": False,
        "content": "",
        "title": "",
        "metadata": {},
        "error": None
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            response.raise_for_status()
            
            content_type = response.headers.get("content-type", "").lower()
            
            if "text/html" in content_type and BS4_AVAILABLE:
                soup = BeautifulSoup(response.text, "lxml")
                
                # Remove script and style elements
                for script in soup(["script", "style", "nav", "footer", "header"]):
                    script.decompose()
                
                # Get title
                title_tag = soup.find("title")
                result["title"] = title_tag.get_text().strip() if title_tag else url
                
                # Get meta description
                meta_desc = soup.find("meta", {"name": "description"})
                if meta_desc:
                    result["metadata"]["description"] = meta_desc.get("content", "")
                
                # Get main content text
                result["content"] = soup.get_text(separator=" ", strip=True)[:50000]  # Limit size
                result["success"] = True
                
            elif "application/json" in content_type:
                result["content"] = response.text
                result["title"] = "JSON Data"
                result["success"] = True
                
            else:
                result["content"] = response.text[:50000]
                result["title"] = url
                result["success"] = True
                
    except Exception as e:
        result["error"] = str(e)
        logger.error(f"Failed to fetch URL {url}: {e}")
    
    return result

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text from a PDF file"""
    if not PDF_AVAILABLE:
        return ""
    
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
        text_content = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_content.append(text)
        return "\n".join(text_content)
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        return ""

def extract_text_from_image(image_bytes: bytes) -> str:
    """Extract text from an image using OCR"""
    if not OCR_AVAILABLE:
        return ""
    
    try:
        image = Image.open(BytesIO(image_bytes))
        text = pytesseract.image_to_string(image)
        return text.strip()
    except Exception as e:
        logger.error(f"OCR extraction failed: {e}")
        return ""

def extract_entities_from_text(text: str, source_evidence_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Extract all entities/indicators from text using regex patterns"""
    extracted = []
    seen_values = set()  # Deduplicate
    
    for pattern_name, config in ENTITY_PATTERNS.items():
        try:
            matches = config["compiled"].findall(text)
            
            for match in matches:
                # Handle tuple matches from groups
                if isinstance(match, tuple):
                    match = match[0] if match else ""
                
                clean_value = match.strip()
                if not clean_value or len(clean_value) < 3:
                    continue
                
                # Skip common false positives
                if clean_value.lower() in ["www", "http", "https", "ftp", "mail"]:
                    continue
                
                # Deduplicate
                dedup_key = f"{config['entity_type']}:{clean_value.lower()}"
                if dedup_key in seen_values:
                    continue
                seen_values.add(dedup_key)
                
                # Calculate risk score
                risk_score = config.get("risk_base", 0.3)
                if ".onion" in clean_value.lower():
                    risk_score = max(risk_score, 0.8)
                if pattern_name.startswith("wallet_"):
                    risk_score = max(risk_score, 0.5)
                
                extracted.append({
                    "type": config["entity_type"],
                    "pattern_match": pattern_name,
                    "value": clean_value,
                    "label": config["label"],
                    "confidence": 0.85,
                    "risk_score": risk_score,
                    "source_evidence_id": source_evidence_id
                })
        except re.error as e:
            logger.error(f"Regex error for pattern {pattern_name}: {e}")
            continue
    
    # Sort by risk score (highest first)
    extracted.sort(key=lambda x: x.get("risk_score", 0), reverse=True)
    
    return extracted

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
    
    # Detect clusters using iterative BFS (avoids stack overflow on large graphs)
    visited = set()
    clusters = []
    
    for entity_id in adjacency:
        if entity_id not in visited:
            cluster = []
            queue = collections.deque([entity_id])
            visited.add(entity_id)
            while queue:
                node = queue.popleft()
                cluster.append(node)
                for neighbor in adjacency.get(node, []):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)
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
        # Pre-build email-by-domain lookup for O(1) access instead of O(emails × domains)
        emails_by_domain = defaultdict(list)
        for email in emails:
            email_value = email.get("value", "")
            if "@" in email_value:
                email_domain = email_value.split("@")[1].lower()
                emails_by_domain[email_domain].append(email)
        
        for domain in domains:
            domain_value = domain.get("value", "")
            # Get emails matching by domain name (O(1) lookup)
            connected_emails = list(emails_by_domain.get(domain_value.lower(), []))
            # Also check emails connected via relationship
            connected_ids = {e["id"] for e in connected_emails}
            for email in emails:
                if email["id"] not in connected_ids and email["id"] in adjacency.get(domain["id"], []):
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

# ============= AI ENGINE FUNCTIONS =============

async def call_gemini_api(prompt: str, system_instruction: str = None, json_mode: bool = False) -> str:
    """Call Gemini 2.0 Flash via google-genai SDK for AI reasoning tasks"""
    if not GENAI_AVAILABLE or not _gemini_client:
        return json.dumps({"error": "Gemini API not configured"}) if json_mode else "Gemini API not configured."
    try:
        contents = prompt
        config = genai_types.GenerateContentConfig(
            temperature=0.3,
            max_output_tokens=4096,
            system_instruction=system_instruction or "You are an expert OSINT investigator and intelligence analyst.",
        )
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: _gemini_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=contents,
                config=config,
            )
        )
        text = response.text.strip() if response.text else ""
        if json_mode:
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
        return text
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return json.dumps({"error": str(e)}) if json_mode else f"AI analysis error: {str(e)}"


async def call_perplexity_search(query: str) -> str:
    """Call Perplexity sonar-pro for real-time web OSINT research"""
    if not OPENAI_AVAILABLE or not PERPLEXITY_API_KEY:
        return "Perplexity not configured."
    try:
        client = AsyncOpenAI(api_key=PERPLEXITY_API_KEY, base_url="https://api.perplexity.ai")
        response = await client.chat.completions.create(
            model="sonar-pro",
            messages=[
                {"role": "system", "content": "You are an OSINT research assistant. Provide factual, sourced information. Be concise and structured."},
                {"role": "user", "content": query}
            ],
            max_tokens=2048,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Perplexity API error: {e}")
        return f"Search unavailable: {str(e)}"


async def bosint_api_call(command: str, query: str) -> Dict[str, Any]:
    """Call BOSINT API for real OSINT data"""
    if not BOSINT_API_KEY:
        return {"error": "BOSINT not configured", "data": None}
    try:
        url = f"{BOSINT_BASE_URL}/{BOSINT_API_KEY}/{command}/{query}"
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://app.bosint.gg/",
                "Origin": "https://app.bosint.gg",
            })
            if response.status_code == 200:
                try:
                    return {"error": None, "data": response.json()}
                except Exception:
                    return {"error": None, "data": {"raw": response.text[:2000]}}
            else:
                logger.warning(f"BOSINT API returned {response.status_code} for {command}/{query}")
                return {"error": f"HTTP {response.status_code}", "data": None}
    except Exception as e:
        logger.error(f"BOSINT API error for {command}/{query}: {e}")
        return {"error": str(e), "data": None}


async def save_entity_to_db(investigation_id: str, entity_type: str, value: str, label: str = None,
                             metadata: Dict = None, confidence: float = 0.8, risk_score: float = 0.3,
                             sources: List[str] = None, notes: str = "") -> Dict:
    """Save an entity to MongoDB, deduplicating by type+value"""
    existing = await db.entities.find_one({
        "investigation_id": investigation_id,
        "entity_type": entity_type,
        "value": value
    }, {"_id": 0})
    if existing:
        return existing

    entity = Entity(
        investigation_id=investigation_id,
        entity_type=entity_type,
        value=value,
        label=label or value,
        metadata=metadata or {},
        confidence=confidence,
        risk_score=risk_score,
        sources=sources or [],
        notes=notes
    )
    doc = serialize_datetime(entity.model_dump())
    await db.entities.insert_one(doc)
    await create_timeline_event(
        investigation_id, "entity_added",
        f"AI discovered {entity_type}: {value}",
        entity_id=entity.id,
        metadata={"source": "ai_investigation", "auto_discovered": True}
    )
    return doc


async def save_relationship_to_db(investigation_id: str, source_id: str, target_id: str,
                                   rel_type: str, label: str = "", confidence: float = 0.75,
                                   metadata: Dict = None) -> Optional[Dict]:
    """Save a relationship to MongoDB, deduplicating"""
    existing = await db.relationships.find_one({
        "investigation_id": investigation_id,
        "source_entity_id": source_id,
        "target_entity_id": target_id,
        "relationship_type": rel_type
    }, {"_id": 0})
    if existing:
        return existing

    rel = Relationship(
        investigation_id=investigation_id,
        source_entity_id=source_id,
        target_entity_id=target_id,
        relationship_type=rel_type,
        label=label,
        metadata=metadata or {},
        confidence=confidence
    )
    doc = serialize_datetime(rel.model_dump())
    await db.relationships.insert_one(doc)
    await create_timeline_event(
        investigation_id, "relationship_discovered",
        f"AI linked: {rel_type}",
        metadata={"auto_discovered": True}
    )
    return doc


async def ai_extract_entities_from_input(input_text: str) -> List[Dict]:
    """Use Gemini to parse and classify entities from raw investigative input"""
    prompt = f"""Analyze this investigative input and extract all identifiers/entities.

Input: {input_text}

Extract every distinct identifier. For each, return:
- entity_type: one of [person, username, email, phone, domain, ip, company, wallet, social, url, hash]
- value: the exact identifier value
- confidence: 0.0-1.0
- label: human-readable label
- notes: brief context about why this was extracted

Return ONLY a JSON array. Example:
[
  {{"entity_type": "username", "value": "shadowhunter77", "confidence": 0.95, "label": "Username: shadowhunter77", "notes": "Primary identifier from input"}},
  {{"entity_type": "email", "value": "john@example.com", "confidence": 0.99, "label": "Email Address", "notes": "Email found in input"}}
]

If only one entity is apparent, return an array with just that one item.
Do not invent entities that are not present. Be precise."""

    try:
        result = await call_gemini_api(prompt, json_mode=True)
        parsed = json.loads(result)
        if isinstance(parsed, list):
            return parsed
        return []
    except Exception as e:
        logger.error(f"Entity extraction error: {e}")
        return extract_entities_from_text(input_text)[:5]


async def ai_infer_relationships(entities: List[Dict]) -> List[Dict]:
    """Use Gemini to infer relationships between a set of entities"""
    if len(entities) < 2:
        return []

    entity_list = "\n".join([f"- ID:{e['id']} TYPE:{e['entity_type']} VALUE:{e['value']}" for e in entities[:30]])
    prompt = f"""Given these entities from an OSINT investigation, infer probable relationships between them.

Entities:
{entity_list}

For each probable relationship, return:
- source_id: entity ID of source
- target_id: entity ID of target
- relationship_type: one of [owns, registered, resolves_to, used_on, interacts_with, linked_to, employed_by, located_at, alias_of]
- label: short description
- confidence: 0.0-1.0
- reasoning: brief explanation

Rules:
- Only infer relationships with confidence > 0.5
- Focus on email→domain (registered), username→social (used_on), domain→ip (resolves_to)
- Return ONLY a JSON array. Return empty array [] if no strong relationships found.

Example:
[
  {{"source_id": "id1", "target_id": "id2", "relationship_type": "registered", "label": "Registered domain", "confidence": 0.85, "reasoning": "Email domain matches"}}
]"""

    try:
        result = await call_gemini_api(prompt, json_mode=True)
        parsed = json.loads(result)
        return parsed if isinstance(parsed, list) else []
    except Exception as e:
        logger.error(f"Relationship inference error: {e}")
        return []


async def process_bosint_username_results(investigation_id: str, username: str, bosint_data: Dict) -> List[Dict]:
    """Parse BOSINT username results and create platform entities"""
    created_entities = []
    data = bosint_data.get("data") or {}

    # Handle various BOSINT response formats
    accounts = []
    if isinstance(data, dict):
        accounts = data.get("accounts", data.get("results", data.get("platforms", [])))
        if isinstance(accounts, dict):
            accounts = [{"platform": k, **v} for k, v in accounts.items()]
    elif isinstance(data, list):
        accounts = data

    for account in accounts[:50]:
        if not isinstance(account, dict):
            continue
        platform = account.get("platform", account.get("site", account.get("name", "unknown")))
        url = account.get("url", account.get("profile_url", account.get("link", "")))
        found = account.get("found", account.get("exists", account.get("status", "unknown")))

        if str(found).lower() in ["false", "0", "not found", "no"]:
            continue

        if url and platform:
            entity = await save_entity_to_db(
                investigation_id, "social",
                url or f"{platform}/{username}",
                label=f"{platform}: @{username}",
                metadata={"platform": platform, "username": username, "status": str(found)},
                confidence=0.85,
                risk_score=0.2,
                sources=["bosint_username_search"],
                notes=f"Found on {platform} via BOSINT username search"
            )
            created_entities.append(entity)

    return created_entities


async def run_perplexity_osint(investigation_id: str, entity_type: str, value: str) -> str:
    """Run Perplexity search for an entity to get web intelligence"""
    queries = {
        "username": f'OSINT research: username "{value}" - find all social media profiles, mentions, associated accounts and real identity clues',
        "email": f'OSINT research: email "{value}" - find associated accounts, data breaches, domain registration, public mentions',
        "domain": f'OSINT research: domain "{value}" - find ownership, hosting infrastructure, associated emails, historical data, suspicious activity',
        "ip": f'OSINT research: IP address "{value}" - find geolocation, ASN, hosting provider, abuse reports, associated domains',
        "phone": f'OSINT research: phone number "{value}" - find owner, location, carrier, associated accounts',
        "wallet": f'OSINT research: cryptocurrency wallet "{value}" - find transaction history, exchange interactions, associated entities',
        "person": f'OSINT research: person named "{value}" - find social media, professional background, public records, associations',
    }
    query = queries.get(entity_type, f'OSINT research on {entity_type}: "{value}"')
    return await call_perplexity_search(query)


async def ai_generate_leads_from_context(investigation_id: str, entities: List[Dict],
                                          relationships: List[Dict], scan_summaries: List[str]) -> List[Dict]:
    """Use Gemini to generate high-quality investigation leads from collected data"""
    entity_summary = "\n".join([f"- {e['entity_type']}: {e['value']} (risk: {e.get('risk_score', 0):.1f})" for e in entities[:20]])
    rel_summary = "\n".join([f"- {r.get('relationship_type', '?')}: entity connection" for r in relationships[:10]])
    scan_text = "\n\n".join(scan_summaries[:5]) if scan_summaries else "No scan data available."

    prompt = f"""You are an expert OSINT investigator analyzing a case. Generate actionable investigation leads.

ENTITIES DISCOVERED:
{entity_summary or "None yet"}

RELATIONSHIPS:
{rel_summary or "None yet"}

SCAN INTELLIGENCE:
{scan_text[:3000]}

Generate 3-7 high-quality investigation leads. For each lead provide:
- title: clear actionable title
- description: detailed explanation
- lead_type: one of [alias_cluster, shared_infrastructure, username_reuse, high_risk_connection, identity_pivot, data_breach_exposure, dark_web_presence]
- severity: critical/high/medium/low
- confidence: 0.0-1.0
- suggested_actions: array of action strings (e.g. "Check username on gaming platforms", "Run dark web search for email")

Return ONLY a JSON array:
[
  {{
    "title": "...",
    "description": "...",
    "lead_type": "...",
    "severity": "high",
    "confidence": 0.85,
    "suggested_actions": ["action 1", "action 2"]
  }}
]"""

    try:
        result = await call_gemini_api(prompt, json_mode=True)
        leads_data = json.loads(result)
        return leads_data if isinstance(leads_data, list) else []
    except Exception as e:
        logger.error(f"AI lead generation error: {e}")
        return []


SWATTED_BASE = "https://swattedw.tf"

async def _swatted_login() -> Optional[Dict[str, str]]:
    """Exchange account token for fresh session credentials. CSRF is single-use so we call this before every POST."""
    if not SWATTED_API_KEY:
        return None
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(
                f"{SWATTED_BASE}/api/login_token_api",
                json={"api_key": SWATTED_API_KEY},
                headers={"Content-Type": "application/json"}
            )
            if r.status_code == 200:
                d = r.json()
                return {
                    "session": d["sessionToken"],
                    "user_id": d["userID"],
                    "csrf": d["csrfToken"],
                    "cookies": dict(r.cookies)
                }
    except Exception as e:
        logger.error(f"Swatted login error: {e}")
    return None


async def swatted_post(endpoint: str, body: Dict) -> Dict[str, Any]:
    """Make an authenticated POST to Swatted. Handles fresh CSRF per request."""
    creds = await _swatted_login()
    if not creds:
        return {"error": "Swatted login failed", "data": None, "success": False}
    try:
        async with httpx.AsyncClient(timeout=30.0, cookies=creds["cookies"]) as client:
            r = await client.post(
                f"{SWATTED_BASE}{endpoint}",
                json=body,
                headers={
                    "Authorization": f"Bearer {creds['session']}",
                    "X-User-ID": creds["user_id"],
                    "X-CSRF-Token": creds["csrf"],
                    "Content-Type": "application/json",
                }
            )
            d = r.json()
            return {"error": None if d.get("success") else d.get("error", "unknown"), "data": d, "success": bool(d.get("success"))}
    except Exception as e:
        logger.error(f"Swatted POST {endpoint} error: {e}")
        return {"error": str(e), "data": None, "success": False}


async def swatted_get(endpoint: str) -> Dict[str, Any]:
    """Make an authenticated GET to Swatted. Can reuse session token (no CSRF needed)."""
    creds = await _swatted_login()
    if not creds:
        return {"error": "Swatted login failed", "data": None, "success": False}
    try:
        async with httpx.AsyncClient(timeout=30.0, cookies=creds["cookies"]) as client:
            r = await client.get(
                f"{SWATTED_BASE}{endpoint}",
                headers={
                    "Authorization": f"Bearer {creds['session']}",
                    "X-User-ID": creds["user_id"],
                }
            )
            d = r.json()
            return {"error": None if d.get("success") else d.get("error", "unknown"), "data": d, "success": bool(d.get("success"))}
    except Exception as e:
        logger.error(f"Swatted GET {endpoint} error: {e}")
        return {"error": str(e), "data": None, "success": False}


async def swatted_breach_lookup(query: str, query_type: str = "email") -> Dict[str, Any]:
    """Unified Swatted breach lookup — tries LeakCheck, HackCheck, LeakOSINT in parallel."""
    if not SWATTED_API_KEY:
        return {"error": "Swatted API not configured", "data": None}

    results = {}
    endpoints = [
        ("/api/leakcheck/v2", "leakcheck"),
        ("/api/hackcheck", "hackcheck"),
        ("/api/leakosint/search", "leakosint"),
    ]
    for endpoint, name in endpoints:
        try:
            r = await swatted_post(endpoint, {"query": query})
            if r.get("success"):
                results[name] = r["data"]
        except Exception as e:
            logger.warning(f"Swatted {name} error: {e}")

    if results:
        return {"error": None, "data": results, "success": True}
    return {"error": "No Swatted breach sources returned data", "data": None, "success": False}


async def swatted_full_breach_scan(query: str) -> Dict[str, Any]:
    """Run all available working breach sources against a query."""
    if not SWATTED_API_KEY:
        return {"error": "Swatted API not configured", "data": {}}

    results = {}
    breach_endpoints = [
        ("/api/leakcheck/v2", "LeakCheck"),
        ("/api/hackcheck", "HackCheck"),
        ("/api/leakosint/search", "LeakOSINT"),
        ("/api/breachbase", "BreachBase"),
        ("/api/intelvault", "IntelVault"),
        ("/api/osintdog/breachvip/search", "BreachVIP"),
    ]

    async def run_one(endpoint, name):
        try:
            r = await swatted_post(endpoint, {"query": query})
            if r.get("success"):
                results[name] = r["data"]
        except Exception as e:
            logger.warning(f"Swatted {name} scan error: {e}")

    await asyncio.gather(*[run_one(ep, name) for ep, name in breach_endpoints])
    return {"error": None if results else "No results", "data": results, "success": bool(results)}


async def investigation_engine_stream(investigation_id: str, input_text: str, auto_expand: bool, scan_depth: str) -> AsyncGenerator[str, None]:
    """Main AI investigation engine - yields SSE events as investigation progresses"""

    async def emit(event_type: str, data: Dict) -> str:
        payload = {"type": event_type, "timestamp": datetime.now(timezone.utc).isoformat(), **data}
        return f"data: {json.dumps(payload)}\n\n"

    scan_summaries = []
    all_created_entities = []

    try:
        yield await emit("status", {"message": "AI Investigation Engine activated", "phase": "init"})
        await asyncio.sleep(0.1)

        # Phase 1: AI Entity Extraction
        yield await emit("status", {"message": "Analyzing input with Gemini AI...", "phase": "extraction"})
        ai_entities = await ai_extract_entities_from_input(input_text)

        if not ai_entities:
            yield await emit("error", {"message": "Could not extract any entities from input. Please provide a username, email, domain, IP, or other identifier."})
            return

        yield await emit("status", {"message": f"Detected {len(ai_entities)} entity/entities", "phase": "extraction", "count": len(ai_entities)})

        # Save extracted entities to DB
        saved_seed_entities = []
        for ent in ai_entities:
            if not ent.get("value"):
                continue
            saved = await save_entity_to_db(
                investigation_id,
                ent.get("entity_type", "unknown"),
                ent["value"],
                label=ent.get("label", ent["value"]),
                confidence=ent.get("confidence", 0.8),
                notes=ent.get("notes", "Extracted from investigative input"),
                sources=["ai_entity_extraction"]
            )
            saved_seed_entities.append(saved)
            all_created_entities.append(saved)
            yield await emit("entity_discovered", {
                "entity": {
                    "id": saved["id"],
                    "entity_type": saved["entity_type"],
                    "value": saved["value"],
                    "label": saved.get("label", saved["value"]),
                    "confidence": saved.get("confidence", 0.8),
                    "risk_score": saved.get("risk_score", 0.3),
                    "source": "ai_extraction"
                }
            })

        # Phase 2: BOSINT Scans
        for seed_entity in saved_seed_entities:
            etype = seed_entity.get("entity_type")
            value = seed_entity.get("value")

            if etype == "username":
                yield await emit("scan_start", {"scan": "bosint_username", "query": value, "description": f"Searching 3,000+ platforms for @{value}..."})
                bosint_result = await bosint_api_call("username", value)

                if bosint_result.get("data"):
                    new_entities = await process_bosint_username_results(investigation_id, value, bosint_result)
                    all_created_entities.extend(new_entities)
                    scan_summaries.append(f"Username scan for '{value}': found {len(new_entities)} platform profiles. Data: {json.dumps(bosint_result.get('data', {}))[:1000]}")

                    for ne in new_entities:
                        yield await emit("entity_discovered", {
                            "entity": {
                                "id": ne["id"],
                                "entity_type": ne["entity_type"],
                                "value": ne["value"],
                                "label": ne.get("label", ne["value"]),
                                "confidence": ne.get("confidence", 0.8),
                                "risk_score": ne.get("risk_score", 0.2),
                                "source": "bosint_username"
                            }
                        })
                        if ne.get("id") != seed_entity.get("id"):
                            await save_relationship_to_db(
                                investigation_id, seed_entity["id"], ne["id"],
                                "used_on", f"@{value} on platform",
                                confidence=0.85,
                                metadata={"source": "bosint_username_search"}
                            )

                    yield await emit("scan_complete", {
                        "scan": "bosint_username",
                        "query": value,
                        "entities_found": len(new_entities),
                        "message": f"Found {len(new_entities)} platform profiles for @{value}"
                    })
                else:
                    scan_summaries.append(f"Username scan for '{value}': BOSINT returned no results or error: {bosint_result.get('error', 'unknown')}")
                    yield await emit("scan_complete", {"scan": "bosint_username", "query": value, "entities_found": 0, "message": "No platform profiles found in BOSINT database"})

            elif etype == "email":
                # BOSINT email breach
                yield await emit("scan_start", {"scan": "bosint_email", "query": value, "description": f"Checking BOSINT breach databases for {value}..."})
                bosint_result = await bosint_api_call("email", value)
                breach_data_combined = {}

                if bosint_result.get("data"):
                    breach_data_combined["bosint"] = bosint_result["data"]
                    scan_summaries.append(f"BOSINT email breach for '{value}': {json.dumps(bosint_result['data'])[:800]}")
                    await db.entities.update_one({"id": seed_entity["id"]}, {"$set": {"metadata.bosint_breach": bosint_result["data"], "risk_score": 0.7}})

                # Swatted full breach scan (LeakCheck + HackCheck + LeakOSINT + BreachBase + IntelVault + BreachVIP)
                yield await emit("scan_start", {"scan": "swatted_breach", "query": value, "description": f"Querying 6 breach databases via Swatted for {value}..."})
                swatted_result = await swatted_full_breach_scan(value)
                if swatted_result.get("data"):
                    breach_data_combined["swatted"] = swatted_result["data"]
                    scan_summaries.append(f"Swatted full breach scan for '{value}': {json.dumps(swatted_result['data'])[:1500]}")
                    await db.entities.update_one({"id": seed_entity["id"]}, {"$set": {
                        "metadata.swatted_breach": swatted_result["data"],
                        "risk_score": 0.8
                    }})
                    # Extract usernames from breach data for further expansion
                    breach_usernames = set()
                    for source_data in swatted_result["data"].values():
                        results_list = source_data.get("results", [])
                        if isinstance(results_list, list):
                            for record in results_list[:10]:
                                if isinstance(record, dict):
                                    if record.get("username"):
                                        breach_usernames.add(record["username"])
                    for uname in list(breach_usernames)[:3]:
                        saved = await save_entity_to_db(
                            investigation_id, "username", uname,
                            label=f"Username: {uname}",
                            confidence=0.9, risk_score=0.5,
                            sources=["swatted_breach_data"],
                            notes=f"Username extracted from breach records for {value}"
                        )
                        all_created_entities.append(saved)
                        yield await emit("entity_discovered", {
                            "entity": {
                                "id": saved["id"], "entity_type": "username",
                                "value": uname, "label": f"Username: {uname}",
                                "confidence": 0.9, "risk_score": 0.5,
                                "source": "swatted_breach"
                            }
                        })
                        await save_relationship_to_db(
                            investigation_id, seed_entity["id"], saved["id"],
                            "linked_to", "Breach-linked username",
                            confidence=0.9, metadata={"source": "swatted_breach_extraction"}
                        )

                yield await emit("scan_complete", {
                    "scan": "email_breach",
                    "query": value,
                    "entities_found": len(breach_data_combined.get("swatted", {})),
                    "breach_data": breach_data_combined,
                    "message": f"Breach scan complete: {len(breach_data_combined.get('swatted', {}))} sources returned data" if breach_data_combined else "No breach data found"
                })

            elif etype == "domain":
                yield await emit("scan_start", {"scan": "bosint_domain", "query": value, "description": f"Running domain intelligence on {value}..."})
                bosint_result = await bosint_api_call("domain", value)

                if bosint_result.get("data"):
                    data = bosint_result["data"]
                    scan_summaries.append(f"Domain intel for '{value}': {json.dumps(data)[:1000]}")
                    await db.entities.update_one({"id": seed_entity["id"]}, {"$set": {"metadata.domain_intel": data}})
                    yield await emit("scan_complete", {"scan": "bosint_domain", "query": value, "entities_found": 0, "domain_data": data, "message": f"Domain intelligence retrieved for {value}"})
                else:
                    scan_summaries.append(f"Domain scan for '{value}': {bosint_result.get('error', 'no data')}")
                    yield await emit("scan_complete", {"scan": "bosint_domain", "query": value, "entities_found": 0, "message": "No domain intelligence available"})

            elif etype == "ip":
                yield await emit("scan_start", {"scan": "bosint_ip", "query": value, "description": f"Running IP intelligence on {value}..."})
                bosint_result = await bosint_api_call("ip", value)

                if bosint_result.get("data"):
                    data = bosint_result["data"]
                    scan_summaries.append(f"IP intel for '{value}': {json.dumps(data)[:1000]}")
                    await db.entities.update_one({"id": seed_entity["id"]}, {"$set": {"metadata.ip_intel": data}})
                    yield await emit("scan_complete", {"scan": "bosint_ip", "query": value, "entities_found": 0, "ip_data": data, "message": f"IP intelligence retrieved for {value}"})
                else:
                    scan_summaries.append(f"IP scan for '{value}': {bosint_result.get('error', 'no data')}")
                    yield await emit("scan_complete", {"scan": "bosint_ip", "query": value, "entities_found": 0, "message": "No IP intelligence available"})

            elif etype == "phone":
                yield await emit("scan_start", {"scan": "bosint_phone", "query": value, "description": f"Running phone intelligence on {value}..."})
                bosint_result = await bosint_api_call("phone", value.replace("+", "").replace(" ", "").replace("-", ""))

                if bosint_result.get("data"):
                    data = bosint_result["data"]
                    scan_summaries.append(f"Phone intel for '{value}': {json.dumps(data)[:1000]}")
                    await db.entities.update_one({"id": seed_entity["id"]}, {"$set": {"metadata.phone_intel": data}})
                    yield await emit("scan_complete", {"scan": "bosint_phone", "query": value, "entities_found": 0, "phone_data": data, "message": f"Phone intelligence retrieved"})
                else:
                    scan_summaries.append(f"Phone scan for '{value}': {bosint_result.get('error', 'no data')}")
                    yield await emit("scan_complete", {"scan": "bosint_phone", "query": value, "entities_found": 0, "message": "No phone intelligence available"})

            # Phase 3: Perplexity Deep Search (for standard/deep scans)
            if scan_depth in ["standard", "deep"] and etype in ["username", "email", "domain", "person"]:
                yield await emit("scan_start", {"scan": "perplexity_search", "query": value, "description": f"Running Perplexity AI deep web search for {value}..."})
                perplexity_result = await run_perplexity_osint(investigation_id, etype, value)

                scan_summaries.append(f"Perplexity web search for {etype} '{value}':\n{perplexity_result[:1500]}")

                # Extract entities from Perplexity results
                regex_entities = extract_entities_from_text(perplexity_result, None)
                new_perplexity_entities = []

                for rex_ent in regex_entities[:10]:
                    if rex_ent["value"] == value:
                        continue
                    saved = await save_entity_to_db(
                        investigation_id,
                        rex_ent["type"],
                        rex_ent["value"],
                        label=rex_ent.get("label", rex_ent["value"]),
                        confidence=rex_ent.get("confidence", 0.6),
                        risk_score=rex_ent.get("risk_score", 0.3),
                        sources=["perplexity_search"],
                        notes=f"Discovered via Perplexity web search for {value}"
                    )
                    new_perplexity_entities.append(saved)
                    all_created_entities.append(saved)
                    yield await emit("entity_discovered", {
                        "entity": {
                            "id": saved["id"],
                            "entity_type": saved["entity_type"],
                            "value": saved["value"],
                            "label": saved.get("label", saved["value"]),
                            "confidence": saved.get("confidence", 0.6),
                            "risk_score": saved.get("risk_score", 0.3),
                            "source": "perplexity_search"
                        }
                    })

                yield await emit("scan_complete", {
                    "scan": "perplexity_search",
                    "query": value,
                    "entities_found": len(new_perplexity_entities),
                    "summary": perplexity_result[:500],
                    "message": f"Perplexity found {len(new_perplexity_entities)} additional entities"
                })

        # Phase 4: BOSINT Dark Web Search
        if scan_depth in ["standard", "deep"]:
            primary_value = saved_seed_entities[0]["value"] if saved_seed_entities else input_text[:50]
            yield await emit("scan_start", {"scan": "darkweb_search", "query": primary_value, "description": f"Scanning dark web for mentions of {primary_value}..."})
            dw_result = await bosint_api_call("darkweb", primary_value)

            if dw_result.get("data"):
                scan_summaries.append(f"Dark web scan for '{primary_value}': {json.dumps(dw_result['data'])[:1000]}")
                yield await emit("scan_complete", {
                    "scan": "darkweb_search",
                    "query": primary_value,
                    "entities_found": 0,
                    "darkweb_data": dw_result["data"],
                    "message": "Dark web intelligence retrieved"
                })
            else:
                yield await emit("scan_complete", {"scan": "darkweb_search", "query": primary_value, "entities_found": 0, "message": "No dark web mentions found"})

        # Phase 5: AI Relationship Inference
        yield await emit("status", {"message": "AI inferring relationships between discovered entities...", "phase": "relationship_analysis"})

        all_current_entities = await db.entities.find({"investigation_id": investigation_id}, {"_id": 0}).to_list(100)
        inferred_rels = await ai_infer_relationships(all_current_entities)
        saved_rels = []

        for rel in inferred_rels:
            src_id = rel.get("source_id")
            tgt_id = rel.get("target_id")
            if src_id and tgt_id and src_id != tgt_id:
                saved_rel = await save_relationship_to_db(
                    investigation_id, src_id, tgt_id,
                    rel.get("relationship_type", "linked_to"),
                    rel.get("label", ""),
                    confidence=rel.get("confidence", 0.7),
                    metadata={"reasoning": rel.get("reasoning", ""), "source": "ai_inference"}
                )
                if saved_rel:
                    saved_rels.append(saved_rel)
                    yield await emit("relationship_discovered", {
                        "relationship": {
                            "id": saved_rel["id"],
                            "source_id": src_id,
                            "target_id": tgt_id,
                            "type": rel.get("relationship_type", "linked_to"),
                            "label": rel.get("label", ""),
                            "confidence": rel.get("confidence", 0.7),
                            "reasoning": rel.get("reasoning", "")
                        }
                    })

        yield await emit("status", {"message": f"Discovered {len(saved_rels)} relationships", "phase": "relationship_analysis", "count": len(saved_rels)})

        # Phase 6: AI Lead Generation
        yield await emit("status", {"message": "Gemini AI generating investigation leads...", "phase": "lead_generation"})

        all_final_entities = await db.entities.find({"investigation_id": investigation_id}, {"_id": 0}).to_list(100)
        all_final_rels = await db.relationships.find({"investigation_id": investigation_id}, {"_id": 0}).to_list(100)

        ai_leads = await ai_generate_leads_from_context(investigation_id, all_final_entities, all_final_rels, scan_summaries)

        for lead_data in ai_leads:
            lead = {
                "id": f"lead_{uuid.uuid4().hex[:12]}",
                "investigation_id": investigation_id,
                "lead_type": lead_data.get("lead_type", "identity_pivot"),
                "title": lead_data.get("title", "Investigation Lead"),
                "description": lead_data.get("description", ""),
                "confidence": lead_data.get("confidence", 0.7),
                "severity": lead_data.get("severity", "medium"),
                "affected_entities": [],
                "evidence_ids": [],
                "suggested_actions": [{"type": "investigate", "label": a, "action": "manual"} for a in lead_data.get("suggested_actions", [])],
                "status": "new",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "metadata": {"source": "ai_investigation_engine", "scan_depth": scan_depth}
            }
            await db.investigation_leads.update_one(
                {"id": lead["id"]}, {"$set": lead}, upsert=True
            )
            yield await emit("lead_generated", {"lead": lead})

        # Also run the rule-based lead engine
        rule_leads = generate_investigation_leads(all_final_entities, all_final_rels, [], [])
        for rl in rule_leads[:5]:
            rl["investigation_id"] = investigation_id
            rl["created_at"] = datetime.now(timezone.utc).isoformat()
            await db.investigation_leads.update_one({"id": rl["id"]}, {"$set": rl}, upsert=True)

        # Create summary timeline event
        await create_timeline_event(
            investigation_id, "ai_analysis",
            f"AI Investigation Engine completed: {len(all_created_entities)} entities, {len(saved_rels)} relationships, {len(ai_leads)} AI leads",
            metadata={
                "entities_discovered": len(all_created_entities),
                "relationships_found": len(saved_rels),
                "leads_generated": len(ai_leads),
                "scan_depth": scan_depth,
                "sources_checked": ["gemini_extraction", "bosint", "perplexity", "rule_engine"]
            }
        )

        yield await emit("complete", {
            "message": "AI Investigation Engine completed",
            "stats": {
                "entities_discovered": len(all_created_entities),
                "relationships_found": len(saved_rels),
                "leads_generated": len(ai_leads),
                "scans_performed": len(scan_summaries)
            }
        })

    except Exception as e:
        logger.error(f"Investigation engine error: {e}", exc_info=True)
        yield await emit("error", {"message": f"Investigation engine error: {str(e)}"})


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
        
        model = "gemini-1.5-flash"

        if GENAI_AVAILABLE and GEMINI_API_KEY:
            response = await call_gemini_api(
                context,
                system_instruction="You are an expert OSINT investigator providing actionable intelligence suggestions.",
                json_mode=True
            )
        elif EMERGENT_AVAILABLE and EMERGENT_LLM_KEY:
            chat = LlmChat(
                api_key=EMERGENT_LLM_KEY,
                session_id=f"analysis-{input.investigation_id}",
                system_message="You are an expert OSINT investigator providing actionable intelligence suggestions."
            ).with_model("gemini", "gemini-3-flash-preview")
            user_message = UserMessage(text=context)
            response = await chat.send_message(user_message)
        else:
            raise HTTPException(status_code=503, detail="No AI backend configured. Add GEMINI_API_KEY to .env")
        
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
async def api_extract_entities(
    request: EntityExtractionRequest,
    x_api_key: Optional[str] = Header(None)
):
    """Extract potential entities from text content"""
    await validate_api_key(x_api_key)
    
    # Use the helper function
    extracted = extract_entities_from_text(request.text, request.source_evidence_id)
    
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

# ============= AI CHAT ENDPOINTS =============

@api_router.get("/investigations/{investigation_id}/chat/history")
async def get_chat_history(
    investigation_id: str,
    session_id: Optional[str] = None,
    limit: int = 50,
    x_api_key: Optional[str] = Header(None)
):
    """Get chat history for an investigation"""
    await validate_api_key(x_api_key)
    
    query = {"investigation_id": investigation_id}
    if session_id:
        query["session_id"] = session_id
    
    messages = await db.chat_messages.find(
        query,
        {"_id": 0}
    ).sort("timestamp", 1).to_list(limit)
    
    return {
        "messages": messages,
        "count": len(messages)
    }

@api_router.post("/investigations/{investigation_id}/chat")
async def chat_with_ai(
    investigation_id: str,
    request: ChatRequest,
    x_api_key: Optional[str] = Header(None)
):
    """Interactive AI chat with investigation context"""
    await validate_api_key(x_api_key)
    
    # Get or create session ID
    session_id = request.session_id or f"chat-{investigation_id}-{uuid.uuid4().hex[:8]}"
    
    try:
        # Fetch investigation context
        investigation = await db.investigations.find_one(
            {"id": investigation_id}, {"_id": 0}
        )
        if not investigation:
            raise HTTPException(status_code=404, detail="Investigation not found")
        
        entities = await db.entities.find(
            {"investigation_id": investigation_id}, {"_id": 0}
        ).to_list(100)
        
        relationships = await db.relationships.find(
            {"investigation_id": investigation_id}, {"_id": 0}
        ).to_list(100)
        
        evidence = await db.evidence.find(
            {"investigation_id": investigation_id}, {"_id": 0}
        ).to_list(50)
        
        timeline = await db.timeline_events.find(
            {"investigation_id": investigation_id}, {"_id": 0}
        ).sort("timestamp", -1).to_list(20)
        
        leads = await db.investigation_leads.find(
            {"investigation_id": investigation_id}, {"_id": 0}
        ).to_list(20)
        
        # Get chat history for context
        chat_history = await db.chat_messages.find(
            {"investigation_id": investigation_id, "session_id": session_id},
            {"_id": 0}
        ).sort("timestamp", 1).to_list(20)
        
        # Build comprehensive context
        context_parts = [
            f"# Investigation: {investigation.get('name', 'Unknown')}",
            f"Description: {investigation.get('description', 'N/A')}",
            f"\n## Statistics:",
            f"- Entities: {len(entities)}",
            f"- Relationships: {len(relationships)}",
            f"- Evidence Items: {len(evidence)}",
            f"- Investigation Leads: {len(leads)}",
        ]
        
        if entities:
            context_parts.append("\n## Key Entities:")
            entities_by_type = {}
            for e in entities:
                et = e.get('entity_type', 'unknown')
                if et not in entities_by_type:
                    entities_by_type[et] = []
                entities_by_type[et].append(e.get('value', '')[:50])
            
            for etype, values in list(entities_by_type.items())[:8]:
                context_parts.append(f"- {etype.upper()}: {', '.join(values[:5])}")
        
        if relationships:
            context_parts.append(f"\n## Relationships: {len(relationships)} connections discovered")
            entity_lookup = {e['id']: e for e in entities}
            for rel in relationships[:5]:
                source = entity_lookup.get(rel.get('source_entity_id'), {})
                target = entity_lookup.get(rel.get('target_entity_id'), {})
                context_parts.append(f"- {source.get('value', '?')[:20]} → {rel.get('relationship_type', '?')} → {target.get('value', '?')[:20]}")
        
        if leads:
            context_parts.append("\n## Active Leads:")
            for lead in leads[:5]:
                context_parts.append(f"- [{lead.get('severity', 'medium').upper()}] {lead.get('title', '?')}: {lead.get('description', '')[:100]}")
        
        if evidence:
            context_parts.append(f"\n## Evidence Summary: {len(evidence)} items")
            for ev in evidence[:5]:
                context_parts.append(f"- [{ev.get('evidence_type', 'unknown')}] {ev.get('content', '')[:80]}...")
        
        investigation_context = "\n".join(context_parts)
        
        # Build system message
        system_message = f"""You are an expert OSINT investigation analyst assistant. You have access to the current investigation data and can help analyze it.

Your capabilities:
1. Answer questions about entities, relationships, and evidence in this investigation
2. Identify patterns, connections, and suspicious activities
3. Suggest next investigative steps
4. Summarize the investigation status
5. Analyze potential connections between entities
6. Assess risk levels and provide threat intelligence insights

Always be professional, precise, and focus on actionable intelligence. When analyzing data, cite specific entities and relationships. If you identify potential leads or patterns, explain your reasoning.

CURRENT INVESTIGATION DATA:
{investigation_context}
"""
        
        # Initialize chat
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=session_id,
            system_message=system_message
        ).with_model("gemini", "gemini-3-flash-preview")
        
        # Add previous messages to context
        for msg in chat_history[-10:]:  # Last 10 messages for context
            if msg.get('role') == 'user':
                await chat.send_message(UserMessage(text=msg.get('content', '')))
            # Note: Assistant messages are automatically tracked by LlmChat
        
        # Store user message
        user_msg = ChatMessage(
            investigation_id=investigation_id,
            session_id=session_id,
            role="user",
            content=request.message
        )
        user_doc = serialize_datetime(user_msg.model_dump())
        await db.chat_messages.insert_one(user_doc)
        
        # Send message and get response
        response = await chat.send_message(UserMessage(text=request.message))
        
        # Store assistant message
        assistant_msg = ChatMessage(
            investigation_id=investigation_id,
            session_id=session_id,
            role="assistant",
            content=response
        )
        assistant_doc = serialize_datetime(assistant_msg.model_dump())
        await db.chat_messages.insert_one(assistant_doc)
        
        # Create timeline event
        await create_timeline_event(
            investigation_id,
            "ai_chat",
            f"AI chat interaction: {request.message[:50]}..."
        )
        
        return {
            "success": True,
            "session_id": session_id,
            "message": response,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"AI chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI chat failed: {str(e)}")

@api_router.delete("/investigations/{investigation_id}/chat/clear")
async def clear_chat_history(
    investigation_id: str,
    session_id: Optional[str] = None,
    x_api_key: Optional[str] = Header(None)
):
    """Clear chat history for an investigation"""
    await validate_api_key(x_api_key)
    
    query = {"investigation_id": investigation_id}
    if session_id:
        query["session_id"] = session_id
    
    result = await db.chat_messages.delete_many(query)
    
    return {
        "success": True,
        "deleted_count": result.deleted_count
    }

# ============= QUICK EVIDENCE INGEST ENDPOINTS =============

@api_router.post("/investigations/{investigation_id}/ingest/url")
async def ingest_url(
    investigation_id: str,
    request: URLIngestRequest,
    x_api_key: Optional[str] = Header(None)
):
    """Quick ingest evidence from a URL with automatic content extraction and entity detection"""
    await validate_api_key(x_api_key)
    
    # Fetch URL content
    url_data = await fetch_url_content(request.url)
    
    if not url_data["success"]:
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {url_data.get('error', 'Unknown error')}")
    
    # Create evidence record
    evidence = Evidence(
        investigation_id=investigation_id,
        evidence_type=request.evidence_type,
        source_url=request.url,
        content=url_data.get("content", "")[:10000],  # Limit stored content
        notes=request.notes or f"Auto-ingested from URL: {url_data.get('title', request.url)}"
    )
    
    doc = serialize_datetime(evidence.model_dump())
    await db.evidence.insert_one(doc)
    
    # Extract entities from content
    full_text = f"{url_data.get('title', '')} {url_data.get('content', '')} {request.url}"
    detected_entities = extract_entities_from_text(full_text, evidence.id)
    
    # Create timeline event
    await create_timeline_event(
        investigation_id,
        "evidence_ingested",
        f"URL ingested: {url_data.get('title', request.url)[:50]}",
        metadata={"evidence_id": evidence.id, "detected_entities": len(detected_entities)}
    )
    
    return {
        "success": True,
        "evidence": {
            "id": evidence.id,
            "type": evidence.evidence_type,
            "title": url_data.get("title", request.url),
            "source_url": request.url,
            "content_length": len(url_data.get("content", ""))
        },
        "detected_entities": detected_entities,
        "extraction_stats": {
            "total_found": len(detected_entities),
            "by_type": {}
        }
    }

@api_router.post("/investigations/{investigation_id}/ingest/text")
async def ingest_raw_text(
    investigation_id: str,
    request: RawTextIngestRequest,
    x_api_key: Optional[str] = Header(None)
):
    """Quick ingest raw text with automatic entity extraction"""
    await validate_api_key(x_api_key)
    
    if not request.content.strip():
        raise HTTPException(status_code=400, detail="Content cannot be empty")
    
    # Create evidence record
    evidence = Evidence(
        investigation_id=investigation_id,
        evidence_type=request.evidence_type,
        content=request.content[:50000],  # Limit size
        notes=request.notes or f"Raw text: {request.title or 'Untitled'}"
    )
    
    doc = serialize_datetime(evidence.model_dump())
    await db.evidence.insert_one(doc)
    
    # Extract entities
    detected_entities = extract_entities_from_text(request.content, evidence.id)
    
    # Group by type for stats
    entities_by_type = {}
    for entity in detected_entities:
        etype = entity.get("type", "unknown")
        if etype not in entities_by_type:
            entities_by_type[etype] = 0
        entities_by_type[etype] += 1
    
    # Create timeline event
    await create_timeline_event(
        investigation_id,
        "evidence_ingested",
        f"Raw text ingested: {request.title or 'Untitled'}",
        metadata={"evidence_id": evidence.id, "detected_entities": len(detected_entities)}
    )
    
    return {
        "success": True,
        "evidence": {
            "id": evidence.id,
            "type": evidence.evidence_type,
            "title": request.title or "Raw Text",
            "content_length": len(request.content)
        },
        "detected_entities": detected_entities,
        "extraction_stats": {
            "total_found": len(detected_entities),
            "by_type": entities_by_type
        }
    }

@api_router.post("/investigations/{investigation_id}/ingest/file")
async def ingest_file(
    investigation_id: str,
    file: UploadFile = File(...),
    evidence_type: str = Form("document"),
    notes: str = Form(""),
    x_api_key: Optional[str] = Header(None)
):
    """Upload and ingest a file with OCR/text extraction"""
    await validate_api_key(x_api_key)
    
    # Read file content
    file_content = await file.read()
    file_size = len(file_content)
    
    if file_size > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")
    
    extracted_text = ""
    content_type = file.content_type or ""
    filename = file.filename or "uploaded_file"
    
    # Extract text based on file type
    if "pdf" in content_type or filename.lower().endswith(".pdf"):
        extracted_text = extract_text_from_pdf(file_content)
        evidence_type = "pdf"
    elif "image" in content_type or any(filename.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".gif", ".webp"]):
        extracted_text = extract_text_from_image(file_content)
        evidence_type = "screenshot"
    elif "text" in content_type or any(filename.lower().endswith(ext) for ext in [".txt", ".log", ".csv"]):
        try:
            extracted_text = file_content.decode("utf-8")
        except:
            extracted_text = file_content.decode("latin-1", errors="ignore")
    
    # Create evidence record
    evidence = Evidence(
        investigation_id=investigation_id,
        evidence_type=evidence_type,
        content=extracted_text[:50000] if extracted_text else f"[Binary file: {filename}]",
        notes=notes or f"Uploaded file: {filename}"
    )
    
    doc = serialize_datetime(evidence.model_dump())
    await db.evidence.insert_one(doc)
    
    # Extract entities if we have text
    detected_entities = []
    if extracted_text:
        detected_entities = extract_entities_from_text(extracted_text, evidence.id)
    
    # Group by type
    entities_by_type = {}
    for entity in detected_entities:
        etype = entity.get("type", "unknown")
        if etype not in entities_by_type:
            entities_by_type[etype] = 0
        entities_by_type[etype] += 1
    
    # Create timeline event
    await create_timeline_event(
        investigation_id,
        "file_uploaded",
        f"File uploaded: {filename}",
        metadata={
            "evidence_id": evidence.id,
            "filename": filename,
            "file_size": file_size,
            "detected_entities": len(detected_entities)
        }
    )
    
    return {
        "success": True,
        "evidence": {
            "id": evidence.id,
            "type": evidence_type,
            "filename": filename,
            "file_size": file_size,
            "text_extracted": bool(extracted_text),
            "content_length": len(extracted_text) if extracted_text else 0
        },
        "detected_entities": detected_entities,
        "extraction_stats": {
            "total_found": len(detected_entities),
            "by_type": entities_by_type,
            "ocr_available": OCR_AVAILABLE,
            "pdf_available": PDF_AVAILABLE
        }
    }

@api_router.post("/investigations/{investigation_id}/entities/batch")
async def add_entities_batch(
    investigation_id: str,
    entities: List[EntityCreate],
    x_api_key: Optional[str] = Header(None)
):
    """Add multiple entities at once (e.g., from detected indicators)"""
    await validate_api_key(x_api_key)
    
    created_entities = []
    
    for entity_data in entities:
        entity = Entity(
            investigation_id=investigation_id,
            **entity_data.model_dump()
        )
        
        doc = serialize_datetime(entity.model_dump())
        await db.entities.insert_one(doc)
        created_entities.append(entity)
    
    # Create single timeline event for batch
    await create_timeline_event(
        investigation_id,
        "entities_batch_added",
        f"Batch added {len(created_entities)} entities",
        metadata={"count": len(created_entities)}
    )
    
    return {
        "success": True,
        "created_count": len(created_entities),
        "entities": [serialize_datetime(e.model_dump()) for e in created_entities]
    }

# ============= EVIDENCE CATEGORIES ENDPOINT =============

@api_router.get("/evidence/categories")
async def get_evidence_categories(x_api_key: Optional[str] = Header(None)):
    """Get all available evidence categories and types"""
    await validate_api_key(x_api_key)
    return EVIDENCE_CATEGORIES

# ============= AI INVESTIGATION ENGINE =============

@api_router.post("/investigations/{investigation_id}/ai/investigate")
async def ai_investigate(
    investigation_id: str,
    request: AIInvestigateRequest,
    x_api_key: Optional[str] = Header(None)
):
    """
    Main AI Investigation Engine — streams SSE events as the AI investigates.
    Accepts any raw input (username, email, domain, IP, phone, text snippet).
    Automatically extracts entities, runs BOSINT/Perplexity/Swatted scans,
    infers relationships, and generates AI leads.
    """
    await validate_api_key(x_api_key)

    investigation = await db.investigations.find_one({"id": investigation_id}, {"_id": 0})
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")

    return StreamingResponse(
        investigation_engine_stream(
            investigation_id,
            request.input_text,
            request.auto_expand,
            request.scan_depth
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        }
    )


@api_router.post("/investigations/{investigation_id}/scan/username")
async def scan_username(
    investigation_id: str,
    request: ScanRequest,
    x_api_key: Optional[str] = Header(None)
):
    """Run BOSINT username scan across 3,000+ platforms"""
    await validate_api_key(x_api_key)

    bosint_result = await bosint_api_call("username", request.query)
    entities_created = []

    if request.save_results and bosint_result.get("data"):
        seed_entity = None
        if request.entity_id:
            seed_entity = await db.entities.find_one({"id": request.entity_id}, {"_id": 0})
        else:
            seed_entity = await save_entity_to_db(investigation_id, "username", request.query, sources=["manual_scan"])

        new_entities = await process_bosint_username_results(investigation_id, request.query, bosint_result)
        entities_created = new_entities

        if seed_entity:
            for ne in new_entities:
                await save_relationship_to_db(
                    investigation_id, seed_entity["id"], ne["id"],
                    "used_on", f"@{request.query} on platform", confidence=0.85
                )

        await create_timeline_event(
            investigation_id, "enrichment_run",
            f"Username scan: @{request.query} found on {len(new_entities)} platforms",
            metadata={"scan_type": "bosint_username", "query": request.query, "results": len(new_entities)}
        )

    return {
        "success": True,
        "query": request.query,
        "scan_type": "bosint_username",
        "raw_data": bosint_result.get("data"),
        "entities_created": len(entities_created),
        "entities": [serialize_datetime(e) for e in entities_created[:20]],
        "error": bosint_result.get("error")
    }


@api_router.post("/investigations/{investigation_id}/scan/email")
async def scan_email(
    investigation_id: str,
    request: ScanRequest,
    x_api_key: Optional[str] = Header(None)
):
    """Run full email breach check via BOSINT + all Swatted breach sources"""
    await validate_api_key(x_api_key)

    bosint_result = await bosint_api_call("email", request.query)
    swatted_result = await swatted_full_breach_scan(request.query)

    combined = {
        "bosint": bosint_result.get("data"),
        "swatted": swatted_result.get("data"),
    }

    if request.save_results and request.entity_id:
        await db.entities.update_one(
            {"id": request.entity_id},
            {"$set": {"metadata.breach_data": combined, "risk_score": 0.75}}
        )
        await create_timeline_event(
            investigation_id, "enrichment_run",
            f"Email breach scan: {request.query}",
            metadata={"scan_type": "email_breach", "query": request.query, "sources": list(swatted_result.get("data", {}).keys())}
        )

    return {
        "success": True,
        "query": request.query,
        "scan_type": "email_breach",
        "breach_data": combined,
        "sources_checked": list(swatted_result.get("data", {}).keys()),
        "bosint_error": bosint_result.get("error"),
        "swatted_error": swatted_result.get("error")
    }


@api_router.post("/investigations/{investigation_id}/scan/breach")
async def scan_breach_full(
    investigation_id: str,
    request: ScanRequest,
    x_api_key: Optional[str] = Header(None)
):
    """Run all 6 Swatted breach sources: LeakCheck, HackCheck, LeakOSINT, BreachBase, IntelVault, BreachVIP"""
    await validate_api_key(x_api_key)

    result = await swatted_full_breach_scan(request.query)

    if request.save_results and request.entity_id and result.get("data"):
        await db.entities.update_one(
            {"id": request.entity_id},
            {"$set": {"metadata.breach_scan": result["data"], "risk_score": 0.8}}
        )
        await create_timeline_event(
            investigation_id, "enrichment_run",
            f"Full breach scan: {request.query} — {len(result.get('data', {}))} sources",
            metadata={"scan_type": "full_breach", "query": request.query, "sources": list(result.get("data", {}).keys())}
        )

    return {
        "success": result.get("success", False),
        "query": request.query,
        "scan_type": "full_breach",
        "sources_checked": ["LeakCheck", "HackCheck", "LeakOSINT", "BreachBase", "IntelVault", "BreachVIP"],
        "sources_with_data": list(result.get("data", {}).keys()),
        "breach_data": result.get("data", {}),
        "error": result.get("error")
    }


@api_router.post("/investigations/{investigation_id}/scan/domain")
async def scan_domain(
    investigation_id: str,
    request: ScanRequest,
    x_api_key: Optional[str] = Header(None)
):
    """Run BOSINT domain intelligence scan"""
    await validate_api_key(x_api_key)

    bosint_result = await bosint_api_call("domain", request.query)

    if request.save_results and request.entity_id and bosint_result.get("data"):
        await db.entities.update_one(
            {"id": request.entity_id},
            {"$set": {"metadata.domain_intel": bosint_result["data"]}}
        )
        await create_timeline_event(
            investigation_id, "enrichment_run",
            f"Domain intelligence scan: {request.query}",
            metadata={"scan_type": "bosint_domain", "query": request.query}
        )

    return {
        "success": True,
        "query": request.query,
        "scan_type": "bosint_domain",
        "domain_data": bosint_result.get("data"),
        "error": bosint_result.get("error")
    }


@api_router.post("/investigations/{investigation_id}/scan/ip")
async def scan_ip(
    investigation_id: str,
    request: ScanRequest,
    x_api_key: Optional[str] = Header(None)
):
    """Run BOSINT IP intelligence scan"""
    await validate_api_key(x_api_key)

    bosint_result = await bosint_api_call("ip", request.query)

    if request.save_results and request.entity_id and bosint_result.get("data"):
        await db.entities.update_one(
            {"id": request.entity_id},
            {"$set": {"metadata.ip_intel": bosint_result["data"]}}
        )

    return {
        "success": True,
        "query": request.query,
        "scan_type": "bosint_ip",
        "ip_data": bosint_result.get("data"),
        "error": bosint_result.get("error")
    }


@api_router.post("/investigations/{investigation_id}/scan/darkweb")
async def scan_darkweb(
    investigation_id: str,
    request: ScanRequest,
    x_api_key: Optional[str] = Header(None)
):
    """Run BOSINT dark web search"""
    await validate_api_key(x_api_key)

    bosint_result = await bosint_api_call("darkweb", request.query)
    swatted_result = await swatted_breach_lookup(request.query, "username")

    combined = {
        "bosint_darkweb": bosint_result.get("data"),
        "swatted": swatted_result.get("data"),
    }

    if request.save_results:
        await create_timeline_event(
            investigation_id, "enrichment_run",
            f"Dark web scan: {request.query}",
            metadata={"scan_type": "darkweb", "query": request.query}
        )

    return {
        "success": True,
        "query": request.query,
        "scan_type": "darkweb",
        "darkweb_data": combined,
        "bosint_error": bosint_result.get("error"),
        "swatted_error": swatted_result.get("error")
    }


@api_router.post("/investigations/{investigation_id}/scan/perplexity")
async def scan_perplexity(
    investigation_id: str,
    request: ScanRequest,
    x_api_key: Optional[str] = Header(None)
):
    """Run Perplexity AI deep web search for any entity"""
    await validate_api_key(x_api_key)

    result = await call_perplexity_search(
        f'OSINT intelligence research on: "{request.query}". Find all publicly available information, social media presence, data breaches, domains, aliases, and associations. Be comprehensive and cite sources.'
    )

    # Extract entities from results
    regex_entities = extract_entities_from_text(result, None)
    entities_created = []

    if request.save_results:
        for rex_ent in regex_entities[:15]:
            if rex_ent["value"] == request.query:
                continue
            saved = await save_entity_to_db(
                investigation_id,
                rex_ent["type"],
                rex_ent["value"],
                label=rex_ent.get("label", rex_ent["value"]),
                confidence=rex_ent.get("confidence", 0.6),
                risk_score=rex_ent.get("risk_score", 0.3),
                sources=["perplexity_search"],
                notes=f"Discovered via Perplexity search for: {request.query}"
            )
            entities_created.append(saved)

        await create_timeline_event(
            investigation_id, "enrichment_run",
            f"Perplexity web search: {request.query[:50]}",
            metadata={"scan_type": "perplexity", "entities_found": len(entities_created)}
        )

    return {
        "success": True,
        "query": request.query,
        "scan_type": "perplexity_search",
        "result": result,
        "entities_extracted": len(entities_created),
        "entities": [serialize_datetime(e) for e in entities_created]
    }


@api_router.post("/investigations/{investigation_id}/ai/chat")
async def ai_chat_gemini(
    investigation_id: str,
    request: ChatRequest,
    x_api_key: Optional[str] = Header(None)
):
    """AI Analyst chat powered by Gemini 1.5 Flash with full investigation context"""
    await validate_api_key(x_api_key)

    session_id = request.session_id or f"chat-{investigation_id}-{uuid.uuid4().hex[:8]}"

    investigation = await db.investigations.find_one({"id": investigation_id}, {"_id": 0})
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")

    entities = await db.entities.find({"investigation_id": investigation_id}, {"_id": 0}).to_list(100)
    relationships = await db.relationships.find({"investigation_id": investigation_id}, {"_id": 0}).to_list(50)
    leads = await db.investigation_leads.find({"investigation_id": investigation_id}, {"_id": 0}).to_list(20)
    evidence = await db.evidence.find({"investigation_id": investigation_id}, {"_id": 0}).to_list(20)
    chat_history = await db.chat_messages.find(
        {"investigation_id": investigation_id, "session_id": session_id}, {"_id": 0}
    ).sort("timestamp", 1).to_list(20)

    # Build entity map for relationship resolution
    entity_map = {e["id"]: e for e in entities}
    entities_by_type = {}
    for e in entities:
        et = e.get("entity_type", "unknown")
        entities_by_type.setdefault(et, []).append(e.get("value", "")[:60])

    context_parts = [
        f"# Investigation: {investigation.get('name', 'Unknown')}",
        f"Description: {investigation.get('description', 'N/A')}",
        f"Status: {investigation.get('status', 'active')}",
        f"\n## Scale: {len(entities)} entities | {len(relationships)} relationships | {len(leads)} leads | {len(evidence)} evidence items",
    ]

    if entities_by_type:
        context_parts.append("\n## Entities by Type:")
        for etype, vals in entities_by_type.items():
            context_parts.append(f"  {etype.upper()}: {', '.join(vals[:8])}")

    if relationships:
        context_parts.append("\n## Key Relationships:")
        for rel in relationships[:8]:
            src = entity_map.get(rel.get("source_entity_id"), {})
            tgt = entity_map.get(rel.get("target_entity_id"), {})
            context_parts.append(f"  {src.get('value','?')[:25]} --[{rel.get('relationship_type','?')}]--> {tgt.get('value','?')[:25]}")

    if leads:
        context_parts.append("\n## Active Leads:")
        for lead in leads[:6]:
            context_parts.append(f"  [{lead.get('severity','?').upper()}] {lead.get('title','?')}: {lead.get('description','')[:120]}")

    if evidence:
        context_parts.append(f"\n## Evidence ({len(evidence)} items):")
        for ev in evidence[:4]:
            context_parts.append(f"  [{ev.get('evidence_type','?')}] {ev.get('content','')[:80]}")

    investigation_context = "\n".join(context_parts)

    system_prompt = f"""You are an expert OSINT investigation analyst with access to live case data. You act like a senior intelligence analyst — precise, methodical, and actionable.

Your role:
- Answer questions about entities, relationships, and patterns in this investigation
- Identify connections, clusters, and suspicious behaviors
- Suggest concrete next investigative steps
- Assess risk and flag high-priority leads
- Cross-reference entities to find hidden connections
- Explain OSINT techniques and how to apply them to this case

Always cite specific entity values and relationships when reasoning. Be direct and action-oriented.

LIVE INVESTIGATION DATA:
{investigation_context}"""

    history_text = ""
    if chat_history:
        history_text = "\n\nPrevious conversation:\n"
        for msg in chat_history[-8:]:
            role = "Analyst" if msg.get("role") == "assistant" else "Investigator"
            history_text += f"{role}: {msg.get('content', '')[:300]}\n"

    full_prompt = f"{history_text}\n\nInvestigator: {request.message}\n\nAnalyst:"

    try:
        if GENAI_AVAILABLE and GEMINI_API_KEY:
            response_text = await call_gemini_api(full_prompt, system_instruction=system_prompt)
        elif EMERGENT_AVAILABLE and EMERGENT_LLM_KEY:
            chat = LlmChat(
                api_key=EMERGENT_LLM_KEY,
                session_id=session_id,
                system_message=system_prompt
            ).with_model("gemini", "gemini-3-flash-preview")
            response_text = await chat.send_message(UserMessage(text=request.message))
        else:
            response_text = "AI chat is not configured. Please add GEMINI_API_KEY to the backend .env file."

        # Save messages
        user_msg = ChatMessage(investigation_id=investigation_id, session_id=session_id, role="user", content=request.message)
        assistant_msg = ChatMessage(investigation_id=investigation_id, session_id=session_id, role="assistant", content=response_text)
        await db.chat_messages.insert_one(serialize_datetime(user_msg.model_dump()))
        await db.chat_messages.insert_one(serialize_datetime(assistant_msg.model_dump()))

        await create_timeline_event(investigation_id, "ai_chat", f"AI chat: {request.message[:60]}...")

        return {
            "success": True,
            "session_id": session_id,
            "message": response_text,
            "model": "gemini-1.5-flash",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"AI chat error: {e}")
        raise HTTPException(status_code=500, detail=f"AI chat failed: {str(e)}")


@api_router.get("/investigations/{investigation_id}/ai/status")
async def get_ai_status(x_api_key: Optional[str] = Header(None)):
    """Check which AI services are configured and available"""
    await validate_api_key(x_api_key)
    return {
        "gemini": bool(GEMINI_API_KEY and GENAI_AVAILABLE),
        "perplexity": bool(PERPLEXITY_API_KEY and OPENAI_AVAILABLE),
        "bosint": bool(BOSINT_API_KEY),
        "swatted": bool(SWATTED_API_KEY),
        "openai": bool(os.environ.get("OPENAI_API_KEY")),
        "models": {
            "reasoning": "gemini-1.5-flash" if GEMINI_API_KEY else "none",
            "web_search": "perplexity-sonar-pro" if PERPLEXITY_API_KEY else "none",
            "osint": "bosint-3000-platforms" if BOSINT_API_KEY else "none",
            "breach": "swatted-20k-daily" if SWATTED_API_KEY else "none"
        }
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

app.add_middleware(GZipMiddleware, minimum_size=1000)

@app.on_event("startup")
async def create_indexes():
    """Create MongoDB indexes for frequently-queried fields"""
    await db.investigations.create_index("id", unique=True)
    await db.entities.create_index("investigation_id")
    await db.entities.create_index([("id", 1), ("investigation_id", 1)])
    await db.relationships.create_index("investigation_id")
    await db.relationships.create_index([("id", 1), ("investigation_id", 1)])
    await db.timeline_events.create_index("investigation_id")
    await db.timeline_events.create_index([("investigation_id", 1), ("timestamp", -1)])
    await db.evidence.create_index("investigation_id")
    await db.evidence.create_index([("id", 1), ("investigation_id", 1)])
    await db.ai_suggestions.create_index([("investigation_id", 1), ("status", 1)])
    await db.investigation_leads.create_index("investigation_id")
    await db.investigation_leads.create_index([("id", 1), ("investigation_id", 1)])
    await db.chat_messages.create_index([("investigation_id", 1), ("session_id", 1)])
    logger.info("MongoDB indexes created")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

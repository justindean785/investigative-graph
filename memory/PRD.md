# TRACE ANALYST - AI-Powered OSINT Investigation Platform

## Product Requirements Document (PRD)

### Original Problem Statement
Build an AI-powered OSINT investigation platform that functions as a central workspace for managing investigations with:
- Investigation Case Manager
- Entity System with graph relationships
- Evidence collection and extraction
- AI Investigation Assistant
- Timeline tracking
- Network discovery and lead generation

### Architecture Requirements
1. **Centralized State**: Single `investigationStore` (Zustand)
2. **Event-Sourced Timeline**: Every action appends a timeline event
3. **Normalized Entity & Relationship Models**
4. **Graph Derivation**: Graph derived from central store entities/relationships
5. **Actionable AI Suggestions**: AI suggestions with clickable actions
6. **Evidence-First Workflow**: Evidence → Entities → Graph → Leads → Timeline → AI

---

## What's Been Implemented

### Date: March 4, 2026

#### Core Platform (100% Complete)
- [x] FastAPI backend with MongoDB
- [x] React frontend with Zustand state management
- [x] Professional dark "cyber intelligence" UI theme
- [x] Investigation CRUD operations
- [x] Entity management (person, email, domain, wallet, IP, username, etc.)
- [x] Relationship/connection management
- [x] Evidence collection system
- [x] Timeline event tracking

#### Evidence-First Workflow (100% Complete)
- [x] Evidence tab as default landing page
- [x] Evidence types: screenshot, webpage, document, social post, blockchain tx, archive
- [x] Entity extraction from evidence
- [x] Guided workflow: Evidence → Entities → Graph → Leads → Timeline → AI

#### Entity System (100% Complete)
- [x] 10 entity types with icons and colors
- [x] Entity cards with link counts and risk indicators
- [x] Entity linking/relationship creation dialog
- [x] Entity detail drawer in graph view

#### Graph Visualization (100% Complete)
- [x] React Flow integration
- [x] Custom node styling with entity icons
- [x] Relationship labels on edges
- [x] MiniMap and zoom controls
- [x] Empty state guiding users to add evidence/entities

#### Investigation Lead Engine (100% Complete) - NEW
- [x] **Automated Hypothesis Generation**
  - Alias cluster detection (shared domain patterns)
  - Wallet cluster detection (shared connections)
  - Shared infrastructure patterns
  - Username reuse detection
  - High-risk connection networks
  - Timing anomaly detection
  - Missing connection hypotheses
- [x] Lead status workflow (new → investigating → confirmed/dismissed)
- [x] Confidence percentages and severity levels
- [x] Analysis details with metadata
- [x] Suggested actions per lead
- [x] Lead filtering by status

#### Entity Intelligence (100% Complete) - NEW
- [x] **Entity Extraction Engine**
  - Email pattern detection
  - Domain extraction (including .onion)
  - IP address detection
  - Crypto wallet detection (ETH, BTC)
  - Phone number detection
  - Username/handle detection
  - URL extraction
- [x] **Entity Enrichment** (MOCKED for MVP)
  - Email: breach exposure, associated usernames, risk score
  - Domain: WHOIS, DNS records, hosting info, threat intelligence
  - Wallet: balance, transactions, exchange interactions, risk indicators
  - IP: geolocation, hosting ASN, reputation, abuse reports
  - Person: social presence, associated entities

#### Graph Intelligence (100% Complete) - NEW
- [x] Cluster detection (connected components)
- [x] Central node detection (degree centrality)
- [x] Suspicious pattern detection
- [x] Shortest path analysis between high-risk entities
- [x] Graph statistics

#### AI Integration
- [x] AI Suggestions tab with Flash/Pro modes
- [x] Gemini 3 integration via Emergent LLM key
- [x] Analysis endpoint for investigation context

---

## API Endpoints

### Investigations
- `POST /api/investigations` - Create investigation
- `GET /api/investigations` - List investigations
- `GET /api/investigations/{id}` - Get investigation
- `DELETE /api/investigations/{id}` - Delete investigation

### Entities
- `POST /api/investigations/{id}/entities` - Add entity
- `GET /api/investigations/{id}/entities` - List entities
- `DELETE /api/investigations/{id}/entities/{entity_id}` - Delete entity

### Relationships
- `POST /api/investigations/{id}/relationships` - Create connection
- `GET /api/investigations/{id}/relationships` - List connections

### Evidence
- `POST /api/investigations/{id}/evidence` - Add evidence
- `GET /api/investigations/{id}/evidence` - List evidence

### Timeline
- `GET /api/investigations/{id}/timeline` - Get timeline events

### Intelligence (NEW)
- `POST /api/extract/entities` - Extract entities from text
- `POST /api/enrich/entity` - Get entity enrichment data
- `GET /api/investigations/{id}/entities/{entity_id}/enrichment` - Get enrichment for entity

### Graph Analysis (NEW)
- `POST /api/investigations/{id}/graph/analyze` - Full graph analysis
- `GET /api/investigations/{id}/graph/clusters` - Get clusters
- `GET /api/investigations/{id}/graph/suspicious-patterns` - Get patterns

### Lead Engine (NEW)
- `POST /api/investigations/{id}/leads/generate` - Generate leads
- `GET /api/investigations/{id}/leads` - List leads
- `PATCH /api/investigations/{id}/leads/{lead_id}` - Update lead status

---

## Tech Stack
- **Backend**: FastAPI, Python, MongoDB
- **Frontend**: React, Tailwind CSS, Zustand, React Flow
- **AI**: Gemini 3 via Emergent LLM Key
- **Database**: MongoDB

---

## What's MOCKED

1. **Entity Enrichment Data** - Returns deterministic mock data based on entity value hash
   - Real implementation would integrate: HaveIBeenPwned, SecurityTrails, VirusTotal, blockchain explorers

2. **OSINT Search** - Returns sample data
   - Real implementation would integrate external OSINT APIs

---

## Remaining Backlog

### P0 (High Priority)
- [ ] Report generation (PDF/DOCX export)
- [ ] Real OSINT data source integrations

### P1 (Medium Priority)
- [ ] Entity auto-enrichment on creation
- [ ] Graph layout algorithms (force-directed, hierarchical)
- [ ] Advanced graph analytics (PageRank, betweenness centrality)

### P2 (Future)
- [ ] Authentication system
- [ ] Team collaboration features
- [ ] Evidence file upload (screenshots, documents)
- [ ] Webhook integrations
- [ ] API rate limiting and quotas

---

## Key Files Reference

### Backend
- `/app/backend/server.py` - Main API server with all endpoints
- `/app/backend/.env` - Environment variables

### Frontend
- `/app/frontend/src/pages/InvestigationWorkspace.js` - Main workspace
- `/app/frontend/src/pages/Dashboard.js` - Case dashboard
- `/app/frontend/src/store/investigationStore.js` - Zustand store
- `/app/frontend/src/config/api.js` - API configuration

### Workspace Components
- `/app/frontend/src/components/workspace/EvidenceWorkspace.js`
- `/app/frontend/src/components/workspace/EntitiesWorkspace.js`
- `/app/frontend/src/components/workspace/GraphView.js`
- `/app/frontend/src/components/workspace/LeadsWorkspace.js`
- `/app/frontend/src/components/workspace/TimelineWorkspace.js`
- `/app/frontend/src/components/workspace/AISuggestionsWorkspace.js`

---

## Testing

### Test Files
- `/app/backend/tests/test_investigation_api.py` - API tests
- `/app/backend/tests/test_lead_engine.py` - Lead engine tests

### Test Reports
- `/app/test_reports/iteration_1.json` - Initial testing
- `/app/test_reports/iteration_2.json` - Lead engine testing

---

## Design Guidelines
- Pure black backgrounds (#050505, #0a0a0a)
- Cyan/blue accent colors (#06b6d4)
- Sharp edges, glassmorphism
- Professional "analyst tool" aesthetic
- Font: JetBrains Mono for code, system fonts for UI

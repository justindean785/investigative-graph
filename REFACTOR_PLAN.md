# TRACE ANALYST AUTONOMOUS INVESTIGATION REFACTOR

## EXECUTIVE SUMMARY

This document outlines the architectural transformation from a manual, tab-heavy OSINT tool into an AI-first autonomous investigation platform.

---

## AUDIT FINDINGS

### Current Architecture Issues

1. **Fragmented User Experience (7 Tabs)**
   - Evidence → Entities → Graph → Leads → Timeline → AI Chat → AI Gen
   - Requires constant manual navigation
   - No unified investigation surface
   - Cognitive load from remembering which tab does what

2. **Manual Suggestion-First Flow**
   - AI generates suggestions
   - User clicks "Accept" or "Investigate"
   - User manually switches tabs
   - User manually triggers next action
   - **AI suggests but doesn't act**

3. **No Autonomous Engine**
   - No entity extraction → enrichment → pivot loop
   - No visited entity tracking
   - No auto-pivoting from OSINT results
   - Manual OSINT search only

4. **Provider Outputs Not Normalized**
   - GHOSINT returns one schema
   - Swatted returns different schema
   - BOSINT returns yet another schema
   - No unified entity/evidence model

5. **Graph Doesn't Self-Build**
   - Manual node/edge creation
   - No auto-linking from source data
   - No provenance tracking
   - No confidence propagation

6. **No Live Execution Feedback**
   - No streaming updates
   - No progress indicators for AI work
   - Fire-and-forget API calls

### What Works (Don't Break)**:
- ✅ GHOSINT/Swatted/BOSINT providers connected
- ✅ Parallel OSINT querying
- ✅ 76/76 backend tests passing
- ✅ Entity extraction regex patterns
- ✅ MongoDB integration

---

## TARGET STATE

### Single Investigation Workspace

```
┌─────────────────────────────────────────────────────────────┐
│  [<] Case #TA-2024-001 | Project Phoenix     [Search] [⚙]  │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 📋 Paste anything — text, breach data, phone, email │   │
│  │ The AI will extract, enrich, and pivot automatically│   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌──────────────────┬─────────────────────────────────────┐ │
│  │ LIVE FEED        │  GRAPH / CANVAS                     │ │
│  │─────────────────│                                     │ │
│  │ ✓ Extracted     │        [Visual Graph View]         │ │
│  │   phone number  │                                     │ │
│  │ → Querying      │                                     │ │
│  │   GHOSINT       │                                     │ │
│  │ → Found email   │                                     │ │
│  │ → Pivoting to   │                                     │ │
│  │   username      │                                     │ │
│  │ ⚠ Low confidence│                                     │ │
│  │   on wallet     │                                     │ │
│  │                 │                                     │ │
│  └──────────────────┴─────────────────────────────────────┘ │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ ENTITY INSPECTOR & EVIDENCE                            │  │
│  │ [Selected Node Details | Source Links | Confidence]    │  │
│  └────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Autonomous Investigation Flow

```
USER PASTES INPUT
     ↓
Extract Entities (backend regex + AI)
     ↓
Enqueue Seed Entities
     ↓
─────────── INVESTIGATION LOOP ───────────
│                                          │
│  Dequeue Entity                          │
│       ↓                                  │
│  Check if Visited                        │
│       ↓                                  │
│  Select Provider Strategy                │
│   (GHOSINT/Swatted/BOSINT)              │
│       ↓                                  │
│  Execute Enrichment Calls                │
│       ↓                                  │
│  Normalize Results                       │
│       ↓                                  │
│  Extract New Entities                    │
│       ↓                                  │
│  Create Graph Nodes/Edges                │
│       ↓                                  │
│  Attach Evidence/Sources                 │
│       ↓                                  │
│  Calculate Confidence                    │
│       ↓                                  │
│  Enqueue Fresh Pivots                    │
│       ↓                                  │
│  Stream Update to Frontend               │
│       ↓                                  │
│  Check Stop Conditions                   │
│   (max depth, low confidence, no pivots) │
│       ↓                                  │
└──────────────────────────────────────────┘
```

---

## IMPLEMENTATION PLAN

### Phase 1: Backend — Autonomous Engine Core

**Files to Create**:
- `backend/engine/__init__.py`
- `backend/engine/investigation_engine.py` — Main orchestrator
- `backend/engine/entity_processor.py` — Entity enrichment logic
- `backend/engine/pivot_planner.py` — Pivot strategy selection
- `backend/engine/normalizer.py` — Provider output normalization
- `backend/engine/graph_updater.py` — Auto graph construction
- `backend/engine/models.py` — Normalized schemas

**New API Endpoints**:
- `POST /api/investigations/{id}/auto-investigate` — Start autonomous investigation
- `GET /api/investigations/{id}/stream` — SSE event stream
- `POST /api/investigations/{id}/pivot` — Manual pivot trigger

**Normalized Entity Schema**:
```python
{
  "id": "ent-uuid",
  "type": "email|phone|username|domain|ip|wallet|name|address",
  "value": "test@gmail.com",
  "confidence": 0.85,
  "risk_score": 0.3,
  "sources": [
    {
      "provider": "ghosint",
      "service": "leakcheck",
      "found_at": "2026-03-21T...",
      "raw_data": {...}
    }
  ],
  "derived_entities": [
    {"type": "username", "value": "test123", "confidence": 0.7}
  ],
  "metadata": {}
}
```

### Phase 2: Frontend — Unified Investigation Workspace

**Files to Refactor**:
- `frontend/src/pages/InvestigationWorkspace.js` → Complete redesign
- `frontend/src/components/workspace/UnifiedInvestigation.js` → NEW main component
- `frontend/src/components/investigation/LiveFeed.js` — NEW stream consumer
- `frontend/src/components/investigation/UniversalInput.js` — NEW paste anything input
- `frontend/src/components/investigation/EntityInspector.js` — NEW detail panel
- `frontend/src/store/investigationStore.js` — Add autonomous state

**Remove These Components** (merge into unified view):
- `AISuggestionsWorkspace.js`
- `LeadsWorkspace.js`
- `TimelineWorkspace.js` (merge into live feed)

**Keep But Refactor**:
- `GraphView.js` — Enhance to show live updates
- `EntitiesWorkspace.js` → Become `EntityInspector.js`
- `EvidenceWorkspace.js` → Drawer in unified view

### Phase 3: Live Streaming

**Backend**:
- SSE endpoint for investigation updates
- Event types: ENTITY_DISCOVERED, ENRICHMENT_STARTED, ENRICHMENT_COMPLETE, PIVOT_SELECTED, CONFIDENCE_UPDATED, INVESTIGATION_PAUSED

**Frontend**:
- EventSource connection
- Live feed component
- Toast notifications for major events

### Phase 4: Quick Wins

**Dashboard Improvements**:
- Add checkbox selection for investigations
- Add bulk delete button
- Add "Delete All" option

**Fixed Gemini Model**:
- ✅ Defaults: `gemini-2.0-flash` (flash/chat) and `gemini-1.5-pro` (pro); override via `GEMINI_MODEL_*` in `.env` when Google rotates IDs

---

## PIVOT STRATEGIES

### Email
1. Breach search (GHOSINT leakcheck, Swatted leakosint, BOSINT email)
2. Dark web search (BOSINT darkweb)
3. Extract usernames from breach data
4. Extract names/phones/addresses from results

### Phone
1. Reverse lookup (BOSINT phone)
2. Breach search (GHOSINT/Swatted)
3. Extract associated emails/names

### Username
1. Platform scan (BOSINT username, Swatted social lookups)
2. Dark web search
3. Extract linked accounts

### Domain
1. WHOIS/DNS (BOSINT domain, Swatted shodan_dns)
2. Infrastructure analysis
3. Extract registrant info

### IP
1. Geolocation (BOSINT ip, Swatted shodan)
2. ASN/hosting analysis
3. Threat intelligence

### Wallet
1. Blockchain analysis (Swatted crypto)
2. Dark web mentions (BOSINT darkweb)

---

## STOP CONDITIONS

- Max investigation depth (default: 5 hops)
- Max entities processed (default: 100)
- Confidence threshold (stop pivoting below 0.3)
- Budget limit (max API calls)
- User intervention requested
- No new high-value pivots remaining
- Loop detection (entity already fully processed)

---

## SUCCESS METRICS

**Before**:
- User pastes phone → must manually run OSINT → must manually extract email → must manually pivot to email → repeat
- Average investigation: 47 manual clicks, 12 tab switches

**After**:
- User pastes phone → AI automatically extracts → enriches → pivots → builds graph
- Average investigation: 3 clicks (paste, supervise, export)

---

## MIGRATION STRATEGY

1. **Backend First**: Implement engine, keep existing endpoints working
2. **Feature Flag**: Add `autonomous_mode` toggle in investigation settings
3. **Gradual Rollout**: Keep old tabs, add new unified view as option
4. **Full Cutover**: Once stable, remove old tab structure

---

## FILES CHANGED SUMMARY

### Backend (New):
- `backend/engine/` (6 new files)
- `backend/engine/investigation_engine.py`
- `backend/engine/entity_processor.py`
- `backend/engine/pivot_planner.py`
- `backend/engine/normalizer.py`
- `backend/engine/graph_updater.py`
- `backend/engine/models.py`

### Backend (Modified):
- `backend/server.py` (+3 endpoints, +SSE setup)

### Frontend (New):
- `frontend/src/components/investigation/` (4 new files)
- `frontend/src/components/investigation/UnifiedInvestigation.js`
- `frontend/src/components/investigation/LiveFeed.js`
- `frontend/src/components/investigation/UniversalInput.js`
- `frontend/src/components/investigation/EntityInspector.js`

### Frontend (Modified):
- `frontend/src/pages/InvestigationWorkspace.js` (major refactor)
- `frontend/src/pages/Dashboard.js` (add bulk delete)
- `frontend/src/store/investigationStore.js` (add autonomous state)
- `frontend/src/components/workspace/GraphView.js` (live updates)

### Frontend (Removed):
- `frontend/src/components/workspace/AISuggestionsWorkspace.js`
- `frontend/src/components/workspace/LeadsWorkspace.js`

---

## ESTIMATED SCOPE

- **Lines Changed**: ~3,500 lines (1,800 backend, 1,700 frontend)
- **New Files**: 10
- **Modified Files**: 8
- **Deleted Files**: 2
- **Tests to Add**: 25 new test cases

---

## NEXT STEPS

1. ✅ Audit complete
2. → Implement backend investigation engine
3. → Normalize provider outputs
4. → Add SSE streaming
5. → Build unified frontend workspace
6. → Add bulk delete to dashboard
7. → Remove old tab structure
8. → Update tests
9. → Deploy and monitor

---

**Status**: Ready for implementation
**Priority**: P0 — Core product transformation
**Risk**: High (large refactor)
**Mitigation**: Incremental rollout with feature flag

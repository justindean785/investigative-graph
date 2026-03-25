# Test Results — Trace Analyst OSINT Platform

_Last updated: 2026-03-25_

## Summary

| Status | Count |
|--------|-------|
| ✅ Implemented & Working | 9 |
| 🔄 In Progress / Stuck | 1 |
| ❌ Not Started | 0 |

---

## Tasks

### 1. FastAPI Backend — Core CRUD
- **implemented**: true
- **working**: true
- **priority**: high
- **needs_retesting**: false
- **notes**: Investigations, Entities, Relationships, Evidence, Timeline endpoints. Tested by `backend/tests/test_investigation_api.py`.

### 2. Authentication (x-api-key header gate)
- **implemented**: true
- **working**: true
- **priority**: high
- **needs_retesting**: false
- **notes**: `API_KEY` env var defaulting to `trace-analyst-secret-2026`. Tested by `testsprite_tests/backend/test_auth.py`.

### 3. MongoDB Integration
- **implemented**: true
- **working**: true
- **priority**: high
- **needs_retesting**: false
- **notes**: conftest.py auto-starts mongod; CI installs MongoDB 7.0 from official repo.

### 4. Entity Extraction Endpoint (`/api/extract/entities`)
- **implemented**: true
- **working**: true
- **priority**: medium
- **needs_retesting**: false
- **notes**: Regex-based extraction for email, domain, IP, URL, crypto wallet, phone. Tested by `backend/tests/test_lead_engine.py` and `testsprite_tests/backend/test_entities.py`.

### 5. AI Chat + Quick Ingest Endpoints
- **implemented**: true
- **working**: true
- **priority**: medium
- **needs_retesting**: false
- **notes**: Chat history persists in MongoDB. LLM calls use emergentintegrations stub when `EMERGENT_LLM_KEY` is unset. Tested by `backend/tests/test_phase1_features.py`.

### 6. Frontend React Build (craco / react-scripts 5)
- **implemented**: true
- **working**: true
- **priority**: high
- **needs_retesting**: false
- **notes**: Requires Node ≤ v22 due to ajv/react-scripts 5 compatibility. `yarn build` succeeds.

### 7. Zustand Investigation Store
- **implemented**: true
- **working**: true
- **priority**: medium
- **needs_retesting**: false
- **notes**: Centralized state with timeline event sourcing. All workspace components consume `useInvestigationStore`.

### 8. SSRF / CORS Hardening (PR #17)
- **implemented**: true
- **working**: true
- **priority**: high
- **needs_retesting**: true
- **notes**: Grok-3 `/grok-enrich` endpoint, SSRF protection, CORS whitelist. PR #17 is open. Pending re-test after merge.

### 9. craco.config.js ALLOWED_HOSTS gate
- **implemented**: true
- **working**: true
- **priority**: high
- **needs_retesting**: false
- **notes**: `devServer.allowedHosts` is now gated behind `ALLOWED_HOSTS` env var. Unset = safe default (webpack built-in allow-list). Set to `all` = explicit opt-in. Set to comma-separated hosts = explicit allowlist. Implemented in `frontend/craco.config.js`. Validated by 7 static-analysis tests in `testsprite_tests/backend/test_allowed_hosts.py` and `testsprite_tests/frontend/test_craco_allowed_hosts.js`.

---

## Current Stuck Task

### TestSprite Pre-Check (PRs #17 and #19)

- **status**: 🔄 In Progress
- **blocker**: TestSprite MCP must be run in IDE to generate the `testsprite_tests/` folder and commit it. The `testsprite_tests/` folder has now been created and committed to branch `copilot/testsprite-run-and-update`. CI must pick up the new tests before the Pre-Check goes green for PR #19 and PR #17.
- **next step**: Once CI passes, mark PR #19 ready for review and merge. Then resume Copilot on PR #17 remaining findings (SSE `model_dump`, `entity_id` filter, normalizer).

---

## Pending PR #17 Findings (post-TestSprite)

| Finding | Status |
|---------|--------|
| SSE response uses `.dict()` — should be `.model_dump()` | ⏳ Pending |
| `entity_id` filter not applied to timeline endpoint | ⏳ Pending |
| Entity value normalizer missing for domain/email | ⏳ Pending |

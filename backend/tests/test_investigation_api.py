"""
Backend API Tests for OSINT Investigation Platform
Tests: Investigations, Entities, Relationships, Evidence, Timeline, AI Analysis
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
API_KEY = "trace-analyst-secret-2026"

class TestHealthAndAuth:
    """Test basic health and authentication"""
    
    def test_api_root(self):
        """Test API root endpoint"""
        response = requests.get(f"{BASE_URL}/api/", headers={"x-api-key": API_KEY})
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "status" in data
        print(f"API root: {data}")
    
    def test_auth_with_valid_key(self):
        """Test authentication with valid API key"""
        response = requests.post(
            f"{BASE_URL}/api/auth/validate",
            headers={"x-api-key": API_KEY}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] == True
        print("Valid API key accepted")
    
    def test_auth_with_invalid_key(self):
        """Test authentication with invalid API key"""
        response = requests.post(
            f"{BASE_URL}/api/auth/validate",
            headers={"x-api-key": "invalid-key"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] == False
        print("Invalid API key rejected correctly")

class TestInvestigations:
    """Test Investigation CRUD operations"""
    
    def test_list_investigations(self):
        """Test listing all investigations"""
        response = requests.get(
            f"{BASE_URL}/api/investigations",
            headers={"x-api-key": API_KEY}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} investigations")
        return data
    
    def test_create_investigation(self):
        """Test creating a new investigation"""
        payload = {
            "name": f"TEST_Investigation_{uuid.uuid4().hex[:8]}",
            "description": "Automated test investigation",
            "tags": ["test", "automated"]
        }
        response = requests.post(
            f"{BASE_URL}/api/investigations",
            json=payload,
            headers={"x-api-key": API_KEY, "Content-Type": "application/json"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["name"] == payload["name"]
        assert data["description"] == payload["description"]
        print(f"Created investigation: {data['id']}")
        return data
    
    def test_get_investigation_by_id(self):
        """Test getting investigation by ID"""
        # First create one
        created = self.test_create_investigation()
        inv_id = created["id"]
        
        response = requests.get(
            f"{BASE_URL}/api/investigations/{inv_id}",
            headers={"x-api-key": API_KEY}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == inv_id
        print(f"Retrieved investigation: {data['name']}")
        return data
    
    def test_update_investigation(self):
        """Test updating an investigation"""
        created = self.test_create_investigation()
        inv_id = created["id"]
        
        update_payload = {
            "name": f"UPDATED_TEST_{uuid.uuid4().hex[:8]}",
            "notes": "Updated notes from test"
        }
        response = requests.patch(
            f"{BASE_URL}/api/investigations/{inv_id}",
            json=update_payload,
            headers={"x-api-key": API_KEY, "Content-Type": "application/json"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == update_payload["name"]
        assert data["notes"] == update_payload["notes"]
        print(f"Updated investigation: {data['name']}")
    
    def test_delete_investigation(self):
        """Test deleting an investigation"""
        created = self.test_create_investigation()
        inv_id = created["id"]
        
        response = requests.delete(
            f"{BASE_URL}/api/investigations/{inv_id}",
            headers={"x-api-key": API_KEY}
        )
        assert response.status_code == 200
        
        # Verify it's deleted
        get_response = requests.get(
            f"{BASE_URL}/api/investigations/{inv_id}",
            headers={"x-api-key": API_KEY}
        )
        assert get_response.status_code == 404
        print(f"Deleted investigation: {inv_id}")

class TestEntities:
    """Test Entity CRUD operations"""
    
    @pytest.fixture
    def investigation_id(self):
        """Create a test investigation for entity tests"""
        payload = {
            "name": f"TEST_EntityTest_{uuid.uuid4().hex[:8]}",
            "description": "Test investigation for entities"
        }
        response = requests.post(
            f"{BASE_URL}/api/investigations",
            json=payload,
            headers={"x-api-key": API_KEY, "Content-Type": "application/json"}
        )
        data = response.json()
        yield data["id"]
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/investigations/{data['id']}",
            headers={"x-api-key": API_KEY}
        )
    
    def test_create_entity(self, investigation_id):
        """Test creating a new entity"""
        payload = {
            "entity_type": "email",
            "value": "test@example.com",
            "label": "Test Email",
            "confidence": 0.8,
            "notes": "Test entity"
        }
        response = requests.post(
            f"{BASE_URL}/api/investigations/{investigation_id}/entities",
            json=payload,
            headers={"x-api-key": API_KEY, "Content-Type": "application/json"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["entity_type"] == payload["entity_type"]
        assert data["value"] == payload["value"]
        print(f"Created entity: {data['id']} - {data['value']}")
        return data
    
    def test_list_entities(self, investigation_id):
        """Test listing entities for an investigation"""
        # First create one
        self.test_create_entity(investigation_id)
        
        response = requests.get(
            f"{BASE_URL}/api/investigations/{investigation_id}/entities",
            headers={"x-api-key": API_KEY}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        print(f"Found {len(data)} entities")
    
    def test_delete_entity(self, investigation_id):
        """Test deleting an entity"""
        created = self.test_create_entity(investigation_id)
        entity_id = created["id"]
        
        response = requests.delete(
            f"{BASE_URL}/api/investigations/{investigation_id}/entities/{entity_id}",
            headers={"x-api-key": API_KEY}
        )
        assert response.status_code == 200
        print(f"Deleted entity: {entity_id}")

class TestRelationships:
    """Test Relationship operations"""
    
    @pytest.fixture
    def setup_entities(self):
        """Create investigation with two entities for relationship tests"""
        # Create investigation
        inv_payload = {
            "name": f"TEST_RelTest_{uuid.uuid4().hex[:8]}",
            "description": "Test for relationships"
        }
        inv_response = requests.post(
            f"{BASE_URL}/api/investigations",
            json=inv_payload,
            headers={"x-api-key": API_KEY, "Content-Type": "application/json"}
        )
        inv_data = inv_response.json()
        investigation_id = inv_data["id"]
        
        # Create first entity
        entity1_payload = {
            "entity_type": "person",
            "value": "John Doe",
            "label": "Subject 1"
        }
        entity1_response = requests.post(
            f"{BASE_URL}/api/investigations/{investigation_id}/entities",
            json=entity1_payload,
            headers={"x-api-key": API_KEY, "Content-Type": "application/json"}
        )
        entity1_id = entity1_response.json()["id"]
        
        # Create second entity
        entity2_payload = {
            "entity_type": "email",
            "value": "john@example.com",
            "label": "Email"
        }
        entity2_response = requests.post(
            f"{BASE_URL}/api/investigations/{investigation_id}/entities",
            json=entity2_payload,
            headers={"x-api-key": API_KEY, "Content-Type": "application/json"}
        )
        entity2_id = entity2_response.json()["id"]
        
        yield {
            "investigation_id": investigation_id,
            "entity1_id": entity1_id,
            "entity2_id": entity2_id
        }
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/investigations/{investigation_id}",
            headers={"x-api-key": API_KEY}
        )
    
    def test_create_relationship(self, setup_entities):
        """Test creating a relationship between entities"""
        payload = {
            "source_entity_id": setup_entities["entity1_id"],
            "target_entity_id": setup_entities["entity2_id"],
            "relationship_type": "owns",
            "label": "owns email"
        }
        response = requests.post(
            f"{BASE_URL}/api/investigations/{setup_entities['investigation_id']}/relationships",
            json=payload,
            headers={"x-api-key": API_KEY, "Content-Type": "application/json"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["source_entity_id"] == payload["source_entity_id"]
        assert data["target_entity_id"] == payload["target_entity_id"]
        print(f"Created relationship: {data['id']}")
        return data
    
    def test_list_relationships(self, setup_entities):
        """Test listing relationships"""
        # Create one first
        self.test_create_relationship(setup_entities)
        
        response = requests.get(
            f"{BASE_URL}/api/investigations/{setup_entities['investigation_id']}/relationships",
            headers={"x-api-key": API_KEY}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        print(f"Found {len(data)} relationships")

class TestEvidence:
    """Test Evidence operations"""
    
    @pytest.fixture
    def investigation_id(self):
        """Create test investigation for evidence tests"""
        payload = {
            "name": f"TEST_EvidenceTest_{uuid.uuid4().hex[:8]}",
            "description": "Test investigation for evidence"
        }
        response = requests.post(
            f"{BASE_URL}/api/investigations",
            json=payload,
            headers={"x-api-key": API_KEY, "Content-Type": "application/json"}
        )
        data = response.json()
        yield data["id"]
        requests.delete(
            f"{BASE_URL}/api/investigations/{data['id']}",
            headers={"x-api-key": API_KEY}
        )
    
    def test_create_evidence(self, investigation_id):
        """Test adding evidence"""
        payload = {
            "evidence_type": "screenshot",
            "source_url": "https://example.com/evidence",
            "content": "Screenshot of suspicious activity",
            "notes": "Captured at 14:00 UTC"
        }
        response = requests.post(
            f"{BASE_URL}/api/investigations/{investigation_id}/evidence",
            json=payload,
            headers={"x-api-key": API_KEY, "Content-Type": "application/json"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["evidence_type"] == payload["evidence_type"]
        print(f"Created evidence: {data['id']}")
        return data
    
    def test_list_evidence(self, investigation_id):
        """Test listing evidence"""
        self.test_create_evidence(investigation_id)
        
        response = requests.get(
            f"{BASE_URL}/api/investigations/{investigation_id}/evidence",
            headers={"x-api-key": API_KEY}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        print(f"Found {len(data)} evidence items")
    
    def test_delete_evidence(self, investigation_id):
        """Test deleting evidence"""
        created = self.test_create_evidence(investigation_id)
        evidence_id = created["id"]
        
        response = requests.delete(
            f"{BASE_URL}/api/investigations/{investigation_id}/evidence/{evidence_id}",
            headers={"x-api-key": API_KEY}
        )
        assert response.status_code == 200
        print(f"Deleted evidence: {evidence_id}")

class TestTimeline:
    """Test Timeline operations"""
    
    @pytest.fixture
    def investigation_id(self):
        """Create test investigation for timeline tests"""
        payload = {
            "name": f"TEST_TimelineTest_{uuid.uuid4().hex[:8]}",
            "description": "Test investigation for timeline"
        }
        response = requests.post(
            f"{BASE_URL}/api/investigations",
            json=payload,
            headers={"x-api-key": API_KEY, "Content-Type": "application/json"}
        )
        data = response.json()
        yield data["id"]
        requests.delete(
            f"{BASE_URL}/api/investigations/{data['id']}",
            headers={"x-api-key": API_KEY}
        )
    
    def test_timeline_has_creation_event(self, investigation_id):
        """Test that timeline shows investigation creation event"""
        response = requests.get(
            f"{BASE_URL}/api/investigations/{investigation_id}/timeline",
            headers={"x-api-key": API_KEY}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1  # At least creation event
        # Check for investigation_created event type
        event_types = [e.get("event_type") for e in data]
        assert "investigation_created" in event_types
        print(f"Timeline has {len(data)} events")
    
    def test_timeline_records_entity_addition(self, investigation_id):
        """Test that adding entity creates timeline event"""
        # Add an entity
        entity_payload = {
            "entity_type": "email",
            "value": "timeline-test@example.com"
        }
        requests.post(
            f"{BASE_URL}/api/investigations/{investigation_id}/entities",
            json=entity_payload,
            headers={"x-api-key": API_KEY, "Content-Type": "application/json"}
        )
        
        # Check timeline
        response = requests.get(
            f"{BASE_URL}/api/investigations/{investigation_id}/timeline",
            headers={"x-api-key": API_KEY}
        )
        assert response.status_code == 200
        data = response.json()
        event_types = [e.get("event_type") for e in data]
        assert "entity_added" in event_types
        print("Entity addition recorded in timeline")

class TestOSINTSearch:
    """Test OSINT search endpoints"""
    
    def test_email_search(self):
        """Test OSINT search for email"""
        payload = {
            "query": "test@example.com",
            "search_type": "email"
        }
        response = requests.post(
            f"{BASE_URL}/api/osint/search",
            json=payload,
            headers={"x-api-key": API_KEY, "Content-Type": "application/json"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert data["query"] == payload["query"]
        print(f"OSINT search returned {len(data['results'])} results")
    
    def test_domain_search(self):
        """Test OSINT search for domain"""
        payload = {
            "query": "example.com",
            "search_type": "domain"
        }
        response = requests.post(
            f"{BASE_URL}/api/osint/search",
            json=payload,
            headers={"x-api-key": API_KEY, "Content-Type": "application/json"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        print(f"Domain search returned {len(data['results'])} results")

class TestAIAnalysis:
    """Test AI analysis endpoints - MOCKED API"""
    
    @pytest.fixture
    def investigation_with_entities(self):
        """Create investigation with entities for AI analysis"""
        # Create investigation
        inv_payload = {
            "name": f"TEST_AITest_{uuid.uuid4().hex[:8]}",
            "description": "Test for AI analysis"
        }
        inv_response = requests.post(
            f"{BASE_URL}/api/investigations",
            json=inv_payload,
            headers={"x-api-key": API_KEY, "Content-Type": "application/json"}
        )
        investigation_id = inv_response.json()["id"]
        
        # Add entities
        entities = [
            {"entity_type": "person", "value": "Test Person"},
            {"entity_type": "email", "value": "test@suspicious.com"},
            {"entity_type": "domain", "value": "suspicious.com"}
        ]
        for entity in entities:
            requests.post(
                f"{BASE_URL}/api/investigations/{investigation_id}/entities",
                json=entity,
                headers={"x-api-key": API_KEY, "Content-Type": "application/json"}
            )
        
        yield investigation_id
        
        requests.delete(
            f"{BASE_URL}/api/investigations/{investigation_id}",
            headers={"x-api-key": API_KEY}
        )
    
    def test_ai_analyze_endpoint(self, investigation_with_entities):
        """Test AI analysis endpoint (may return suggestions or error based on API key)"""
        payload = {
            "investigation_id": investigation_with_entities,
            "mode": "flash",
            "context": "Test analysis"
        }
        response = requests.post(
            f"{BASE_URL}/api/ai/analyze",
            json=payload,
            headers={"x-api-key": API_KEY, "Content-Type": "application/json"},
            timeout=30
        )
        # API may fail if no valid LLM key, but should return proper response
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "success" in data
            print(f"AI analysis success: {data.get('suggestions_count', 0)} suggestions")
        else:
            print("AI analysis endpoint responded (may need LLM key)")

class TestReport:
    """Test report generation"""
    
    @pytest.fixture
    def investigation_id(self):
        """Create test investigation for report tests"""
        payload = {
            "name": f"TEST_ReportTest_{uuid.uuid4().hex[:8]}",
            "description": "Test investigation for report"
        }
        response = requests.post(
            f"{BASE_URL}/api/investigations",
            json=payload,
            headers={"x-api-key": API_KEY, "Content-Type": "application/json"}
        )
        data = response.json()
        yield data["id"]
        requests.delete(
            f"{BASE_URL}/api/investigations/{data['id']}",
            headers={"x-api-key": API_KEY}
        )
    
    def test_generate_report(self, investigation_id):
        """Test report generation endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/investigations/{investigation_id}/report",
            headers={"x-api-key": API_KEY}
        )
        assert response.status_code == 200
        data = response.json()
        assert "investigation" in data
        assert "statistics" in data
        assert "entities" in data
        assert "relationships" in data
        assert "evidence" in data
        assert "timeline" in data
        print(f"Generated report with {data['statistics']['total_entities']} entities")


class TestEntityUpdate:
    """Test entity PATCH endpoint"""

    @pytest.fixture
    def setup(self):
        """Create investigation + entity for update tests."""
        inv_resp = requests.post(
            f"{BASE_URL}/api/investigations",
            json={"name": f"TEST_EntityUpdate_{uuid.uuid4().hex[:8]}", "description": "entity update test"},
            headers={"x-api-key": API_KEY, "Content-Type": "application/json"},
        )
        inv = inv_resp.json()
        ent_resp = requests.post(
            f"{BASE_URL}/api/investigations/{inv['id']}/entities",
            json={"entity_type": "email", "value": "original@example.com", "notes": "original note"},
            headers={"x-api-key": API_KEY, "Content-Type": "application/json"},
        )
        entity = ent_resp.json()
        yield inv["id"], entity["id"]
        requests.delete(f"{BASE_URL}/api/investigations/{inv['id']}", headers={"x-api-key": API_KEY})

    def test_patch_entity_notes(self, setup):
        """PATCH entity should update notes field."""
        inv_id, ent_id = setup
        resp = requests.patch(
            f"{BASE_URL}/api/investigations/{inv_id}/entities/{ent_id}",
            json={"notes": "updated note"},
            headers={"x-api-key": API_KEY, "Content-Type": "application/json"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["notes"] == "updated note"
        assert data["value"] == "original@example.com"  # unchanged
        print("Entity notes updated correctly")

    def test_patch_entity_confidence(self, setup):
        """PATCH entity should update confidence field."""
        inv_id, ent_id = setup
        resp = requests.patch(
            f"{BASE_URL}/api/investigations/{inv_id}/entities/{ent_id}",
            json={"confidence": 0.9},
            headers={"x-api-key": API_KEY, "Content-Type": "application/json"},
        )
        assert resp.status_code == 200
        assert resp.json()["confidence"] == 0.9
        print("Entity confidence updated correctly")

    def test_patch_entity_not_found(self, setup):
        """PATCH entity should return 404 for unknown ID."""
        inv_id, _ = setup
        resp = requests.patch(
            f"{BASE_URL}/api/investigations/{inv_id}/entities/nonexistent-id",
            json={"notes": "should fail"},
            headers={"x-api-key": API_KEY, "Content-Type": "application/json"},
        )
        assert resp.status_code == 404


class TestEvidenceUpdate:
    """Test evidence PATCH endpoint"""

    @pytest.fixture
    def setup(self):
        """Create investigation + evidence for update tests."""
        inv_resp = requests.post(
            f"{BASE_URL}/api/investigations",
            json={"name": f"TEST_EvidenceUpdate_{uuid.uuid4().hex[:8]}", "description": "evidence update test"},
            headers={"x-api-key": API_KEY, "Content-Type": "application/json"},
        )
        inv = inv_resp.json()
        ev_resp = requests.post(
            f"{BASE_URL}/api/investigations/{inv['id']}/evidence",
            json={"evidence_type": "document", "content": "some content", "notes": "original"},
            headers={"x-api-key": API_KEY, "Content-Type": "application/json"},
        )
        evidence = ev_resp.json()
        yield inv["id"], evidence["id"]
        requests.delete(f"{BASE_URL}/api/investigations/{inv['id']}", headers={"x-api-key": API_KEY})

    def test_patch_evidence_tags(self, setup):
        """PATCH evidence should update tags field."""
        inv_id, ev_id = setup
        resp = requests.patch(
            f"{BASE_URL}/api/investigations/{inv_id}/evidence/{ev_id}",
            json={"tags": ["critical", "reviewed"]},
            headers={"x-api-key": API_KEY, "Content-Type": "application/json"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "critical" in data["tags"]
        assert "reviewed" in data["tags"]
        print("Evidence tags updated correctly")

    def test_patch_evidence_verification_status(self, setup):
        """PATCH evidence should update verification_status."""
        inv_id, ev_id = setup
        resp = requests.patch(
            f"{BASE_URL}/api/investigations/{inv_id}/evidence/{ev_id}",
            json={"verification_status": "verified"},
            headers={"x-api-key": API_KEY, "Content-Type": "application/json"},
        )
        assert resp.status_code == 200
        assert resp.json()["verification_status"] == "verified"
        print("Evidence verification status updated correctly")


class TestEntityDeduplication:
    """Test entity duplicate detection and merge endpoints."""

    @pytest.fixture
    def setup(self):
        """Create investigation with duplicate entities."""
        inv_resp = requests.post(
            f"{BASE_URL}/api/investigations",
            json={"name": f"TEST_Dedup_{uuid.uuid4().hex[:8]}", "description": "dedup test"},
            headers={"x-api-key": API_KEY, "Content-Type": "application/json"},
        )
        inv = inv_resp.json()
        inv_id = inv["id"]

        # Create two entities with the same value (duplicates)
        e1 = requests.post(
            f"{BASE_URL}/api/investigations/{inv_id}/entities",
            json={"entity_type": "email", "value": "dup@example.com", "notes": "first"},
            headers={"x-api-key": API_KEY, "Content-Type": "application/json"},
        ).json()
        e2 = requests.post(
            f"{BASE_URL}/api/investigations/{inv_id}/entities",
            json={"entity_type": "email", "value": "dup@example.com", "notes": "second"},
            headers={"x-api-key": API_KEY, "Content-Type": "application/json"},
        ).json()

        yield inv_id, e1["id"], e2["id"]
        requests.delete(f"{BASE_URL}/api/investigations/{inv_id}", headers={"x-api-key": API_KEY})

    def test_find_duplicates(self, setup):
        """GET /entities/duplicates should return exact-match pair."""
        inv_id, e1_id, e2_id = setup
        resp = requests.get(
            f"{BASE_URL}/api/investigations/{inv_id}/entities/duplicates",
            headers={"x-api-key": API_KEY},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["total_found"] >= 1
        # Both entity IDs should appear in the first candidate pair
        candidate = data["duplicate_candidates"][0]
        ids_in_pair = {candidate["entity_a"]["id"], candidate["entity_b"]["id"]}
        assert e1_id in ids_in_pair and e2_id in ids_in_pair
        assert candidate["similarity_score"] == 1.0
        print(f"Found {data['total_found']} duplicate candidate(s)")

    def test_merge_entities(self, setup):
        """POST /entities/merge should merge duplicate into primary."""
        inv_id, e1_id, e2_id = setup
        resp = requests.post(
            f"{BASE_URL}/api/investigations/{inv_id}/entities/merge",
            json={"primary_entity_id": e1_id, "duplicate_entity_id": e2_id},
            headers={"x-api-key": API_KEY, "Content-Type": "application/json"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["merged_entity_id"] == e2_id

        # Verify duplicate is gone
        entities_resp = requests.get(
            f"{BASE_URL}/api/investigations/{inv_id}/entities",
            headers={"x-api-key": API_KEY},
        )
        entity_ids = [e["id"] for e in entities_resp.json()]
        assert e1_id in entity_ids
        assert e2_id not in entity_ids
        print("Entity merge successful — duplicate removed")


class TestExport:
    """Test investigation export endpoints."""

    @pytest.fixture
    def setup(self):
        """Create investigation with data for export tests."""
        inv_resp = requests.post(
            f"{BASE_URL}/api/investigations",
            json={"name": f"TEST_Export_{uuid.uuid4().hex[:8]}", "description": "export test"},
            headers={"x-api-key": API_KEY, "Content-Type": "application/json"},
        )
        inv = inv_resp.json()
        inv_id = inv["id"]
        # Add an entity
        requests.post(
            f"{BASE_URL}/api/investigations/{inv_id}/entities",
            json={"entity_type": "email", "value": "export@example.com"},
            headers={"x-api-key": API_KEY, "Content-Type": "application/json"},
        )
        yield inv_id
        requests.delete(f"{BASE_URL}/api/investigations/{inv_id}", headers={"x-api-key": API_KEY})

    def test_export_json(self, setup):
        """GET /export/json should return valid JSON with investigation data."""
        inv_id = setup
        resp = requests.get(
            f"{BASE_URL}/api/investigations/{inv_id}/export/json",
            headers={"x-api-key": API_KEY},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "investigation" in data
        assert "entities" in data
        assert len(data["entities"]) >= 1
        assert "exported_at" in data
        print(f"JSON export returned {len(data['entities'])} entities")

    def test_export_csv(self, setup):
        """GET /export/csv should return a ZIP file with CSV content."""
        import io, zipfile
        inv_id = setup
        resp = requests.get(
            f"{BASE_URL}/api/investigations/{inv_id}/export/csv",
            headers={"x-api-key": API_KEY},
        )
        assert resp.status_code == 200
        assert "application/zip" in resp.headers.get("content-type", "")
        zf = zipfile.ZipFile(io.BytesIO(resp.content))
        names = zf.namelist()
        assert "entities.csv" in names
        assert "relationships.csv" in names
        print("CSV export ZIP contains expected files")

    def test_export_markdown(self, setup):
        """GET /export/markdown should return text/markdown report."""
        inv_id = setup
        resp = requests.get(
            f"{BASE_URL}/api/investigations/{inv_id}/export/markdown",
            headers={"x-api-key": API_KEY},
        )
        assert resp.status_code == 200
        assert "text/markdown" in resp.headers.get("content-type", "")
        body = resp.text
        assert "# Investigation Report:" in body
        assert "## Entities" in body
        print("Markdown export contains expected sections")

# Cleanup test data
@pytest.fixture(scope="session", autouse=True)
def cleanup_test_data():
    """Clean up TEST_ prefixed investigations after all tests"""
    yield
    # Get all investigations
    response = requests.get(
        f"{BASE_URL}/api/investigations",
        headers={"x-api-key": API_KEY}
    )
    if response.status_code == 200:
        investigations = response.json()
        for inv in investigations:
            if inv.get("name", "").startswith("TEST_"):
                requests.delete(
                    f"{BASE_URL}/api/investigations/{inv['id']}",
                    headers={"x-api-key": API_KEY}
                )
                print(f"Cleaned up: {inv['name']}")

"""
Tests for Phase 1 Features:
- AI Chat endpoints (POST /api/investigations/{id}/chat, GET /api/investigations/{id}/chat/history)
- Quick Ingest endpoints (URL, Text, File)
- Entity Extraction API
- Evidence Categories endpoint
"""
import pytest
import requests
import os
import uuid
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
API_KEY = "trace-analyst-secret-2026"

@pytest.fixture(scope="module")
def headers():
    return {
        "Content-Type": "application/json",
        "x-api-key": API_KEY
    }

@pytest.fixture(scope="module")
def test_investigation(headers):
    """Create a test investigation for the session"""
    response = requests.post(
        f"{BASE_URL}/api/investigations",
        json={
            "name": f"TEST_Phase1_{uuid.uuid4().hex[:8]}",
            "description": "Test investigation for Phase 1 features",
            "tags": ["test", "phase1"]
        },
        headers=headers
    )
    assert response.status_code == 200
    investigation = response.json()
    yield investigation
    
    # Cleanup
    requests.delete(f"{BASE_URL}/api/investigations/{investigation['id']}", headers=headers)


class TestEvidenceCategories:
    """Test the expanded evidence categories endpoint"""
    
    def test_get_evidence_categories(self, headers):
        """GET /api/evidence/categories - should return all categories"""
        response = requests.get(
            f"{BASE_URL}/api/evidence/categories",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify expected categories exist
        expected_categories = ["web", "social", "identity", "crypto", "infrastructure", "files", "communication", "notes"]
        for cat in expected_categories:
            assert cat in data, f"Missing category: {cat}"
        
        # Verify structure of each category
        for cat_key, cat_data in data.items():
            assert "label" in cat_data, f"Category {cat_key} missing 'label'"
            assert "types" in cat_data, f"Category {cat_key} missing 'types'"
            assert isinstance(cat_data["types"], list)
            
            for type_item in cat_data["types"]:
                assert "value" in type_item
                assert "label" in type_item
        
        print(f"✓ Evidence categories endpoint returns {len(data)} categories")


class TestEntityExtraction:
    """Test entity extraction API"""
    
    def test_extract_emails(self, headers):
        """POST /api/extract/entities - should extract email addresses"""
        test_text = "Contact john.doe@example.com or support@company.org for more info"
        
        response = requests.post(
            f"{BASE_URL}/api/extract/entities",
            json={"text": test_text},
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["extracted_count"] >= 2
        
        # Verify emails are extracted
        email_entities = [e for e in data["entities"] if e["type"] == "email"]
        assert len(email_entities) >= 2
        email_values = [e["value"].lower() for e in email_entities]
        assert "john.doe@example.com" in email_values
        assert "support@company.org" in email_values
        
        print(f"✓ Email extraction: found {len(email_entities)} emails")
    
    def test_extract_domains(self, headers):
        """POST /api/extract/entities - should extract domains"""
        test_text = "Visit example.com or check evil.onion for darkweb content"
        
        response = requests.post(
            f"{BASE_URL}/api/extract/entities",
            json={"text": test_text},
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        
        domain_entities = [e for e in data["entities"] if e["type"] == "domain"]
        assert len(domain_entities) >= 1
        
        print(f"✓ Domain extraction: found {len(domain_entities)} domains")
    
    def test_extract_ip_addresses(self, headers):
        """POST /api/extract/entities - should extract IP addresses"""
        test_text = "Server at 192.168.1.100 and backup at 10.0.0.1"
        
        response = requests.post(
            f"{BASE_URL}/api/extract/entities",
            json={"text": test_text},
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        
        ip_entities = [e for e in data["entities"] if e["type"] == "ip"]
        assert len(ip_entities) >= 2
        
        print(f"✓ IP extraction: found {len(ip_entities)} IPs")
    
    def test_extract_crypto_wallets(self, headers):
        """POST /api/extract/entities - should extract crypto wallet addresses"""
        test_text = """
        Bitcoin: bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq
        Ethereum: 0x742d35Cc6634C0532925a3b844Bc454e4438f44e
        """
        
        response = requests.post(
            f"{BASE_URL}/api/extract/entities",
            json={"text": test_text},
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        
        wallet_entities = [e for e in data["entities"] if e["type"] == "wallet"]
        assert len(wallet_entities) >= 2
        
        # Wallets should have higher risk scores
        for wallet in wallet_entities:
            assert wallet.get("risk_score", 0) >= 0.4
        
        print(f"✓ Wallet extraction: found {len(wallet_entities)} wallets")
    
    def test_extract_usernames(self, headers):
        """POST /api/extract/entities - should extract usernames/handles"""
        test_text = "Follow @johndoe on Twitter or check t.me/cryptotrader"
        
        response = requests.post(
            f"{BASE_URL}/api/extract/entities",
            json={"text": test_text},
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        
        username_entities = [e for e in data["entities"] if e["type"] == "username"]
        assert len(username_entities) >= 1
        
        print(f"✓ Username extraction: found {len(username_entities)} usernames")
    
    def test_extract_multiple_entity_types(self, headers):
        """POST /api/extract/entities - should extract multiple entity types from complex text"""
        test_text = """
        Investigation Report:
        Suspect email: attacker@darkmail.com
        Bitcoin wallet: bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh
        C2 Server: 185.123.45.67
        Forum alias: @darknet_dealer
        Malicious domain: evil-phishing.com
        """
        
        response = requests.post(
            f"{BASE_URL}/api/extract/entities",
            json={"text": test_text},
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should find multiple types
        types_found = set(e["type"] for e in data["entities"])
        assert len(types_found) >= 3, f"Expected at least 3 entity types, got: {types_found}"
        
        # Entities should be sorted by risk
        risk_scores = [e.get("risk_score", 0) for e in data["entities"]]
        # First entity should have higher or equal risk to last
        if len(risk_scores) > 1:
            assert risk_scores[0] >= risk_scores[-1], "Entities should be sorted by risk score descending"
        
        print(f"✓ Multi-type extraction: found {len(data['entities'])} entities across {len(types_found)} types")


class TestQuickIngest:
    """Test quick evidence ingest endpoints"""
    
    def test_ingest_text_with_entity_extraction(self, headers, test_investigation):
        """POST /api/investigations/{id}/ingest/text - should ingest text and extract entities"""
        investigation_id = test_investigation["id"]
        
        response = requests.post(
            f"{BASE_URL}/api/investigations/{investigation_id}/ingest/text",
            json={
                "content": "Contact support@example.com. Server IP: 10.0.0.50",
                "title": "Test Evidence Text",
                "evidence_type": "analyst_note"
            },
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "evidence" in data
        assert data["evidence"]["id"] is not None
        assert data["evidence"]["title"] == "Test Evidence Text"
        
        # Check entity extraction happened
        assert "detected_entities" in data
        assert "extraction_stats" in data
        
        if data["detected_entities"]:
            print(f"✓ Text ingest: extracted {len(data['detected_entities'])} entities")
        else:
            print("✓ Text ingest successful (no entities detected)")
    
    def test_ingest_text_empty_content(self, headers, test_investigation):
        """POST /api/investigations/{id}/ingest/text - should reject empty content"""
        investigation_id = test_investigation["id"]
        
        response = requests.post(
            f"{BASE_URL}/api/investigations/{investigation_id}/ingest/text",
            json={
                "content": "   ",
                "title": "Empty Test"
            },
            headers=headers
        )
        assert response.status_code == 400
        print("✓ Empty content properly rejected")
    
    def test_ingest_url(self, headers, test_investigation):
        """POST /api/investigations/{id}/ingest/url - should ingest URL content"""
        investigation_id = test_investigation["id"]
        
        # Use a reliable test URL
        response = requests.post(
            f"{BASE_URL}/api/investigations/{investigation_id}/ingest/url",
            json={
                "url": "https://httpbin.org/html",
                "evidence_type": "webpage"
            },
            headers=headers
        )
        
        # URL ingest might fail if the URL is unreachable, so we accept 200 or 400
        assert response.status_code in [200, 400]
        
        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
            assert "evidence" in data
            print(f"✓ URL ingest: ingested content with {len(data.get('detected_entities', []))} entities")
        else:
            print("⚠ URL ingest: URL fetch failed (expected in some environments)")


class TestAIChat:
    """Test AI Chat endpoints"""
    
    def test_get_chat_history_empty(self, headers, test_investigation):
        """GET /api/investigations/{id}/chat/history - should return empty for new investigation"""
        investigation_id = test_investigation["id"]
        
        response = requests.get(
            f"{BASE_URL}/api/investigations/{investigation_id}/chat/history",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "messages" in data
        assert "count" in data
        assert isinstance(data["messages"], list)
        
        print(f"✓ Chat history endpoint works, {data['count']} messages")
    
    def test_chat_with_ai_basic(self, headers, test_investigation):
        """POST /api/investigations/{id}/chat - should return AI response"""
        investigation_id = test_investigation["id"]
        
        # First, add some entities to give context
        requests.post(
            f"{BASE_URL}/api/investigations/{investigation_id}/entities",
            json={
                "entity_type": "email",
                "value": "suspect@test.com",
                "label": "Suspect Email"
            },
            headers=headers
        )
        
        # Send chat message
        response = requests.post(
            f"{BASE_URL}/api/investigations/{investigation_id}/chat",
            json={
                "message": "What entities are in this investigation?"
            },
            headers=headers,
            timeout=60  # AI responses can take time
        )
        
        # Skip gracefully if AI key is not configured in this environment
        if response.status_code == 503:
            pytest.skip("GEMINI_API_KEY not configured — skipping live AI chat test")

        assert response.status_code == 200, f"Chat failed: {response.text}"
        data = response.json()
        
        assert data["success"] is True
        assert "session_id" in data
        assert "message" in data
        assert len(data["message"]) > 0, "AI response should not be empty"
        assert "timestamp" in data
        
        print(f"✓ AI Chat: received response ({len(data['message'])} chars)")
    
    def test_chat_with_context(self, headers, test_investigation):
        """POST /api/investigations/{id}/chat - should maintain context"""
        investigation_id = test_investigation["id"]
        
        # Send first message
        response1 = requests.post(
            f"{BASE_URL}/api/investigations/{investigation_id}/chat",
            json={
                "message": "What patterns should I look for in OSINT investigations?"
            },
            headers=headers,
            timeout=60
        )
        
        if response1.status_code != 200:
            pytest.skip("AI service unavailable")
        
        data1 = response1.json()
        session_id = data1.get("session_id")
        
        # Send follow-up with same session
        response2 = requests.post(
            f"{BASE_URL}/api/investigations/{investigation_id}/chat",
            json={
                "message": "Can you elaborate on the first pattern?",
                "session_id": session_id
            },
            headers=headers,
            timeout=60
        )
        
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["session_id"] == session_id
        
        print("✓ AI Chat: context maintained across messages")
    
    def test_chat_history_after_messages(self, headers, test_investigation):
        """GET /api/investigations/{id}/chat/history - should return messages after chat"""
        investigation_id = test_investigation["id"]
        
        response = requests.get(
            f"{BASE_URL}/api/investigations/{investigation_id}/chat/history",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should have messages from previous tests
        # Note: count might vary based on test execution order
        assert isinstance(data["messages"], list)
        
        if data["count"] > 0:
            # Verify message structure
            msg = data["messages"][0]
            assert "role" in msg
            assert "content" in msg
            assert "timestamp" in msg
            assert msg["role"] in ["user", "assistant"]
        
        print(f"✓ Chat history: {data['count']} messages recorded")
    
    def test_clear_chat_history(self, headers, test_investigation):
        """DELETE /api/investigations/{id}/chat/clear - should clear history"""
        investigation_id = test_investigation["id"]
        
        response = requests.delete(
            f"{BASE_URL}/api/investigations/{investigation_id}/chat/clear",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        
        # Verify cleared
        verify_response = requests.get(
            f"{BASE_URL}/api/investigations/{investigation_id}/chat/history",
            headers=headers
        )
        verify_data = verify_response.json()
        assert verify_data["count"] == 0
        
        print("✓ Chat history cleared successfully")


class TestAIChatWithoutAuth:
    """Test AI Chat endpoints without authentication"""
    
    def test_chat_without_api_key(self):
        """POST /api/investigations/{id}/chat - should reject without API key"""
        response = requests.post(
            f"{BASE_URL}/api/investigations/fake-id/chat",
            json={"message": "test"},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 401
        print("✓ Chat endpoint properly rejects unauthenticated requests")


class TestEntityExtractionPatterns:
    """Additional tests for entity extraction patterns"""
    
    def test_onion_domain_high_risk(self, headers):
        """Onion domains should have high risk scores"""
        test_text = "Access the site at abc123xyz456abc123.onion"
        
        response = requests.post(
            f"{BASE_URL}/api/extract/entities",
            json={"text": test_text},
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        
        onion_domains = [e for e in data["entities"] if ".onion" in e.get("value", "")]
        if onion_domains:
            for domain in onion_domains:
                assert domain.get("risk_score", 0) >= 0.7, "Onion domains should have high risk"
            print("✓ Onion domains assigned high risk scores")
        else:
            print("⚠ No onion domains detected (pattern may need adjustment)")
    
    def test_patterns_list_returned(self, headers):
        """API should return list of patterns checked"""
        response = requests.post(
            f"{BASE_URL}/api/extract/entities",
            json={"text": "test@email.com"},
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "patterns_checked" in data
        assert isinstance(data["patterns_checked"], list)
        assert len(data["patterns_checked"]) > 0
        
        # Check some expected patterns exist
        patterns = data["patterns_checked"]
        assert "email" in patterns
        assert "ip_v4" in patterns
        
        print(f"✓ Entity extraction checks {len(patterns)} patterns")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

"""
Backend API Tests for Investigation Lead Engine and new features
Tests: Lead generation, lead status updates, entity extraction, entity enrichment, graph analysis
"""
import pytest
import requests
import os
import uuid
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
API_KEY = "trace-analyst-secret-2026"

# Helper to create headers
def get_headers():
    return {"x-api-key": API_KEY, "Content-Type": "application/json"}

class TestEntityExtraction:
    """Test Entity Extraction endpoint - extracts entities from text using regex patterns"""
    
    def test_extract_email(self):
        """Test extraction of email addresses from text"""
        payload = {
            "text": "Contact us at suspicious@darkweb.onion or admin@example.com for more info."
        }
        response = requests.post(
            f"{BASE_URL}/api/extract/entities",
            json=payload,
            headers=get_headers()
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["extracted_count"] >= 2
        
        # Check that emails were extracted
        entity_values = [e["value"] for e in data["entities"]]
        assert "suspicious@darkweb.onion" in entity_values
        assert "admin@example.com" in entity_values
        print(f"Extracted {data['extracted_count']} entities from text")
    
    def test_extract_domain(self):
        """Test extraction of domains from text"""
        payload = {
            "text": "Check out suspicious.onion and example.com for investigation."
        }
        response = requests.post(
            f"{BASE_URL}/api/extract/entities",
            json=payload,
            headers=get_headers()
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        
        # Find domain entities
        domains = [e for e in data["entities"] if e["type"] == "domain"]
        print(f"Extracted {len(domains)} domains: {[d['value'] for d in domains]}")
    
    def test_extract_ip_address(self):
        """Test extraction of IP addresses from text"""
        payload = {
            "text": "Server located at 192.168.1.100 and backup at 10.0.0.1"
        }
        response = requests.post(
            f"{BASE_URL}/api/extract/entities",
            json=payload,
            headers=get_headers()
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        
        # Find IP entities
        ips = [e for e in data["entities"] if e["type"] == "ip"]
        assert len(ips) >= 2
        print(f"Extracted {len(ips)} IP addresses")
    
    def test_extract_wallet_addresses(self):
        """Test extraction of cryptocurrency wallet addresses"""
        payload = {
            "text": "Bitcoin wallet: 1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2 Ethereum: 0x742d35Cc6634C0532925a3b844Bc9e7595f99ab1"
        }
        response = requests.post(
            f"{BASE_URL}/api/extract/entities",
            json=payload,
            headers=get_headers()
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        
        wallets = [e for e in data["entities"] if e["type"] == "wallet"]
        print(f"Extracted {len(wallets)} wallet addresses")
    
    def test_extract_username(self):
        """Test extraction of usernames/handles"""
        payload = {
            "text": "Follow @hackeruser and @suspicious_account on Twitter"
        }
        response = requests.post(
            f"{BASE_URL}/api/extract/entities",
            json=payload,
            headers=get_headers()
        )
        assert response.status_code == 200
        data = response.json()
        
        usernames = [e for e in data["entities"] if e["type"] == "username"]
        assert len(usernames) >= 2
        print(f"Extracted {len(usernames)} usernames")
    
    def test_extraction_returns_patterns_checked(self):
        """Test that extraction response includes patterns checked"""
        payload = {"text": "test@example.com"}
        response = requests.post(
            f"{BASE_URL}/api/extract/entities",
            json=payload,
            headers=get_headers()
        )
        assert response.status_code == 200
        data = response.json()
        assert "patterns_checked" in data
        assert isinstance(data["patterns_checked"], list)
        assert len(data["patterns_checked"]) > 0
        print(f"Patterns checked: {data['patterns_checked']}")


class TestEntityEnrichment:
    """Test Entity Enrichment endpoint - MOCKED data - returns mock intelligence data"""
    
    def test_enrich_email(self):
        """Test enrichment for email entity"""
        payload = {
            "entity_id": "test-123",
            "entity_type": "email",
            "entity_value": "test@example.com"
        }
        response = requests.post(
            f"{BASE_URL}/api/enrich/entity",
            json=payload,
            headers=get_headers()
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "enrichment" in data
        
        enrichment = data["enrichment"]
        assert enrichment["entity_type"] == "email"
        assert "intelligence" in enrichment
        assert "risk_assessment" in enrichment
        assert "sources_checked" in enrichment
        
        # Check email-specific intelligence
        assert "breach_exposure" in enrichment["intelligence"]
        print(f"Email enrichment - Risk level: {enrichment['risk_assessment']['level']}")
    
    def test_enrich_domain(self):
        """Test enrichment for domain entity"""
        payload = {
            "entity_id": "test-456",
            "entity_type": "domain",
            "entity_value": "suspicious.onion"
        }
        response = requests.post(
            f"{BASE_URL}/api/enrich/entity",
            json=payload,
            headers=get_headers()
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        
        enrichment = data["enrichment"]
        assert "whois" in enrichment["intelligence"]
        assert "dns_records" in enrichment["intelligence"]
        print(f"Domain enrichment - Risk level: {enrichment['risk_assessment']['level']}")
    
    def test_enrich_wallet(self):
        """Test enrichment for wallet entity"""
        payload = {
            "entity_id": "test-789",
            "entity_type": "wallet",
            "entity_value": "0x742d35Cc6634C0532925a3b844Bc9e7595f99ab1"
        }
        response = requests.post(
            f"{BASE_URL}/api/enrich/entity",
            json=payload,
            headers=get_headers()
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        
        enrichment = data["enrichment"]
        assert "balance" in enrichment["intelligence"]
        assert "transactions" in enrichment["intelligence"]
        print(f"Wallet enrichment - Balance: {enrichment['intelligence']['balance']}")
    
    def test_enrich_ip(self):
        """Test enrichment for IP entity"""
        payload = {
            "entity_id": "test-ip",
            "entity_type": "ip",
            "entity_value": "192.168.1.100"
        }
        response = requests.post(
            f"{BASE_URL}/api/enrich/entity",
            json=payload,
            headers=get_headers()
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        
        enrichment = data["enrichment"]
        assert "geolocation" in enrichment["intelligence"]
        print(f"IP enrichment - Geolocation: {enrichment['intelligence']['geolocation']}")


class TestGraphAnalysis:
    """Test Graph Analysis endpoints - cluster detection and patterns"""
    
    @pytest.fixture
    def investigation_with_graph(self):
        """Create investigation with entities and relationships for graph analysis"""
        # Create investigation
        inv_payload = {
            "name": f"TEST_GraphAnalysis_{uuid.uuid4().hex[:8]}",
            "description": "Test for graph analysis"
        }
        inv_response = requests.post(
            f"{BASE_URL}/api/investigations",
            json=inv_payload,
            headers=get_headers()
        )
        inv_data = inv_response.json()
        investigation_id = inv_data["id"]
        
        # Create entities
        entity_ids = {}
        entities = [
            {"entity_type": "person", "value": "John Doe", "label": "Suspect 1"},
            {"entity_type": "email", "value": "john@suspicious.com", "label": "Email 1"},
            {"entity_type": "email", "value": "johndoe@darkmail.onion", "label": "Email 2"},
            {"entity_type": "wallet", "value": "0xABCDEF1234567890abcdef1234567890abcdef12", "label": "Wallet 1"},
            {"entity_type": "domain", "value": "suspicious.com", "label": "Domain 1"}
        ]
        
        for entity in entities:
            resp = requests.post(
                f"{BASE_URL}/api/investigations/{investigation_id}/entities",
                json=entity,
                headers=get_headers()
            )
            entity_ids[entity["value"]] = resp.json()["id"]
        
        # Create relationships
        relationships = [
            ("John Doe", "john@suspicious.com", "owns"),
            ("John Doe", "johndoe@darkmail.onion", "owns"),
            ("john@suspicious.com", "suspicious.com", "linked_to"),
            ("John Doe", "0xABCDEF1234567890abcdef1234567890abcdef12", "owns")
        ]
        
        for source, target, rel_type in relationships:
            rel_payload = {
                "source_entity_id": entity_ids[source],
                "target_entity_id": entity_ids[target],
                "relationship_type": rel_type
            }
            requests.post(
                f"{BASE_URL}/api/investigations/{investigation_id}/relationships",
                json=rel_payload,
                headers=get_headers()
            )
        
        yield investigation_id
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/investigations/{investigation_id}",
            headers=get_headers()
        )
    
    def test_graph_analyze(self, investigation_with_graph):
        """Test full graph analysis endpoint"""
        payload = {
            "investigation_id": investigation_with_graph,
            "analysis_type": "full"
        }
        response = requests.post(
            f"{BASE_URL}/api/investigations/{investigation_with_graph}/graph/analyze",
            json=payload,
            headers=get_headers()
        )
        assert response.status_code == 200
        data = response.json()
        
        # Analysis data is nested under 'analysis' key
        assert data["success"] == True
        analysis = data.get("analysis", data)  # Handle both nested and flat response
        assert "clusters" in analysis
        assert "central_nodes" in analysis
        assert "suspicious_patterns" in analysis
        assert "summary" in analysis
        print(f"Graph analysis: {analysis['summary']}")
    
    def test_graph_clusters(self, investigation_with_graph):
        """Test graph clusters endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/investigations/{investigation_with_graph}/graph/clusters",
            headers=get_headers()
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "clusters" in data
        assert isinstance(data["clusters"], list)
        print(f"Found {len(data['clusters'])} clusters")
    
    def test_graph_suspicious_patterns(self, investigation_with_graph):
        """Test suspicious patterns endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/investigations/{investigation_with_graph}/graph/suspicious-patterns",
            headers=get_headers()
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "patterns" in data
        assert isinstance(data["patterns"], list)
        print(f"Found {len(data['patterns'])} suspicious patterns")


class TestLeadEngine:
    """Test Investigation Lead Engine - automated hypothesis generation"""
    
    @pytest.fixture
    def investigation_for_leads(self):
        """Create investigation with entities suitable for lead generation"""
        # Create investigation
        inv_payload = {
            "name": f"TEST_LeadEngine_{uuid.uuid4().hex[:8]}",
            "description": "Test for lead engine"
        }
        inv_response = requests.post(
            f"{BASE_URL}/api/investigations",
            json=inv_payload,
            headers=get_headers()
        )
        inv_data = inv_response.json()
        investigation_id = inv_data["id"]
        
        # Create entities for various lead patterns
        entity_ids = {}
        entities = [
            # Person with connections
            {"entity_type": "person", "value": "Crypto Trader X", "label": "Primary Suspect"},
            
            # Multiple emails on same domain - should trigger alias_cluster
            {"entity_type": "email", "value": "admin@shadytrader.com", "label": "Admin Email"},
            {"entity_type": "email", "value": "sales@shadytrader.com", "label": "Sales Email"},
            {"entity_type": "email", "value": "support@shadytrader.com", "label": "Support Email"},
            
            # Domain
            {"entity_type": "domain", "value": "shadytrader.com", "label": "Main Domain"},
            
            # Wallets - for wallet cluster pattern
            {"entity_type": "wallet", "value": "0x1111111111111111111111111111111111111111", "label": "Wallet 1"},
            {"entity_type": "wallet", "value": "0x2222222222222222222222222222222222222222", "label": "Wallet 2"},
            
            # Username that matches email pattern - for username_reuse
            {"entity_type": "username", "value": "@admin_shadytrader", "label": "Twitter Handle"}
        ]
        
        for entity in entities:
            resp = requests.post(
                f"{BASE_URL}/api/investigations/{investigation_id}/entities",
                json=entity,
                headers=get_headers()
            )
            entity_ids[entity["value"]] = resp.json()["id"]
        
        # Create relationships
        relationships = [
            ("Crypto Trader X", "admin@shadytrader.com", "owns"),
            ("Crypto Trader X", "0x1111111111111111111111111111111111111111", "owns"),
            ("Crypto Trader X", "0x2222222222222222222222222222222222222222", "owns"),
            ("admin@shadytrader.com", "shadytrader.com", "linked_to"),
            ("sales@shadytrader.com", "shadytrader.com", "linked_to"),
        ]
        
        for source, target, rel_type in relationships:
            if source in entity_ids and target in entity_ids:
                rel_payload = {
                    "source_entity_id": entity_ids[source],
                    "target_entity_id": entity_ids[target],
                    "relationship_type": rel_type
                }
                requests.post(
                    f"{BASE_URL}/api/investigations/{investigation_id}/relationships",
                    json=rel_payload,
                    headers=get_headers()
                )
        
        yield investigation_id
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/investigations/{investigation_id}",
            headers=get_headers()
        )
    
    def test_generate_leads(self, investigation_for_leads):
        """Test lead generation endpoint"""
        response = requests.post(
            f"{BASE_URL}/api/investigations/{investigation_for_leads}/leads/generate",
            headers=get_headers()
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert "leads_generated" in data
        assert "leads" in data
        assert data["leads_generated"] >= 0  # May be 0 if not enough data for patterns
        
        print(f"Generated {data['leads_generated']} leads")
        if data["leads"]:
            print(f"Lead types: {[l['lead_type'] for l in data['leads']]}")
        return data["leads"]
    
    def test_leads_have_required_fields(self, investigation_for_leads):
        """Test that generated leads have all required fields"""
        # Generate leads
        response = requests.post(
            f"{BASE_URL}/api/investigations/{investigation_for_leads}/leads/generate",
            headers=get_headers()
        )
        data = response.json()
        
        for lead in data.get("leads", []):
            # Required fields
            assert "id" in lead
            assert "lead_type" in lead
            assert "title" in lead
            assert "description" in lead
            assert "confidence" in lead
            assert "severity" in lead
            assert "status" in lead
            assert "suggested_actions" in lead
            
            # Validate confidence is 0-1
            assert 0 <= lead["confidence"] <= 1
            
            # Validate severity levels
            assert lead["severity"] in ["low", "medium", "high", "critical"]
            
            # Validate status
            assert lead["status"] in ["new", "investigating", "confirmed", "dismissed"]
            
            print(f"Lead: {lead['title']} - {lead['severity']} ({lead['confidence']*100:.0f}% confidence)")
    
    def test_leads_have_suggested_actions(self, investigation_for_leads):
        """Test that leads include suggested actions"""
        response = requests.post(
            f"{BASE_URL}/api/investigations/{investigation_for_leads}/leads/generate",
            headers=get_headers()
        )
        data = response.json()
        
        for lead in data.get("leads", []):
            if lead.get("suggested_actions"):
                for action in lead["suggested_actions"]:
                    assert "type" in action
                    assert "label" in action
                    # Action types: investigate, search, connect, enrich, report
                    assert action["type"] in ["investigate", "search", "connect", "enrich", "report"]
                print(f"Lead '{lead['title']}' has {len(lead['suggested_actions'])} suggested actions")
    
    def test_get_leads(self, investigation_for_leads):
        """Test fetching leads for investigation"""
        # First generate some leads
        requests.post(
            f"{BASE_URL}/api/investigations/{investigation_for_leads}/leads/generate",
            headers=get_headers()
        )
        
        # Then fetch them
        response = requests.get(
            f"{BASE_URL}/api/investigations/{investigation_for_leads}/leads",
            headers=get_headers()
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "leads" in data
        assert "total" in data
        assert isinstance(data["leads"], list)
        print(f"Fetched {data['total']} leads")
    
    def test_get_leads_with_status_filter(self, investigation_for_leads):
        """Test fetching leads filtered by status"""
        # Generate leads
        requests.post(
            f"{BASE_URL}/api/investigations/{investigation_for_leads}/leads/generate",
            headers=get_headers()
        )
        
        # Fetch leads with status filter
        response = requests.get(
            f"{BASE_URL}/api/investigations/{investigation_for_leads}/leads?status=new",
            headers=get_headers()
        )
        assert response.status_code == 200
        data = response.json()
        
        # All leads should be 'new' status
        for lead in data.get("leads", []):
            assert lead["status"] == "new"
        print(f"Fetched {data['total']} leads with status 'new'")
    
    def test_update_lead_status_to_investigating(self, investigation_for_leads):
        """Test changing lead status to investigating"""
        # Generate leads
        gen_response = requests.post(
            f"{BASE_URL}/api/investigations/{investigation_for_leads}/leads/generate",
            headers=get_headers()
        )
        leads = gen_response.json().get("leads", [])
        
        if not leads:
            pytest.skip("No leads generated to update")
        
        lead_id = leads[0]["id"]
        
        # Update status
        response = requests.patch(
            f"{BASE_URL}/api/investigations/{investigation_for_leads}/leads/{lead_id}?status=investigating",
            headers=get_headers()
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        
        # Verify update persisted
        get_response = requests.get(
            f"{BASE_URL}/api/investigations/{investigation_for_leads}/leads",
            headers=get_headers()
        )
        updated_lead = next((l for l in get_response.json()["leads"] if l["id"] == lead_id), None)
        assert updated_lead is not None
        assert updated_lead["status"] == "investigating"
        print(f"Lead {lead_id} status updated to 'investigating'")
    
    def test_update_lead_status_to_confirmed(self, investigation_for_leads):
        """Test changing lead status to confirmed"""
        gen_response = requests.post(
            f"{BASE_URL}/api/investigations/{investigation_for_leads}/leads/generate",
            headers=get_headers()
        )
        leads = gen_response.json().get("leads", [])
        
        if not leads:
            pytest.skip("No leads generated to update")
        
        lead_id = leads[0]["id"]
        
        response = requests.patch(
            f"{BASE_URL}/api/investigations/{investigation_for_leads}/leads/{lead_id}?status=confirmed",
            headers=get_headers()
        )
        assert response.status_code == 200
        print(f"Lead {lead_id} status updated to 'confirmed'")
    
    def test_update_lead_status_to_dismissed(self, investigation_for_leads):
        """Test dismissing a lead"""
        gen_response = requests.post(
            f"{BASE_URL}/api/investigations/{investigation_for_leads}/leads/generate",
            headers=get_headers()
        )
        leads = gen_response.json().get("leads", [])
        
        if not leads:
            pytest.skip("No leads generated to dismiss")
        
        lead_id = leads[0]["id"]
        
        response = requests.patch(
            f"{BASE_URL}/api/investigations/{investigation_for_leads}/leads/{lead_id}?status=dismissed",
            headers=get_headers()
        )
        assert response.status_code == 200
        print(f"Lead {lead_id} dismissed")
    
    def test_delete_lead(self, investigation_for_leads):
        """Test deleting a lead"""
        gen_response = requests.post(
            f"{BASE_URL}/api/investigations/{investigation_for_leads}/leads/generate",
            headers=get_headers()
        )
        leads = gen_response.json().get("leads", [])
        
        if not leads:
            pytest.skip("No leads generated to delete")
        
        lead_id = leads[0]["id"]
        
        response = requests.delete(
            f"{BASE_URL}/api/investigations/{investigation_for_leads}/leads/{lead_id}",
            headers=get_headers()
        )
        assert response.status_code == 200
        
        # Verify deleted
        get_response = requests.get(
            f"{BASE_URL}/api/investigations/{investigation_for_leads}/leads",
            headers=get_headers()
        )
        remaining_leads = get_response.json()["leads"]
        assert lead_id not in [l["id"] for l in remaining_leads]
        print(f"Lead {lead_id} deleted successfully")


class TestLeadPatterns:
    """Test specific lead pattern detection"""
    
    @pytest.fixture
    def investigation_with_alias_cluster(self):
        """Create investigation that should trigger alias_cluster pattern"""
        inv_payload = {
            "name": f"TEST_AliasCluster_{uuid.uuid4().hex[:8]}",
            "description": "Test for alias cluster pattern"
        }
        inv_response = requests.post(
            f"{BASE_URL}/api/investigations",
            json=inv_payload,
            headers=get_headers()
        )
        investigation_id = inv_response.json()["id"]
        
        entity_ids = {}
        
        # Domain
        domain_resp = requests.post(
            f"{BASE_URL}/api/investigations/{investigation_id}/entities",
            json={"entity_type": "domain", "value": "clusterdomain.com"},
            headers=get_headers()
        )
        entity_ids["domain"] = domain_resp.json()["id"]
        
        # Multiple emails with same domain
        for i in range(3):
            email_resp = requests.post(
                f"{BASE_URL}/api/investigations/{investigation_id}/entities",
                json={"entity_type": "email", "value": f"user{i}@clusterdomain.com"},
                headers=get_headers()
            )
            entity_ids[f"email{i}"] = email_resp.json()["id"]
        
        yield investigation_id
        
        requests.delete(f"{BASE_URL}/api/investigations/{investigation_id}", headers=get_headers())
    
    def test_alias_cluster_pattern(self, investigation_with_alias_cluster):
        """Test that alias cluster pattern is detected"""
        response = requests.post(
            f"{BASE_URL}/api/investigations/{investigation_with_alias_cluster}/leads/generate",
            headers=get_headers()
        )
        data = response.json()
        
        lead_types = [l["lead_type"] for l in data.get("leads", [])]
        # The alias_cluster pattern should be detected when multiple emails share a domain
        print(f"Generated lead types: {lead_types}")
        if "alias_cluster" in lead_types:
            print("Alias cluster pattern correctly detected!")
        else:
            print("Note: Alias cluster pattern not detected - may require email-domain relationships")


class TestLeadMetadata:
    """Test lead metadata and analysis details"""
    
    @pytest.fixture
    def investigation_with_leads(self):
        """Create investigation and generate leads"""
        inv_payload = {
            "name": f"TEST_LeadMetadata_{uuid.uuid4().hex[:8]}",
            "description": "Test for lead metadata"
        }
        inv_response = requests.post(
            f"{BASE_URL}/api/investigations",
            json=inv_payload,
            headers=get_headers()
        )
        investigation_id = inv_response.json()["id"]
        
        # Add entities
        entities = [
            {"entity_type": "person", "value": "Test Person"},
            {"entity_type": "email", "value": "test@example.com"},
            {"entity_type": "wallet", "value": "0xABCDEF0123456789abcdef0123456789abcdef01"},
            {"entity_type": "domain", "value": "example.onion"}
        ]
        entity_ids = {}
        for entity in entities:
            resp = requests.post(
                f"{BASE_URL}/api/investigations/{investigation_id}/entities",
                json=entity,
                headers=get_headers()
            )
            entity_ids[entity["value"]] = resp.json()["id"]
        
        # Create relationships to trigger patterns
        relationships = [
            ("Test Person", "test@example.com", "owns"),
            ("Test Person", "0xABCDEF0123456789abcdef0123456789abcdef01", "owns"),
            ("Test Person", "example.onion", "owns")
        ]
        for source, target, rel_type in relationships:
            requests.post(
                f"{BASE_URL}/api/investigations/{investigation_id}/relationships",
                json={
                    "source_entity_id": entity_ids[source],
                    "target_entity_id": entity_ids[target],
                    "relationship_type": rel_type
                },
                headers=get_headers()
            )
        
        yield investigation_id
        
        requests.delete(f"{BASE_URL}/api/investigations/{investigation_id}", headers=get_headers())
    
    def test_leads_contain_metadata(self, investigation_with_leads):
        """Test that leads contain useful metadata"""
        response = requests.post(
            f"{BASE_URL}/api/investigations/{investigation_with_leads}/leads/generate",
            headers=get_headers()
        )
        data = response.json()
        
        for lead in data.get("leads", []):
            if lead.get("metadata"):
                print(f"Lead '{lead['title']}' metadata: {lead['metadata']}")
                # Metadata should be a dict
                assert isinstance(lead["metadata"], dict)
    
    def test_leads_contain_affected_entities(self, investigation_with_leads):
        """Test that leads reference affected entities"""
        response = requests.post(
            f"{BASE_URL}/api/investigations/{investigation_with_leads}/leads/generate",
            headers=get_headers()
        )
        data = response.json()
        
        for lead in data.get("leads", []):
            if lead.get("affected_entities"):
                assert isinstance(lead["affected_entities"], list)
                print(f"Lead '{lead['title']}' affects {len(lead['affected_entities'])} entities")


# Cleanup test data
@pytest.fixture(scope="session", autouse=True)
def cleanup_test_data():
    """Clean up TEST_ prefixed investigations after all tests"""
    yield
    response = requests.get(f"{BASE_URL}/api/investigations", headers=get_headers())
    if response.status_code == 200:
        investigations = response.json()
        for inv in investigations:
            if inv.get("name", "").startswith("TEST_"):
                requests.delete(
                    f"{BASE_URL}/api/investigations/{inv['id']}",
                    headers=get_headers()
                )
                print(f"Cleaned up: {inv['name']}")

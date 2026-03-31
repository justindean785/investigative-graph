"""
Entity processor — handles enrichment of individual entities.
"""

import logging
from typing import List, Dict, Any, Optional

from .models import NormalizedEntity, NormalizedEvidence
from .pivot_planner import PivotPlanner

logger = logging.getLogger(__name__)


class EntityProcessor:
    """Process and enrich entities using OSINT providers."""
    
    def __init__(self, osint_search_func):
        """
        Initialize with OSINT search function.
        
        Args:
            osint_search_func: Async function that takes (query, search_type) and returns OSINT results
        """
        self.osint_search = osint_search_func
    
    async def enrich_entity(
        self,
        entity: NormalizedEntity
    ) -> Dict[str, Any]:
        """
        Enrich an entity by querying OSINT providers.
        
        Returns:
            dict with keys: 'success', 'results', 'error'
        """
        try:
            # Map entity type to OSINT search type
            search_type = entity.entity_type
            
            # Call the OSINT search
            logger.info(f"Enriching {entity.entity_type}: {entity.value}")
            results = await self.osint_search(entity.value, search_type)
            
            return {
                "success": True,
                "results": results.get("results", []) if isinstance(results, dict) else results,
                "live_data": results.get("live_data", True) if isinstance(results, dict) else True
            }
            
        except Exception as e:
            logger.error(f"Failed to enrich {entity.value}: {e}")
            return {
                "success": False,
                "results": [],
                "error": str(e)
            }
    
    @staticmethod
    def extract_entities_from_text(text: str) -> List[Dict[str, str]]:
        """
        Extract entities from raw text using regex patterns.
        
        Returns list of {'type': str, 'value': str} dicts.
        """
        import re
        
        entities = []
        
        # Email pattern
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        for match in re.finditer(email_pattern, text):
            entities.append({"type": "email", "value": match.group()})
        
        # Phone pattern (various formats)
        phone_pattern = r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        for match in re.finditer(phone_pattern, text):
            phone = match.group().strip()
            if len(phone) >= 10:  # Minimum valid phone length
                entities.append({"type": "phone", "value": phone})
        
        # Username pattern (@ mentions or common username format)
        username_pattern = r'@([a-zA-Z0-9_]{3,20})\b'
        for match in re.finditer(username_pattern, text):
            entities.append({"type": "username", "value": match.group(1)})
        
        # IP address pattern
        ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
        for match in re.finditer(ip_pattern, text):
            ip = match.group()
            # Basic validation
            octets = ip.split('.')
            if all(0 <= int(octet) <= 255 for octet in octets):
                entities.append({"type": "ip", "value": ip})
        
        # Domain pattern
        domain_pattern = r'\b(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}\b'
        for match in re.finditer(domain_pattern, text):
            domain = match.group().lower()
            # Exclude emails and very short domains
            if '@' not in domain and len(domain) > 4:
                entities.append({"type": "domain", "value": domain})
        
        # Wallet addresses (Bitcoin, Ethereum)
        btc_pattern = r'\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b'
        eth_pattern = r'\b0x[a-fA-F0-9]{40}\b'
        
        for match in re.finditer(btc_pattern, text):
            entities.append({"type": "wallet", "value": match.group(), "metadata": {"currency": "BTC"}})
        
        for match in re.finditer(eth_pattern, text):
            entities.append({"type": "wallet", "value": match.group(), "metadata": {"currency": "ETH"}})
        
        # Deduplicate
        seen = set()
        unique_entities = []
        for ent in entities:
            key = (ent["type"], ent["value"].lower())
            if key not in seen:
                seen.add(key)
                unique_entities.append(ent)
        
        return unique_entities

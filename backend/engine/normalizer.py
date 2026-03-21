"""
Provider output normalizer.

Converts GHOSINT/Swatted/BOSINT responses into unified NormalizedEntity/NormalizedEvidence.
"""

import logging
import re
from typing import List, Dict, Any
from datetime import datetime

from .models import NormalizedEntity, NormalizedEvidence, NormalizedSource

logger = logging.getLogger(__name__)


class ProviderNormalizer:
    """Normalize provider outputs into unified schema."""

    @staticmethod
    def normalize_ghosint_result(result: Dict[str, Any], query: str, query_type: str) -> tuple[List[NormalizedEntity], List[NormalizedEvidence]]:
        """Normalize GHOSINT search result."""
        entities = []
        evidence_list = []
        
        source_name = result.get("source", "ghosint/unknown")
        provider, service = source_name.split("/") if "/" in source_name else ("ghosint", source_name)
        
        raw_data = result.get("data", {})
        
        # Create source
        source = NormalizedSource(
            provider=provider,
            service=service,
            raw_data=raw_data
        )
        
        # Extract entities from breach data
        if query_type == "email" and isinstance(raw_data, dict):
            # GHOSINT leakcheck returns list of breaches
            if isinstance(raw_data, list):
                for breach in raw_data:
                    password = breach.get("password")
                    if password:
                        # Extract potential usernames from breach data
                        username_match = re.search(r'username["\s:]+([a-zA-Z0-9_-]+)', str(breach), re.IGNORECASE)
                        if username_match:
                            entities.append(NormalizedEntity(
                                entity_type="username",
                                value=username_match.group(1),
                                confidence=0.6,
                                sources=[source],
                                derived_from=query,
                                metadata={"extraction_source": "breach_data"}
                            ))
            
            # GHOSINT snusbase returns database hits
            elif isinstance(raw_data, dict):
                for db_name, records in raw_data.items():
                    if isinstance(records, list):
                        for record in records[:5]:  # Limit to first 5 records
                            # Extract phone if present
                            if "phone" in record and record["phone"]:
                                phone = str(record["phone"]).strip()
                                if phone and len(phone) > 5:
                                    entities.append(NormalizedEntity(
                                        entity_type="phone",
                                        value=phone,
                                        confidence=0.7,
                                        sources=[source],
                                        derived_from=query,
                                        metadata={"database": db_name}
                                    ))
                            
                            # Extract name if present
                            if "name" in record and record["name"]:
                                name = str(record["name"]).strip()
                                if name and len(name) > 2:
                                    entities.append(NormalizedEntity(
                                        entity_type="name",
                                        value=name,
                                        confidence=0.6,
                                        sources=[source],
                                        derived_from=query,
                                        metadata={"database": db_name}
                                    ))
        
        # Create evidence from raw result
        if raw_data:
            evidence_list.append(NormalizedEvidence(
                evidence_type="breach_data" if query_type == "email" else "osint_lookup",
                content=f"{service} results for {query}",
                sources=[source],
                metadata={"result_count": len(raw_data) if isinstance(raw_data, list) else 1}
            ))
        
        return entities, evidence_list

    @staticmethod
    def normalize_swatted_result(result: Dict[str, Any], query: str, query_type: str) -> tuple[List[NormalizedEntity], List[NormalizedEvidence]]:
        """Normalize Swatted search result."""
        entities = []
        evidence_list = []
        
        source_name = result.get("source", "swatted/unknown")
        provider, service = source_name.split("/") if "/" in source_name else ("swatted", source_name)
        
        raw_data = result.get("data", {})
        
        source = NormalizedSource(
            provider=provider,
            service=service,
            raw_data=raw_data
        )
        
        # Extract from Swatted results
        if query_type == "email" and isinstance(raw_data, dict):
            # Swatted leakosint/snusbase structure
            results_data = raw_data.get("results", {})
            
            # Extract data array if present
            data_array = results_data.get("data", []) if isinstance(results_data, dict) else []
            
            if isinstance(data_array, list):
                for record in data_array[:5]:
                    if isinstance(record, dict):
                        # Extract usernames
                        username = record.get("username") or record.get("user")
                        if username:
                            entities.append(NormalizedEntity(
                                entity_type="username",
                                value=str(username).strip(),
                                confidence=0.7,
                                sources=[source],
                                derived_from=query
                            ))
        
        # Create evidence
        if raw_data:
            evidence_list.append(NormalizedEvidence(
                evidence_type="breach_data" if query_type == "email" else "osint_lookup",
                content=f"{service} results for {query}",
                sources=[source],
                metadata={"provider": "swatted"}
            ))
        
        return entities, evidence_list

    @staticmethod
    def normalize_bosint_result(result: Dict[str, Any], query: str, query_type: str) -> tuple[List[NormalizedEntity], List[NormalizedEvidence]]:
        """Normalize BOSINT search result."""
        entities = []
        evidence_list = []
        
        source_name = result.get("source", "bosint/unknown")
        provider, service = source_name.split("/") if "/" in source_name else ("bosint", source_name)
        
        raw_data = result.get("data", {})
        
        source = NormalizedSource(
            provider=provider,
            service=service,
            raw_data=raw_data
        )
        
        # Extract from BOSINT results
        if query_type == "email" and service == "email":
            # BOSINT email breach check
            breaches = raw_data.get("breaches", [])
            if isinstance(breaches, list):
                for breach in breaches[:3]:
                    if isinstance(breach, dict):
                        # Extract any usernames from breach data
                        username = breach.get("username")
                        if username:
                            entities.append(NormalizedEntity(
                                entity_type="username",
                                value=str(username).strip(),
                                confidence=0.65,
                                sources=[source],
                                derived_from=query
                            ))
        
        elif query_type == "email" and service == "darkweb":
            # BOSINT dark web search
            results = raw_data.get("results", [])
            if isinstance(results, list):
                for item in results[:3]:
                    if isinstance(item, dict):
                        description = item.get("description", "")
                        # Extract potential usernames from dark web mentions
                        username_matches = re.findall(r'@([a-zA-Z0-9_]{3,20})', description)
                        for username in username_matches:
                            entities.append(NormalizedEntity(
                                entity_type="username",
                                value=username,
                                confidence=0.5,  # Lower confidence from dark web
                                sources=[source],
                                derived_from=query,
                                metadata={"source_type": "darkweb"}
                            ))
        
        elif query_type == "phone" and service == "phone":
            # BOSINT phone lookup
            name = raw_data.get("name") or raw_data.get("full_name")
            if name:
                entities.append(NormalizedEntity(
                    entity_type="name",
                    value=str(name).strip(),
                    confidence=0.75,
                    sources=[source],
                    derived_from=query,
                    metadata={
                        "carrier": raw_data.get("carrier"),
                        "location": raw_data.get("location")
                    }
                ))
        
        # Create evidence
        if raw_data:
            evidence_list.append(NormalizedEvidence(
                evidence_type=f"{service}_lookup",
                content=f"BOSINT {service} results for {query}",
                sources=[source],
                metadata={"command": service}
            ))
        
        return entities, evidence_list

    @staticmethod
    def normalize_osint_search_results(
        results: List[Dict[str, Any]], 
        query: str, 
        query_type: str
    ) -> tuple[List[NormalizedEntity], List[NormalizedEvidence]]:
        """Normalize full OSINT search results from all providers."""
        all_entities = []
        all_evidence = []
        
        for result in results:
            source_name = result.get("source", "")
            
            try:
                if source_name.startswith("ghosint"):
                    entities, evidence = ProviderNormalizer.normalize_ghosint_result(result, query, query_type)
                elif source_name.startswith("swatted"):
                    entities, evidence = ProviderNormalizer.normalize_swatted_result(result, query, query_type)
                elif source_name.startswith("bosint"):
                    entities, evidence = ProviderNormalizer.normalize_bosint_result(result, query, query_type)
                else:
                    logger.warning(f"Unknown provider: {source_name}")
                    continue
                
                all_entities.extend(entities)
                all_evidence.extend(evidence)
                
            except Exception as e:
                logger.error(f"Failed to normalize result from {source_name}: {e}")
        
        # Deduplicate entities by (type, value)
        seen = set()
        deduped_entities = []
        for entity in all_entities:
            key = (entity.entity_type, entity.value.lower())
            if key not in seen:
                seen.add(key)
                deduped_entities.append(entity)
            else:
                # Merge sources if duplicate
                for existing in deduped_entities:
                    if existing.entity_type == entity.entity_type and existing.value.lower() == entity.value.lower():
                        existing.sources.extend(entity.sources)
                        existing.confidence = max(existing.confidence, entity.confidence)
                        break
        
        return deduped_entities, all_evidence

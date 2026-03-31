"""
routers/ai.py — AI analysis, chat, Grok enrichment, and suggestion management endpoints.

Routes:
  POST /api/ai/analyze                                    — Gemini analysis → stored suggestions
  POST /api/ai/grok/enrich                               — Grok-3 entity enrichment
  GET  /api/investigations/{id}/suggestions               — list pending suggestions
  PATCH /api/investigations/{id}/suggestions/{sid}        — update suggestion status
  GET  /api/investigations/{id}/chat/history              — retrieve chat history
  POST /api/investigations/{id}/chat                      — interactive AI chat (Gemini)
  DELETE /api/investigations/{id}/chat/clear              — clear chat history

All business logic preserved verbatim from server.py.
Only the import paths and router prefix differ.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from core.config import (
    GEMINI_API_KEY,
    GEMINI_MODEL_CHAT,
    GEMINI_MODEL_FLASH,
    GEMINI_MODEL_PRO,
    GROK_API_KEY,
)
from core.deps import (
    create_timeline_event,
    db,
    enforce_rate_limit,
    serialize_datetime,
)
from core.security import validate_api_key
from fastapi import APIRouter, Header, HTTPException
from google import genai
from models import (
    AIAnalysisRequest,
    AISuggestion,
    ChatMessage,
    ChatRequest,
    GrokEnrichRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["ai"])

# ---------------------------------------------------------------------------
# Client initialisation (module-level singletons)
# ---------------------------------------------------------------------------

_gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

try:
    from openai import AsyncOpenAI

    _grok_client = (
        AsyncOpenAI(
            api_key=GROK_API_KEY,
            base_url="https://api.x.ai/v1",
        )
        if GROK_API_KEY
        else None
    )
except ImportError:
    _grok_client = None


# ---------------------------------------------------------------------------
# Routes — AI Analysis
# ---------------------------------------------------------------------------


@router.post("/ai/analyze")
async def ai_analyze(
    input: AIAnalysisRequest,
    x_api_key: str = Header(None),
):
    """
    Run Gemini analysis on an investigation and persist generated suggestions.

    Fetches the investigation's entities and relationships, builds a structured
    prompt, calls Gemini, parses the JSON response, stores each suggestion, and
    returns a summary.  Falls back gracefully on JSON parse errors.
    """
    await validate_api_key(x_api_key)
    enforce_rate_limit(x_api_key, "ai")

    try:
        entities = await db.entities.find(
            {"investigation_id": input.investigation_id}, {"_id": 0}
        ).to_list(10000)
        relationships = await db.relationships.find(
            {"investigation_id": input.investigation_id}, {"_id": 0}
        ).to_list(10000)

        # Build context for AI
        context = (
            "You are an OSINT investigation assistant analyzing a case.\n\n"
            f"Entities in investigation: {len(entities)}\n"
        )

        if entities:
            context += "\n\nKey entities:\n"
            for ent in entities[:10]:
                context += f"- {ent['entity_type']}: {ent['value']}\n"

        if relationships:
            context += (
                f"\n\nRelationships: {len(relationships)} connections discovered\n"
            )

        if input.context:
            context += f"\n\nAdditional context: {input.context}\n"

        context += (
            "\nProvide 3-5 investigative suggestions. For each suggestion, provide:\n"
            "1. A clear title\n"
            "2. A brief description\n"
            "3. The suggestion type (one of: connection, lead, pattern, enrichment)\n"
            "4. Action data (structured data for executing the suggestion)\n\n"
            "Format as JSON array with structure:\n"
            "[\n"
            "  {\n"
            '    "title": "...",\n'
            '    "description": "...",\n'
            '    "suggestion_type": "...",\n'
            '    "action_data": {...}\n'
            "  }\n"
            "]\n"
        )

        model = (
            GEMINI_MODEL_FLASH
            if (input.mode or "").lower() == "flash"
            else GEMINI_MODEL_PRO
        )

        if not _gemini_client:
            raise HTTPException(status_code=503, detail="GEMINI_API_KEY not configured")

        gemini_response = _gemini_client.models.generate_content(
            model=model,
            contents=context,
            config=genai.types.GenerateContentConfig(
                system_instruction=(
                    "You are an expert OSINT investigator providing actionable "
                    "intelligence suggestions."
                ),
                temperature=0.7,
            ),
        )
        response_text: str = gemini_response.text

        # Parse AI response
        try:
            clean = response_text.strip()
            if "```json" in clean:
                clean = clean.split("```json")[1].split("```")[0].strip()
            elif "```" in clean:
                clean = clean.split("```")[1].split("```")[0].strip()

            suggestions_data = json.loads(clean)

            for sug_data in suggestions_data:
                suggestion = AISuggestion(
                    investigation_id=input.investigation_id,
                    suggestion_type=sug_data.get("suggestion_type", "lead"),
                    title=sug_data.get("title", "Suggestion"),
                    description=sug_data.get("description", ""),
                    action_data=sug_data.get("action_data", {}),
                )
                doc = serialize_datetime(suggestion.model_dump())
                await db.ai_suggestions.insert_one(doc)

            await create_timeline_event(
                input.investigation_id,
                "ai_analysis",
                (
                    f"AI analysis completed using {model} — "
                    f"{len(suggestions_data)} suggestions generated"
                ),
            )

            return {
                "success": True,
                "model_used": model,
                "suggestions_count": len(suggestions_data),
                "suggestions": suggestions_data,
            }

        except json.JSONDecodeError:
            # Fallback: store raw response as a single generic suggestion
            suggestion = AISuggestion(
                investigation_id=input.investigation_id,
                suggestion_type="lead",
                title="AI Analysis Result",
                description=response_text[:500],
                action_data={},
            )
            doc = serialize_datetime(suggestion.model_dump())
            await db.ai_suggestions.insert_one(doc)

            return {
                "success": True,
                "model_used": model,
                "suggestions_count": 1,
                "raw_response": response_text,
            }

    except Exception as exc:
        logger.error("AI analysis failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500, detail="AI analysis failed. Please try again later."
        )


# ---------------------------------------------------------------------------
# Routes — Grok Enrichment
# ---------------------------------------------------------------------------


@router.post("/ai/grok/enrich")
async def grok_enrich_entity(
    request: GrokEnrichRequest,
    x_api_key: Optional[str] = Header(None),
):
    """
    Use Grok-3 to enrich an entity with intelligence data.

    Returns enriched metadata, suggested relationships, a risk score,
    investigation leads, and a one-line summary.  On success the entity
    record in MongoDB is updated with the new metadata and risk score.
    """
    await validate_api_key(x_api_key)

    if not _grok_client:
        raise HTTPException(status_code=503, detail="GROK_API_KEY not configured")

    prompt = (
        "Elite OSINT analyst mode. Enrich this entity and return ONLY valid JSON:\n"
        "{\n"
        '  "enriched_metadata": {...},\n'
        '  "relationships": [{ "type": "...", "target": "...", "confidence": 0.9 }],\n'
        '  "risk_score": 0.65,\n'
        '  "leads": ["step 1", "step 2"],\n'
        '  "summary": "one-line intel"\n'
        "}\n\n"
        f"Entity: {request.entity_type} → {request.value}\n"
        f"Context: {request.context or 'None'}"
    )

    response = await _grok_client.chat.completions.create(
        model="grok-3",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=1200,
    )

    raw_content: str = response.choices[0].message.content or ""

    # Strip markdown code fences if the model wrapped the JSON
    if "```json" in raw_content:
        raw_content = raw_content.split("```json")[1].split("```")[0].strip()
    elif "```" in raw_content:
        raw_content = raw_content.split("```")[1].split("```")[0].strip()

    try:
        result = json.loads(raw_content)
    except json.JSONDecodeError as exc:
        logger.error("Grok enrichment returned non-JSON: %r", raw_content[:200])
        raise HTTPException(
            status_code=502,
            detail="Grok returned an unexpected response format. Try again.",
        ) from exc

    await db.entities.update_one(
        {"investigation_id": request.investigation_id, "value": request.value},
        {
            "$set": {
                "metadata": result.get("enriched_metadata", {}),
                "risk_score": result.get("risk_score", 0.0),
            }
        },
    )

    await create_timeline_event(
        request.investigation_id,
        "ai_enrichment",
        f"Grok-3 enriched {request.entity_type}: {request.value}",
    )

    return {"success": True, "data": result}


# ---------------------------------------------------------------------------
# Routes — Suggestions
# ---------------------------------------------------------------------------


@router.get(
    "/investigations/{investigation_id}/suggestions",
    response_model=List[AISuggestion],
)
async def get_suggestions(
    investigation_id: str,
    x_api_key: str = Header(None),
):
    """Return all pending AI suggestions for an investigation."""
    await validate_api_key(x_api_key)

    suggestions = await db.ai_suggestions.find(
        {"investigation_id": investigation_id, "status": "pending"},
        {"_id": 0},
    ).to_list(10000)

    for sug in suggestions:
        if isinstance(sug.get("created_at"), str):
            sug["created_at"] = datetime.fromisoformat(sug["created_at"])

    return suggestions


@router.patch("/investigations/{investigation_id}/suggestions/{suggestion_id}")
async def update_suggestion_status(
    investigation_id: str,
    suggestion_id: str,
    status: str,
    x_api_key: str = Header(None),
):
    """Update the status of a single AI suggestion."""
    await validate_api_key(x_api_key)

    valid_statuses = {"pending", "accepted", "rejected", "implemented"}
    if status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"status must be one of: {', '.join(sorted(valid_statuses))}",
        )

    await db.ai_suggestions.update_one(
        {"id": suggestion_id, "investigation_id": investigation_id},
        {"$set": {"status": status}},
    )

    return {"success": True}


# ---------------------------------------------------------------------------
# Routes — Chat
# ---------------------------------------------------------------------------


@router.get("/investigations/{investigation_id}/chat/history")
async def get_chat_history(
    investigation_id: str,
    session_id: Optional[str] = None,
    limit: int = 50,
    x_api_key: Optional[str] = Header(None),
):
    """Retrieve chat message history for an investigation (optionally filtered by session)."""
    await validate_api_key(x_api_key)

    query = {"investigation_id": investigation_id}
    if session_id:
        query["session_id"] = session_id

    messages = (
        await db.chat_messages.find(query, {"_id": 0})
        .sort("timestamp", 1)
        .to_list(limit)
    )

    return {"messages": messages, "count": len(messages)}


@router.post("/investigations/{investigation_id}/chat")
async def chat_with_ai(
    investigation_id: str,
    request: ChatRequest,
    x_api_key: Optional[str] = Header(None),
):
    """
    Interactive AI chat with full investigation context.

    Builds a rich system prompt from the investigation's current entities,
    relationships, evidence, and active leads, then calls Gemini in
    conversation mode.  Messages are persisted to the chat_messages collection.
    """
    await validate_api_key(x_api_key)
    enforce_rate_limit(x_api_key, "ai")

    session_id = request.session_id or f"chat-{investigation_id}-{uuid.uuid4().hex[:8]}"

    try:
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

        leads = await db.investigation_leads.find(
            {"investigation_id": investigation_id}, {"_id": 0}
        ).to_list(20)

        chat_history = (
            await db.chat_messages.find(
                {"investigation_id": investigation_id, "session_id": session_id},
                {"_id": 0},
            )
            .sort("timestamp", 1)
            .to_list(20)
        )

        # Build comprehensive context string
        context_parts = [
            f"# Investigation: {investigation.get('name', 'Unknown')}",
            f"Description: {investigation.get('description', 'N/A')}",
            "\n## Statistics:",
            f"- Entities: {len(entities)}",
            f"- Relationships: {len(relationships)}",
            f"- Evidence Items: {len(evidence)}",
            f"- Investigation Leads: {len(leads)}",
        ]

        if entities:
            context_parts.append("\n## Key Entities:")
            entities_by_type: dict = {}
            for e in entities:
                et = e.get("entity_type", "unknown")
                if et not in entities_by_type:
                    entities_by_type[et] = []
                entities_by_type[et].append(e.get("value", "")[:50])
            for etype, values in list(entities_by_type.items())[:8]:
                context_parts.append(f"- {etype.upper()}: {', '.join(values[:5])}")

        if relationships:
            context_parts.append(
                f"\n## Relationships: {len(relationships)} connections discovered"
            )
            entity_lookup = {e["id"]: e for e in entities}
            for rel in relationships[:5]:
                source = entity_lookup.get(rel.get("source_entity_id"), {})
                target = entity_lookup.get(rel.get("target_entity_id"), {})
                context_parts.append(
                    f"- {source.get('value', '?')[:20]} "
                    f"→ {rel.get('relationship_type', '?')} "
                    f"→ {target.get('value', '?')[:20]}"
                )

        if leads:
            context_parts.append("\n## Active Leads:")
            for lead in leads[:5]:
                context_parts.append(
                    f"- [{lead.get('severity', 'medium').upper()}] "
                    f"{lead.get('title', '?')}: "
                    f"{lead.get('description', '')[:100]}"
                )

        if evidence:
            context_parts.append(f"\n## Evidence Summary: {len(evidence)} items")
            for ev in evidence[:5]:
                context_parts.append(
                    f"- [{ev.get('evidence_type', 'unknown')}] "
                    f"{ev.get('content', '')[:80]}..."
                )

        investigation_context = "\n".join(context_parts)

        system_message = (
            "You are an expert OSINT investigation analyst assistant. "
            "You have access to the current investigation data and can "
            "help analyze it.\n\n"
            "Your capabilities:\n"
            "1. Answer questions about entities, relationships, and "
            "evidence in this investigation\n"
            "2. Identify patterns, connections, and suspicious activities\n"
            "3. Suggest next investigative steps\n"
            "4. Summarize the investigation status\n"
            "5. Analyze potential connections between entities\n"
            "6. Assess risk levels and provide threat intelligence insights\n\n"
            "Always be professional, precise, and focus on actionable "
            "intelligence. When analyzing data, cite specific entities "
            "and relationships. If you identify potential leads or "
            "patterns, explain your reasoning.\n\n"
            "CURRENT INVESTIGATION DATA:\n"
            f"{investigation_context}\n"
        )

        if not _gemini_client:
            raise HTTPException(status_code=503, detail="GEMINI_API_KEY not configured")

        # Build conversation history for Gemini multi-turn
        contents = []
        for msg in chat_history[-10:]:
            role = "user" if msg.get("role") == "user" else "model"
            contents.append(
                genai.types.Content(
                    role=role,
                    parts=[genai.types.Part(text=msg.get("content", ""))],
                )
            )
        contents.append(
            genai.types.Content(
                role="user",
                parts=[genai.types.Part(text=request.message)],
            )
        )

        # Persist user message before calling the model
        user_msg = ChatMessage(
            investigation_id=investigation_id,
            session_id=session_id,
            role="user",
            content=request.message,
        )
        user_doc = serialize_datetime(user_msg.model_dump())
        await db.chat_messages.insert_one(user_doc)

        gemini_response = _gemini_client.models.generate_content(
            model=GEMINI_MODEL_CHAT,
            contents=contents,
            config=genai.types.GenerateContentConfig(
                system_instruction=system_message,
                temperature=0.7,
            ),
        )
        response_text: str = gemini_response.text

        # Persist assistant reply
        assistant_msg = ChatMessage(
            investigation_id=investigation_id,
            session_id=session_id,
            role="assistant",
            content=response_text,
        )
        assistant_doc = serialize_datetime(assistant_msg.model_dump())
        await db.chat_messages.insert_one(assistant_doc)

        await create_timeline_event(
            investigation_id,
            "ai_chat",
            f"AI chat interaction: {request.message[:50]}...",
        )

        return {
            "success": True,
            "session_id": session_id,
            "message": response_text,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as exc:
        logger.error("AI chat failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500, detail="AI chat failed. Please try again later."
        )


@router.delete("/investigations/{investigation_id}/chat/clear")
async def clear_chat_history(
    investigation_id: str,
    session_id: Optional[str] = None,
    x_api_key: Optional[str] = Header(None),
):
    """Delete all (or session-scoped) chat messages for an investigation."""
    await validate_api_key(x_api_key)

    query = {"investigation_id": investigation_id}
    if session_id:
        query["session_id"] = session_id

    result = await db.chat_messages.delete_many(query)

    return {"success": True, "deleted_count": result.deleted_count}

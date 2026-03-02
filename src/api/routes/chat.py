"""RAG chat endpoint — scoped to a library with per-library persona."""

import json
import os

import psycopg2
import psycopg2.extras
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config.settings import DATABASE_URL
from src.embeddings.provider import embed_text
from src.llm.provider import get_provider

router = APIRouter()

DEFAULT_SYSTEM_PROMPT = """You are a helpful document assistant. Answer questions based ONLY on the provided document excerpts.

CRITICAL RULES:
1. ONLY use information from the provided document excerpts to answer questions
2. If the excerpts don't contain relevant information, say so honestly - don't fabricate
3. Quote directly from the documents when possible
4. Cite which document/section the information comes from
5. Be clear, professional, and helpful"""


class ChatRequest(BaseModel):
    message: str
    context_limit: int = 10


class ChatResponse(BaseModel):
    response: str
    sources: list[dict]


def _get_library_persona(library_id: int) -> str:
    """Get system prompt from library config, or use default."""
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SELECT config FROM libraries WHERE id = %s", (library_id,))
            row = cur.fetchone()
            if not row:
                return DEFAULT_SYSTEM_PROMPT
            config = row["config"] or {}
            persona = config.get("persona", {})
            if persona.get("system_prompt"):
                return persona["system_prompt"]
            return DEFAULT_SYSTEM_PROMPT
    finally:
        conn.close()


def retrieve_context(library_id: int, query: str, limit: int = 10) -> list[dict]:
    """Retrieve relevant chunks from a specific library via semantic search."""
    embedding = embed_text(query)

    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT c.text, d.title, d.section,
                       1 - (c.embedding <=> %s::vector) as similarity
                FROM chunks c
                JOIN documents d ON d.id = c.document_id
                WHERE c.embedding IS NOT NULL AND c.library_id = %s
                ORDER BY c.embedding <=> %s::vector
                LIMIT %s
            """, (str(embedding), library_id, str(embedding), limit))
            rows = cur.fetchall()
    finally:
        conn.close()

    return [
        {"text": row[0], "title": row[1], "section": row[2],
         "similarity": round(float(row[3]), 4)}
        for row in rows
    ]


@router.post("/libraries/{library_id}/chat", response_model=ChatResponse)
def chat_with_library(library_id: int, req: ChatRequest):
    """RAG chat within a specific library."""
    sources = retrieve_context(library_id, req.message, limit=req.context_limit)

    if not sources:
        return ChatResponse(
            response="This library doesn't have any indexed content yet. Please upload some documents first.",
            sources=[],
        )

    context_parts = []
    for i, src in enumerate(sources, 1):
        label = src["title"]
        if src["section"] and src["section"] != src["title"]:
            label = f"{src['section']} - {src['title']}"
        context_parts.append(f'[Excerpt {i} from "{label}"]\n{src["text"]}')

    context_block = "\n\n---\n\n".join(context_parts)

    user_message = f"""Based on these document excerpts, please answer the following question.

DOCUMENT EXCERPTS:
{context_block}

QUESTION: {req.message}"""

    system_prompt = _get_library_persona(library_id)

    try:
        provider = get_provider()
        response_text = provider.generate(
            system=system_prompt,
            user=user_message,
            max_tokens=1500,
        )
    except Exception as e:
        err = str(e)
        if "credit balance" in err or "billing" in err.lower():
            raise HTTPException(status_code=402, detail="LLM API credit balance too low.")
        elif "api_key" in err.lower() or "authentication" in err.lower() or "401" in err:
            raise HTTPException(status_code=401, detail="Invalid or missing API key.")
        else:
            raise HTTPException(status_code=503, detail=f"LLM error: {err}")

    return ChatResponse(
        response=response_text,
        sources=[{"title": s["title"], "section": s["section"], "similarity": s["similarity"]}
                 for s in sources[:5]],
    )

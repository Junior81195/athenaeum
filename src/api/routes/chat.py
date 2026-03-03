"""RAG chat endpoint — scoped to a library with per-library persona and citation support."""

import json
import logging
import os
import uuid

import psycopg2
import psycopg2.extras
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from config.settings import DATABASE_URL
from src.embeddings.provider import embed_text
from src.llm.provider import get_provider
from src.api.auth import require_auth, is_admin, check_library_read_access
from src.api.rate_limit import check_rate_limit

router = APIRouter()
logger = logging.getLogger("athenaeum.chat")

DEFAULT_SYSTEM_PROMPT = """You are a helpful document assistant. Answer questions based ONLY on the provided document excerpts.

CRITICAL RULES:
1. ONLY use information from the provided document excerpts to answer questions
2. If the excerpts don't contain relevant information, say so honestly — don't fabricate
3. Use inline citations like [1], [2], [3] to reference specific source excerpts
4. Every factual claim MUST have a citation
5. Quote directly from the documents when relevant, using blockquotes
6. Be clear, professional, and helpful
7. At the end, suggest 2-3 follow-up questions the user might want to ask"""


# ── Request/Response Models ──────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    context_limit: int = 10
    conversation_id: str | None = None


class SourceDetail(BaseModel):
    index: int
    title: str
    section: str | None
    text: str
    similarity: float
    document_id: int
    page_start: int | None = None
    page_end: int | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceDetail]
    suggestions: list[str]
    conversation_id: str


class ConversationSummary(BaseModel):
    id: str
    title: str | None
    created_at: str
    updated_at: str
    message_count: int


class MessageDetail(BaseModel):
    id: str
    role: str
    content: str
    sources_json: list | None
    created_at: str


class ConversationDetail(BaseModel):
    id: str
    library_id: int | None
    library_ids: list[int] = []
    title: str | None
    created_at: str
    messages: list[MessageDetail]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_library_persona(library_id: int) -> str:
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
                # Append citation instructions to custom personas
                base = persona["system_prompt"]
                return base + "\n\nIMPORTANT: Use inline citations [1], [2], [3] referencing the numbered source excerpts. Every factual claim needs a citation. At the end, suggest 2-3 follow-up questions."
            return DEFAULT_SYSTEM_PROMPT
    finally:
        conn.close()


def retrieve_context(library_id: int, query: str, limit: int = 10) -> list[dict]:
    """Retrieve relevant chunks with full metadata for citation cards."""
    embedding = embed_text(query)

    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT c.text, d.title, d.section, d.id as document_id,
                       d.page_start, d.page_end,
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
        {
            "text": row[0], "title": row[1], "section": row[2],
            "document_id": row[3], "page_start": row[4], "page_end": row[5],
            "similarity": round(float(row[6]), 4),
        }
        for row in rows
    ]


def _extract_suggestions(response_text: str) -> tuple[str, list[str]]:
    """Extract follow-up suggestions from the end of the LLM response."""
    suggestions = []
    lines = response_text.strip().split("\n")

    # Look for suggestion patterns at the end
    suggestion_start = None
    for i in range(len(lines) - 1, max(len(lines) - 8, -1), -1):
        line = lines[i].strip()
        if not line:
            continue
        # Match numbered or bulleted suggestion lines
        if any(line.startswith(p) for p in ["1.", "2.", "3.", "- ", "* ", "•"]):
            clean = line.lstrip("0123456789.-*• ").strip().rstrip("?") + "?"
            if len(clean) > 10:
                suggestions.insert(0, clean)
                suggestion_start = i
        elif suggestions and any(kw in line.lower() for kw in ["follow-up", "follow up", "you might", "questions"]):
            suggestion_start = i
            break
        elif suggestions:
            break

    # Remove suggestion section from answer
    if suggestion_start is not None and suggestions:
        answer = "\n".join(lines[:suggestion_start]).strip()
    else:
        answer = response_text.strip()

    return answer, suggestions[:3]


def _save_message(conn, conversation_id: str, role: str, content: str, sources: list | None = None):
    """Save a message to the conversation."""
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO messages (conversation_id, role, content, sources_json)
            VALUES (%s, %s, %s, %s)
        """, (conversation_id, role, content, json.dumps(sources) if sources else None))
        cur.execute(
            "UPDATE conversations SET updated_at = NOW() WHERE id = %s",
            (conversation_id,)
        )


# ── Chat Endpoint ────────────────────────────────────────────────────────────

@router.post("/libraries/{library_id}/chat", response_model=ChatResponse)
def chat_with_library(library_id: int, req: ChatRequest, request: Request):
    """RAG chat within a specific library with structured citations."""
    check_rate_limit(request, "chat")

    # Check library access
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SELECT * FROM libraries WHERE id = %s", (library_id,))
            lib_row = cur.fetchone()
            if not lib_row:
                raise HTTPException(status_code=404, detail="Library not found")
            check_library_read_access(dict(lib_row), request)
    finally:
        conn.close()

    # Handle conversation
    user = request.state.remote_user or None
    conversation_id = req.conversation_id

    conn = psycopg2.connect(DATABASE_URL)
    try:
        if conversation_id:
            # Verify conversation exists and belongs to this library
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id FROM conversations WHERE id = %s AND library_id = %s",
                    (conversation_id, library_id)
                )
                if not cur.fetchone():
                    raise HTTPException(status_code=404, detail="Conversation not found")
        else:
            # Create new conversation
            conversation_id = str(uuid.uuid4())
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO conversations (id, library_id, user_id, title)
                    VALUES (%s, %s, %s, %s)
                """, (conversation_id, library_id, user, req.message[:100]))
            conn.commit()

        # Save user message
        _save_message(conn, conversation_id, "user", req.message)
        conn.commit()
    finally:
        conn.close()

    # Retrieve context
    sources = retrieve_context(library_id, req.message, limit=req.context_limit)

    if not sources:
        empty_response = ChatResponse(
            answer="This library doesn't have any indexed content yet. Please upload some documents first.",
            sources=[],
            suggestions=[],
            conversation_id=conversation_id,
        )
        conn = psycopg2.connect(DATABASE_URL)
        try:
            _save_message(conn, conversation_id, "assistant", empty_response.answer)
            conn.commit()
        finally:
            conn.close()
        return empty_response

    # Build context block with numbered references
    context_parts = []
    for i, src in enumerate(sources, 1):
        label = src["title"]
        if src["section"] and src["section"] != src["title"]:
            label = f"{src['section']} — {src['title']}"
        page_info = ""
        if src.get("page_start"):
            page_info = f" (pp. {src['page_start']}-{src.get('page_end', src['page_start'])})"
        context_parts.append(f'[{i}] "{label}"{page_info}\n{src["text"]}')

    context_block = "\n\n---\n\n".join(context_parts)

    user_message = f"""Based on these numbered document excerpts, answer the question. Use inline citations [1], [2], etc. to reference sources.

DOCUMENT EXCERPTS:
{context_block}

QUESTION: {req.message}"""

    system_prompt = _get_library_persona(library_id)

    try:
        provider = get_provider()
        response_text = provider.generate(
            system=system_prompt,
            user=user_message,
            max_tokens=2000,
        )
    except Exception as e:
        err = str(e)
        if "credit balance" in err or "billing" in err.lower():
            raise HTTPException(status_code=402, detail="LLM API credit balance too low.")
        elif "api_key" in err.lower() or "authentication" in err.lower() or "401" in err:
            raise HTTPException(status_code=401, detail="Invalid or missing API key.")
        else:
            raise HTTPException(status_code=503, detail=f"LLM error: {err}")

    # Extract suggestions from response
    answer, suggestions = _extract_suggestions(response_text)

    # Build source details
    source_details = [
        SourceDetail(
            index=i + 1,
            title=s["title"],
            section=s["section"],
            text=s["text"],
            similarity=s["similarity"],
            document_id=s["document_id"],
            page_start=s.get("page_start"),
            page_end=s.get("page_end"),
        )
        for i, s in enumerate(sources[:10])
    ]

    # Save assistant message
    conn = psycopg2.connect(DATABASE_URL)
    try:
        _save_message(conn, conversation_id, "assistant", answer,
                       [{"index": s.index, "title": s.title, "section": s.section, "similarity": s.similarity}
                        for s in source_details])
        conn.commit()
    finally:
        conn.close()

    logger.info("chat_response", extra={"extra": {
        "library_id": library_id, "user": user or "anonymous",
        "sources": len(source_details), "conversation_id": conversation_id,
    }})

    return ChatResponse(
        answer=answer,
        sources=source_details,
        suggestions=suggestions,
        conversation_id=conversation_id,
    )


# ── Conversation Endpoints ───────────────────────────────────────────────────

@router.get("/libraries/{library_id}/conversations", response_model=list[ConversationSummary])
def list_conversations(library_id: int, request: Request):
    """List conversations for a library (user-scoped)."""
    user = request.state.remote_user
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            if user:
                cur.execute("""
                    SELECT c.id, c.title, c.created_at, c.updated_at,
                           COUNT(m.id) as message_count
                    FROM conversations c
                    LEFT JOIN messages m ON m.conversation_id = c.id
                    WHERE c.library_id = %s AND (c.user_id = %s OR c.user_id IS NULL)
                    GROUP BY c.id
                    ORDER BY c.updated_at DESC
                    LIMIT 50
                """, (library_id, user))
            else:
                # Anonymous: show anonymous conversations (limited)
                cur.execute("""
                    SELECT c.id, c.title, c.created_at, c.updated_at,
                           COUNT(m.id) as message_count
                    FROM conversations c
                    LEFT JOIN messages m ON m.conversation_id = c.id
                    WHERE c.library_id = %s AND c.user_id IS NULL
                    GROUP BY c.id
                    ORDER BY c.updated_at DESC
                    LIMIT 10
                """, (library_id,))
            rows = cur.fetchall()
    finally:
        conn.close()

    return [
        ConversationSummary(
            id=str(row["id"]),
            title=row["title"],
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
            message_count=row["message_count"],
        )
        for row in rows
    ]


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: str, request: Request):
    """Get a conversation with all its messages."""
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("""
                SELECT id, library_id, title, created_at
                FROM conversations WHERE id = %s
            """, (conversation_id,))
            conv = cur.fetchone()
            if not conv:
                raise HTTPException(status_code=404, detail="Conversation not found")

            # For multi-library conversations, fetch from join table
            library_ids = []
            if conv["library_id"] is None:
                cur.execute("""
                    SELECT library_id FROM conversation_libraries
                    WHERE conversation_id = %s ORDER BY library_id
                """, (conversation_id,))
                library_ids = [row["library_id"] for row in cur.fetchall()]

            cur.execute("""
                SELECT id, role, content, sources_json, created_at
                FROM messages
                WHERE conversation_id = %s
                ORDER BY created_at ASC
            """, (conversation_id,))
            msgs = cur.fetchall()
    finally:
        conn.close()

    return ConversationDetail(
        id=str(conv["id"]),
        library_id=conv["library_id"],
        library_ids=library_ids,
        title=conv["title"],
        created_at=str(conv["created_at"]),
        messages=[
            MessageDetail(
                id=str(m["id"]),
                role=m["role"],
                content=m["content"],
                sources_json=m["sources_json"],
                created_at=str(m["created_at"]),
            )
            for m in msgs
        ],
    )


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: str, request: Request):
    """Delete a conversation (owner or admin only)."""
    user = request.state.remote_user
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SELECT user_id FROM conversations WHERE id = %s", (conversation_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Conversation not found")
            if row["user_id"] and row["user_id"] != user and not is_admin(request):
                raise HTTPException(status_code=403, detail="Not your conversation")
            cur.execute("DELETE FROM conversations WHERE id = %s", (conversation_id,))
            conn.commit()
    finally:
        conn.close()

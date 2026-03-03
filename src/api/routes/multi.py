"""Multi-library search and chat — cross-library RAG with per-library attribution."""

import json
import logging
import uuid

import psycopg2
import psycopg2.extras
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from config.settings import DATABASE_URL
from src.embeddings.provider import embed_text
from src.llm.provider import get_provider
from src.api.auth import check_library_read_access
from src.api.rate_limit import check_rate_limit
from src.api.routes.chat import (
    DEFAULT_SYSTEM_PROMPT,
    ConversationSummary,
    SourceDetail,
    _extract_suggestions,
    _save_message,
)

router = APIRouter()
logger = logging.getLogger("athenaeum.multi")

MAX_LIBRARIES_PER_REQUEST = 20


# ── Request/Response Models ──────────────────────────────────────────────────

class MultiSearchRequest(BaseModel):
    query: str
    library_ids: list[int]
    limit: int = 20


class MultiSearchResult(BaseModel):
    chunk_id: int
    document_id: int
    document_title: str
    section: str | None
    text: str
    similarity: float
    library_id: int
    library_name: str
    library_slug: str


class MultiSearchResponse(BaseModel):
    query: str
    results: list[MultiSearchResult]
    total: int


class MultiChatRequest(BaseModel):
    message: str
    library_ids: list[int]
    context_limit: int = 10
    conversation_id: str | None = None


class MultiSourceDetail(BaseModel):
    index: int
    title: str
    section: str | None
    text: str
    similarity: float
    document_id: int
    page_start: int | None = None
    page_end: int | None = None
    library_id: int
    library_name: str
    library_slug: str


class MultiChatResponse(BaseModel):
    answer: str
    sources: list[MultiSourceDetail]
    suggestions: list[str]
    conversation_id: str


# ── Helpers ──────────────────────────────────────────────────────────────────

def _validate_library_ids(library_ids: list[int], request: Request) -> dict[int, dict]:
    """Validate and check access on all library IDs. Returns {id: row} mapping."""
    if not library_ids:
        raise HTTPException(status_code=400, detail="library_ids must not be empty")
    if len(library_ids) > MAX_LIBRARIES_PER_REQUEST:
        raise HTTPException(status_code=400, detail=f"Maximum {MAX_LIBRARIES_PER_REQUEST} libraries per request")

    unique_ids = list(set(library_ids))
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SELECT * FROM libraries WHERE id = ANY(%s)", (unique_ids,))
            rows = cur.fetchall()
    finally:
        conn.close()

    found = {row["id"]: dict(row) for row in rows}
    missing = [lid for lid in unique_ids if lid not in found]
    if missing:
        raise HTTPException(status_code=404, detail=f"Libraries not found: {missing}")

    for lib_row in found.values():
        check_library_read_access(lib_row, request)

    return found


def _multi_search(library_ids: list[int], query: str, limit: int) -> list[dict]:
    """Run a single pgvector query across multiple libraries."""
    embedding = embed_text(query)

    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT c.id, c.document_id, c.library_id, l.name, l.slug,
                       d.title, d.section, c.text,
                       d.page_start, d.page_end,
                       1 - (c.embedding <=> %s::vector) as similarity
                FROM chunks c
                JOIN documents d ON d.id = c.document_id
                JOIN libraries l ON l.id = c.library_id
                WHERE c.embedding IS NOT NULL AND c.library_id = ANY(%s)
                ORDER BY c.embedding <=> %s::vector
                LIMIT %s
            """, (str(embedding), library_ids, str(embedding), limit))
            rows = cur.fetchall()
    finally:
        conn.close()

    return [
        {
            "chunk_id": row[0],
            "document_id": row[1],
            "library_id": row[2],
            "library_name": row[3],
            "library_slug": row[4],
            "title": row[5],
            "section": row[6],
            "text": row[7],
            "page_start": row[8],
            "page_end": row[9],
            "similarity": round(float(row[10]), 4),
        }
        for row in rows
    ]


# ── Search Endpoint ──────────────────────────────────────────────────────────

@router.post("/search", response_model=MultiSearchResponse)
def multi_search(req: MultiSearchRequest, request: Request):
    """Semantic search across multiple libraries with per-library attribution."""
    check_rate_limit(request, "search")
    _validate_library_ids(req.library_ids, request)

    results = _multi_search(req.library_ids, req.query, req.limit)

    return MultiSearchResponse(
        query=req.query,
        results=[
            MultiSearchResult(
                chunk_id=r["chunk_id"],
                document_id=r["document_id"],
                document_title=r["title"],
                section=r["section"],
                text=r["text"],
                similarity=r["similarity"],
                library_id=r["library_id"],
                library_name=r["library_name"],
                library_slug=r["library_slug"],
            )
            for r in results
        ],
        total=len(results),
    )


# ── Chat Endpoint ────────────────────────────────────────────────────────────

@router.post("/chat", response_model=MultiChatResponse)
def multi_chat(req: MultiChatRequest, request: Request):
    """RAG chat across multiple libraries with cross-library citations."""
    check_rate_limit(request, "chat")
    _validate_library_ids(req.library_ids, request)

    user = request.state.remote_user or None
    conversation_id = req.conversation_id

    conn = psycopg2.connect(DATABASE_URL)
    try:
        if conversation_id:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id FROM conversations WHERE id = %s AND library_id IS NULL",
                    (conversation_id,)
                )
                if not cur.fetchone():
                    raise HTTPException(status_code=404, detail="Conversation not found")
        else:
            conversation_id = str(uuid.uuid4())
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO conversations (id, library_id, user_id, title)
                    VALUES (%s, NULL, %s, %s)
                """, (conversation_id, user, req.message[:100]))
                for lib_id in set(req.library_ids):
                    cur.execute("""
                        INSERT INTO conversation_libraries (conversation_id, library_id)
                        VALUES (%s, %s)
                    """, (conversation_id, lib_id))
            conn.commit()

        _save_message(conn, conversation_id, "user", req.message)
        conn.commit()
    finally:
        conn.close()

    # Retrieve context across libraries
    sources = _multi_search(req.library_ids, req.message, req.context_limit)

    if not sources:
        empty_answer = "The selected libraries don't have any indexed content yet. Please upload some documents first."
        conn = psycopg2.connect(DATABASE_URL)
        try:
            _save_message(conn, conversation_id, "assistant", empty_answer)
            conn.commit()
        finally:
            conn.close()
        return MultiChatResponse(
            answer=empty_answer, sources=[], suggestions=[], conversation_id=conversation_id
        )

    # Build context block with library attribution
    context_parts = []
    for i, src in enumerate(sources, 1):
        label = src["title"]
        if src["section"] and src["section"] != src["title"]:
            label = f"{src['section']} — {src['title']}"
        page_info = ""
        if src.get("page_start"):
            page_info = f" (pp. {src['page_start']}-{src.get('page_end', src['page_start'])})"
        context_parts.append(f'[{i}] "{label}" [{src["library_name"]}]{page_info}\n{src["text"]}')

    context_block = "\n\n---\n\n".join(context_parts)

    user_message = f"""Based on these numbered document excerpts from multiple libraries, answer the question. Use inline citations [1], [2], etc. to reference sources. Note which library each source comes from.

DOCUMENT EXCERPTS:
{context_block}

QUESTION: {req.message}"""

    try:
        provider = get_provider()
        response_text = provider.generate(
            system=DEFAULT_SYSTEM_PROMPT,
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

    answer, suggestions = _extract_suggestions(response_text)

    source_details = [
        MultiSourceDetail(
            index=i + 1,
            title=s["title"],
            section=s["section"],
            text=s["text"],
            similarity=s["similarity"],
            document_id=s["document_id"],
            page_start=s.get("page_start"),
            page_end=s.get("page_end"),
            library_id=s["library_id"],
            library_name=s["library_name"],
            library_slug=s["library_slug"],
        )
        for i, s in enumerate(sources[:10])
    ]

    conn = psycopg2.connect(DATABASE_URL)
    try:
        _save_message(conn, conversation_id, "assistant", answer,
                       [{"index": s.index, "title": s.title, "section": s.section,
                         "similarity": s.similarity, "library_name": s.library_name}
                        for s in source_details])
        conn.commit()
    finally:
        conn.close()

    logger.info("multi_chat_response", extra={"extra": {
        "library_ids": req.library_ids, "user": user or "anonymous",
        "sources": len(source_details), "conversation_id": conversation_id,
    }})

    return MultiChatResponse(
        answer=answer,
        sources=source_details,
        suggestions=suggestions,
        conversation_id=conversation_id,
    )


# ── Multi-library Conversations ──────────────────────────────────────────────

@router.get("/conversations", response_model=list[ConversationSummary])
def list_multi_conversations(request: Request):
    """List multi-library conversations (where library_id IS NULL)."""
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
                    WHERE c.library_id IS NULL AND (c.user_id = %s OR c.user_id IS NULL)
                    GROUP BY c.id
                    ORDER BY c.updated_at DESC
                    LIMIT 50
                """, (user,))
            else:
                cur.execute("""
                    SELECT c.id, c.title, c.created_at, c.updated_at,
                           COUNT(m.id) as message_count
                    FROM conversations c
                    LEFT JOIN messages m ON m.conversation_id = c.id
                    WHERE c.library_id IS NULL AND c.user_id IS NULL
                    GROUP BY c.id
                    ORDER BY c.updated_at DESC
                    LIMIT 10
                """)
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

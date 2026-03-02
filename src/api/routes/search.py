"""Semantic search within a library."""

import psycopg2
from fastapi import APIRouter, Query
from pydantic import BaseModel

from config.settings import DATABASE_URL
from src.embeddings.provider import embed_text

router = APIRouter()


class SearchResult(BaseModel):
    chunk_id: int
    document_id: int
    document_title: str
    section: str | None
    text: str
    similarity: float


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    total: int


@router.get("/libraries/{library_id}/search", response_model=SearchResponse)
def semantic_search(
    library_id: int,
    q: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=50),
):
    """Semantic search within a specific library."""
    embedding = embed_text(q)

    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT c.id, c.document_id, d.title, d.section, c.text,
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

    results = [
        SearchResult(
            chunk_id=row[0],
            document_id=row[1],
            document_title=row[2],
            section=row[3],
            text=row[4],
            similarity=round(float(row[5]), 4),
        )
        for row in rows
    ]

    return SearchResponse(query=q, results=results, total=len(results))

"""Browse documents within a library."""

import json

import psycopg2
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from config.settings import DATABASE_URL

router = APIRouter()


class DocumentSummary(BaseModel):
    id: int
    title: str
    section: str | None
    source: str | None
    word_count: int


class DocumentDetail(BaseModel):
    id: int
    title: str
    section: str | None
    full_text: str
    source: str | None
    page_start: int | None
    page_end: int | None


class TopicSummary(BaseModel):
    id: int
    name: str
    chunk_count: int
    document_count: int
    keywords: list[str]


@router.get("/libraries/{library_id}/documents", response_model=list[DocumentSummary])
def list_documents(
    library_id: int,
    search: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List documents in a library."""
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor() as cur:
            conditions = ["d.library_id = %s"]
            params: list = [library_id]

            if search:
                conditions.append("(d.title ILIKE %s OR d.full_text ILIKE %s)")
                params.extend([f"%{search}%", f"%{search}%"])

            where = "WHERE " + " AND ".join(conditions)
            params.extend([limit, offset])

            cur.execute(f"""
                SELECT d.id, d.title, d.section, s.name,
                       LENGTH(d.full_text) / 5 as word_count
                FROM documents d
                LEFT JOIN sources s ON s.id = d.source_id
                {where}
                ORDER BY d.title
                LIMIT %s OFFSET %s
            """, params)
            rows = cur.fetchall()
    finally:
        conn.close()

    return [
        DocumentSummary(
            id=row[0], title=row[1], section=row[2],
            source=row[3], word_count=row[4],
        )
        for row in rows
    ]


@router.get("/libraries/{library_id}/documents/{document_id}", response_model=DocumentDetail)
def get_document(library_id: int, document_id: int):
    """Get full document text."""
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT d.id, d.title, d.section, d.full_text,
                       s.name, d.page_start, d.page_end
                FROM documents d
                LEFT JOIN sources s ON s.id = d.source_id
                WHERE d.id = %s AND d.library_id = %s
            """, (document_id, library_id))
            row = cur.fetchone()
    finally:
        conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentDetail(
        id=row[0], title=row[1], section=row[2], full_text=row[3],
        source=row[4], page_start=row[5], page_end=row[6],
    )


@router.get("/libraries/{library_id}/topics", response_model=list[TopicSummary])
def list_topics(library_id: int):
    """List topics for a library."""
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT t.id, t.name, t.description,
                       COUNT(dt.document_id) as document_count
                FROM topics t
                LEFT JOIN document_topics dt ON dt.topic_id = t.id
                WHERE t.library_id = %s
                GROUP BY t.id, t.name, t.description
                ORDER BY t.name
            """, (library_id,))
            rows = cur.fetchall()
    finally:
        conn.close()

    results = []
    for row in rows:
        desc = json.loads(row[2]) if row[2] else {}
        results.append(TopicSummary(
            id=row[0],
            name=row[1],
            chunk_count=desc.get("chunk_count", 0),
            document_count=int(row[3]),
            keywords=desc.get("keywords", []),
        ))
    return results


@router.get("/libraries/{library_id}/info")
def get_library_info(library_id: int):
    """Library metadata + live corpus stats."""
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, slug, name, description, config FROM libraries WHERE id = %s", (library_id,))
            lib_row = cur.fetchone()
            if not lib_row:
                raise HTTPException(status_code=404, detail="Library not found")

            cur.execute("SELECT COUNT(*) FROM documents WHERE library_id = %s", (library_id,))
            doc_count = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM chunks WHERE library_id = %s AND embedding IS NOT NULL", (library_id,))
            chunk_count = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM topics WHERE library_id = %s", (library_id,))
            topic_count = cur.fetchone()[0]

            cur.execute("SELECT COUNT(DISTINCT section) FROM documents WHERE library_id = %s AND section IS NOT NULL", (library_id,))
            section_count = cur.fetchone()[0]
    finally:
        conn.close()

    config = lib_row[4] or {}

    return {
        "library": {
            "id": lib_row[0],
            "slug": lib_row[1],
            "name": lib_row[2],
            "description": lib_row[3],
        },
        "corpus": {
            "document_count": doc_count,
            "chunk_count": chunk_count,
            "topic_count": topic_count,
            "section_count": section_count,
        },
        "config": config,
    }

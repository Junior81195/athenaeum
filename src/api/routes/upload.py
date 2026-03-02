"""Document upload + auto-ingest pipeline."""

import hashlib
import os
import tempfile

import psycopg2
import psycopg2.extras
from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from pydantic import BaseModel

from config.settings import DATABASE_URL, DATA_DIR
from src.ingestion.pdf_loader import extract_sections_from_pdf, extract_text_from_file
from src.ingestion.chunker import chunk_text
from src.embeddings.provider import embed_texts

router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".text"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


class UploadResponse(BaseModel):
    filename: str
    sections_created: int
    chunks_created: int
    chunks_embedded: int


@router.post("/libraries/{library_id}/upload", response_model=UploadResponse)
async def upload_document(library_id: int, request: Request, file: UploadFile = File(...)):
    """Upload a PDF or text file, extract text, chunk, and embed."""
    # Validate library exists
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, slug FROM libraries WHERE id = %s", (library_id,))
            lib_row = cur.fetchone()
            if not lib_row:
                raise HTTPException(status_code=404, detail="Library not found")
            lib_slug = lib_row[1]
    finally:
        conn.close()

    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")

    # Read file content
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 50MB)")

    # Save to data/{library_slug}/
    lib_data_dir = os.path.join(DATA_DIR, lib_slug)
    os.makedirs(lib_data_dir, exist_ok=True)
    file_path = os.path.join(lib_data_dir, file.filename)
    with open(file_path, "wb") as f:
        f.write(content)

    # Extract sections
    try:
        if ext == ".pdf":
            sections = extract_sections_from_pdf(file_path)
        else:
            sections = extract_text_from_file(file_path)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to extract text: {e}")

    if not sections:
        raise HTTPException(status_code=422, detail="No text content extracted from file")

    # Create source record
    conn = psycopg2.connect(DATABASE_URL)
    sections_created = 0
    chunks_created = 0
    chunks_embedded = 0
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO sources (library_id, name, source_type, scraped_at)
                VALUES (%s, %s, %s, NOW()) RETURNING id
            """, (library_id, file.filename, "upload"))
            source_id = cur.fetchone()[0]

            for section in sections:
                # SHA-256 dedup
                content_hash = hashlib.sha256(section["text"].encode()).hexdigest()

                # Check for existing document with same hash in this library
                cur.execute(
                    "SELECT id FROM documents WHERE library_id = %s AND content_hash = %s",
                    (library_id, content_hash)
                )
                if cur.fetchone():
                    continue  # Skip duplicate

                # Insert document
                cur.execute("""
                    INSERT INTO documents (library_id, source_id, title, section, full_text,
                                          page_start, page_end, content_hash)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
                """, (library_id, source_id, section["title"], section.get("title"),
                      section["text"], section.get("page_start"), section.get("page_end"),
                      content_hash))
                doc_id = cur.fetchone()[0]
                sections_created += 1

                # Chunk the document
                chunks = chunk_text(section["text"])
                chunk_texts = []
                chunk_records = []

                for chunk in chunks:
                    cur.execute("""
                        INSERT INTO chunks (library_id, document_id, chunk_index, text, token_count)
                        VALUES (%s, %s, %s, %s, %s) RETURNING id
                    """, (library_id, doc_id, chunk["chunk_index"],
                          chunk["text"], chunk["token_count"]))
                    chunk_id = cur.fetchone()[0]
                    chunk_texts.append(chunk["text"])
                    chunk_records.append(chunk_id)
                    chunks_created += 1

                # Embed chunks in batches using local model
                if chunk_texts:
                    batch_size = 32
                    for i in range(0, len(chunk_texts), batch_size):
                        batch_texts = chunk_texts[i:i + batch_size]
                        batch_ids = chunk_records[i:i + batch_size]
                        embeddings = embed_texts(batch_texts)
                        for cid, emb in zip(batch_ids, embeddings):
                            cur.execute(
                                "UPDATE chunks SET embedding = %s WHERE id = %s",
                                (str(emb), cid)
                            )
                            chunks_embedded += 1

            conn.commit()
    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")
    finally:
        conn.close()

    return UploadResponse(
        filename=file.filename,
        sections_created=sections_created,
        chunks_created=chunks_created,
        chunks_embedded=chunks_embedded,
    )

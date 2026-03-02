-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Libraries table (each library is a namespace)
CREATE TABLE IF NOT EXISTS libraries (
    id SERIAL PRIMARY KEY,
    slug VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    owner VARCHAR(255),
    config JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Sources table
CREATE TABLE IF NOT EXISTS sources (
    id SERIAL PRIMARY KEY,
    library_id INTEGER REFERENCES libraries(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    url TEXT,
    source_type VARCHAR(50) NOT NULL,
    scraped_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Documents table (full documents — renamed from transcripts for multi-library clarity)
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    library_id INTEGER NOT NULL REFERENCES libraries(id) ON DELETE CASCADE,
    source_id INTEGER REFERENCES sources(id),
    title VARCHAR(500) NOT NULL,
    section VARCHAR(255),
    full_text TEXT NOT NULL,
    page_start INTEGER,
    page_end INTEGER,
    content_hash VARCHAR(64) NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(library_id, content_hash)
);

-- Chunks table (for vector search)
CREATE TABLE IF NOT EXISTS chunks (
    id SERIAL PRIMARY KEY,
    library_id INTEGER NOT NULL REFERENCES libraries(id) ON DELETE CASCADE,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    token_count INTEGER,
    embedding vector(768),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create HNSW index for fast similarity search
CREATE INDEX IF NOT EXISTS chunks_embedding_idx
    ON chunks USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Library-scoped indexes
CREATE INDEX IF NOT EXISTS idx_sources_library ON sources(library_id);
CREATE INDEX IF NOT EXISTS idx_documents_library ON documents(library_id);
CREATE INDEX IF NOT EXISTS idx_documents_section ON documents(section);
CREATE INDEX IF NOT EXISTS idx_documents_hash ON documents(content_hash);
CREATE INDEX IF NOT EXISTS idx_chunks_library ON chunks(library_id);
CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id);

-- Topics table (auto-tagged, per library)
CREATE TABLE IF NOT EXISTS topics (
    id SERIAL PRIMARY KEY,
    library_id INTEGER NOT NULL REFERENCES libraries(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(library_id, name)
);

-- Many-to-many: documents <-> topics
CREATE TABLE IF NOT EXISTS document_topics (
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    topic_id INTEGER REFERENCES topics(id) ON DELETE CASCADE,
    relevance_score FLOAT DEFAULT 0.0,
    PRIMARY KEY (document_id, topic_id)
);

CREATE INDEX IF NOT EXISTS idx_topics_library ON topics(library_id);

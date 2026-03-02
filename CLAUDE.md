# Athenaeum

> Personal semantic library platform — upload documents, search semantically, chat with AI.

Named for the Temple of Athena — the classical word for a library or reading room.

## Quick Start

```bash
source ~/.secrets/hercules.env    # REQUIRED before any docker/db commands

make run                          # Start all 3 services (db + api + frontend)
make build                        # Rebuild all containers
make dev                          # Local API hot-reload on port 8140
make logs                         # Tail API logs
make stop                         # Stop all containers
```

## Architecture

```
Upload PDF/text → Extract sections (pdfplumber) → Chunk (500 tokens, 50 overlap)
  → Embed (all-mpnet-base-v2, 768d, local) → pgvector HNSW cosine index
  → Semantic search → Top-k chunks + parent documents
  → RAG prompt (per-library persona from config JSONB) → LLM (free-llm gateway)
  → Response grounded in actual document excerpts
```

Multi-library: all content tables have `library_id` FK with CASCADE delete. Libraries are fully isolated namespaces.

## API (port 8140)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Health check |
| GET | `/api/libraries` | List all libraries |
| POST | `/api/libraries` | Create library `{name, slug, description, config}` |
| GET | `/api/libraries/{id}` | Library detail + corpus stats |
| GET | `/api/libraries/by-slug/{slug}` | Get library by URL slug |
| PATCH | `/api/libraries/{id}` | Update library (owner/admin) |
| DELETE | `/api/libraries/{id}` | Delete library + all content (owner/admin) |
| POST | `/api/libraries/{id}/upload` | Upload PDF/TXT/MD → auto-ingest |
| GET | `/api/libraries/{id}/search?q=...` | Semantic search within library |
| POST | `/api/libraries/{id}/chat` | RAG chat `{message, context_limit}` |
| GET | `/api/libraries/{id}/documents` | Browse documents |
| GET | `/api/libraries/{id}/documents/{doc_id}` | Full document text |
| GET | `/api/libraries/{id}/topics` | Auto-discovered topics |
| GET | `/api/libraries/{id}/info` | Library metadata + live corpus stats |
| GET | `/api/settings` | Current LLM config |

## Project Structure

```
config/
├── init.sql             # Multi-library schema (libraries, documents, chunks, topics)
└── settings.py          # DATABASE_URL, LLM config, embedding model
src/
├── api/main.py          # FastAPI app + Authelia auth middleware
├── api/routes/
│   ├── libraries.py     # Library CRUD
│   ├── upload.py        # PDF upload + auto-ingest pipeline
│   ├── search.py        # Semantic search (pgvector cosine)
│   ├── chat.py          # RAG chat with per-library persona
│   ├── browse.py        # Document browsing + topics + info
│   └── settings.py      # LLM provider config
├── embeddings/provider.py  # Singleton SentenceTransformer (all-mpnet-base-v2)
├── ingestion/
│   ├── pdf_loader.py    # PDF section extraction (pdfplumber)
│   ├── chunker.py       # Token-based text chunking
│   ├── embed.py         # Batch embedding (Gemini)
│   └── embed_local.py   # Local embedding (sentence-transformers)
├── llm/provider.py      # Abstract LLM + 5 providers
└── db.py                # Shared connection helper
frontend/
├── app/
│   ├── page.tsx                        # Library catalog (homepage)
│   └── library/[slug]/
│       ├── page.tsx                    # Library dashboard
│       ├── chat/page.tsx               # RAG chat interface
│       └── upload/page.tsx             # Document upload
├── components/Nav.tsx                  # Breadcrumb navigation
└── lib/api.ts                          # All API calls (typed)
tests/                                  # Pytest suite
```

## Database

```
PostgreSQL 16 + pgvector @ 127.0.0.1:5442

libraries   → namespace table (slug, name, config JSONB)
documents   → full document text (library_id FK, content_hash dedup)
chunks      → vectorized text (embedding vector(768), HNSW index)
topics      → auto-discovered topics per library
```

```bash
source ~/.secrets/hercules.env
docker compose exec db psql -U athenaeum athenaeum
```

## Auth

Authelia SSO via nginx. Headers injected into every request:
- `Remote-User` → `request.state.remote_user`
- `Remote-Groups` → `request.state.remote_groups`

Library ownership: only the owner or `admins` group can update/delete.

## Environment

```bash
# Required
ATHENAEUM_DB_PASSWORD=...

# LLM (defaults wired in docker-compose.yml)
LLM_PROVIDER=openai        # Uses free-llm gateway
LLM_MODEL=auto
LLM_API_KEY=free
LLM_BASE_URL=http://free_llm_api:8000/v1
```

## Testing

```bash
pytest tests/ -v                  # All tests (requires running containers)
pytest tests/test_api.py -v       # API smoke tests
```

## Deployment

```bash
source ~/.secrets/hercules.env

# Full rebuild with production URL baked into Next.js:
NEXT_PUBLIC_API_URL=https://athenaeum.herakles.dev docker compose up -d --build

# Just restart API (picks up src/ changes via volume mount):
docker compose restart api
```

**URLs**: `https://athenaeum.herakles.dev` | API: `127.0.0.1:8140` | DB: `127.0.0.1:5442` | Frontend: `127.0.0.1:3140`

## Extension Patterns

### Add an API Route
1. Create `src/api/routes/myroute.py`
2. Register in `src/api/main.py`: `app.include_router(myroute.router, prefix="/api")`
3. Add types + fetch call in `frontend/lib/api.ts`

### Add a Frontend Page
1. Create `frontend/app/mypage/page.tsx` (Next.js App Router)
2. Add nav link in `frontend/components/Nav.tsx`
3. Use CSS vars: `var(--bg)` `var(--accent)` and classes: `.card` `.btn` `.badge`

## Critical Rules

### MUST
- `source ~/.secrets/hercules.env` before docker/db commands
- Read files before editing
- DB binds to `127.0.0.1` only — never `0.0.0.0`
- `NEXT_PUBLIC_API_URL` must be set at build time (baked into client bundle)

### NEVER
- Expose database port to internet
- Hardcode API keys or passwords
- Create docs files unless asked

---

**Port**: 8140 | **Status**: active | **Forked from**: alan-watts scaffold

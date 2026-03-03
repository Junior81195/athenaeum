"""Athenaeum MCP Server — read-only access to semantic libraries.

Exposes tools for listing libraries, searching content, chatting with AI,
browsing documents, and reading full document text.

Usage:
    python -m src.mcp_server

Transport: stdio (local only, no auth needed)
"""

import json
import os
import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

API_BASE = os.environ.get("ATHENAEUM_API_URL", "http://127.0.0.1:8140")

server = Server("athenaeum")


def _get(path: str, params: dict | None = None) -> dict | list:
    with httpx.Client(timeout=30.0) as client:
        r = client.get(f"{API_BASE}{path}", params=params)
        r.raise_for_status()
        return r.json()


def _post(path: str, body: dict) -> dict:
    with httpx.Client(timeout=120.0) as client:
        r = client.post(f"{API_BASE}{path}", json=body)
        r.raise_for_status()
        return r.json()


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="athenaeum_list_libraries",
            description="List all public Athenaeum libraries with document and chunk counts.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="athenaeum_search",
            description="Semantic search within an Athenaeum library. Returns relevant document chunks ranked by similarity.",
            inputSchema={
                "type": "object",
                "properties": {
                    "library_id": {
                        "type": "integer",
                        "description": "Library ID to search in (get from athenaeum_list_libraries)",
                    },
                    "query": {
                        "type": "string",
                        "description": "Natural language search query",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results (default 5)",
                        "default": 5,
                    },
                },
                "required": ["library_id", "query"],
            },
        ),
        Tool(
            name="athenaeum_chat",
            description="Chat with an Athenaeum library using RAG. AI answers are grounded in document content with source citations.",
            inputSchema={
                "type": "object",
                "properties": {
                    "library_id": {
                        "type": "integer",
                        "description": "Library ID to chat with",
                    },
                    "message": {
                        "type": "string",
                        "description": "Question to ask the library",
                    },
                    "context_limit": {
                        "type": "integer",
                        "description": "Number of source chunks to use (default 8)",
                        "default": 8,
                    },
                },
                "required": ["library_id", "message"],
            },
        ),
        Tool(
            name="athenaeum_browse",
            description="Browse documents and topics in an Athenaeum library.",
            inputSchema={
                "type": "object",
                "properties": {
                    "library_id": {
                        "type": "integer",
                        "description": "Library ID to browse",
                    },
                    "search": {
                        "type": "string",
                        "description": "Optional text search filter for document titles",
                    },
                },
                "required": ["library_id"],
            },
        ),
        Tool(
            name="athenaeum_read_document",
            description="Read the full text of a specific document in an Athenaeum library.",
            inputSchema={
                "type": "object",
                "properties": {
                    "library_id": {
                        "type": "integer",
                        "description": "Library ID containing the document",
                    },
                    "document_id": {
                        "type": "integer",
                        "description": "Document ID to read (get from athenaeum_browse or athenaeum_search)",
                    },
                },
                "required": ["library_id", "document_id"],
            },
        ),
        Tool(
            name="athenaeum_multi_search",
            description="Semantic search across multiple Athenaeum libraries at once. Returns results with per-library attribution.",
            inputSchema={
                "type": "object",
                "properties": {
                    "library_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Library IDs to search across (get from athenaeum_list_libraries)",
                    },
                    "query": {
                        "type": "string",
                        "description": "Natural language search query",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results (default 10)",
                        "default": 10,
                    },
                },
                "required": ["library_ids", "query"],
            },
        ),
        Tool(
            name="athenaeum_multi_chat",
            description="Chat across multiple Athenaeum libraries using RAG. AI answers are grounded in content from all selected libraries with cross-library source citations.",
            inputSchema={
                "type": "object",
                "properties": {
                    "library_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Library IDs to chat across",
                    },
                    "message": {
                        "type": "string",
                        "description": "Question to ask across the libraries",
                    },
                    "context_limit": {
                        "type": "integer",
                        "description": "Number of source chunks to use (default 8)",
                        "default": 8,
                    },
                },
                "required": ["library_ids", "message"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "athenaeum_list_libraries":
            libs = _get("/api/libraries")
            lines = []
            for lib in libs:
                lines.append(
                    f"[{lib['id']}] {lib['name']} (/{lib['slug']}) — "
                    f"{lib['document_count']} docs, {lib['chunk_count']} chunks"
                )
                if lib.get("description"):
                    lines.append(f"    {lib['description'][:120]}")
            return [TextContent(type="text", text="\n".join(lines) or "No libraries found.")]

        elif name == "athenaeum_search":
            lib_id = arguments["library_id"]
            query = arguments["query"]
            limit = arguments.get("limit", 5)
            data = _get(f"/api/libraries/{lib_id}/search", {"q": query, "limit": limit})
            results = data.get("results", [])
            lines = [f"Search: \"{data.get('query', query)}\" — {len(results)} results\n"]
            for r in results:
                sim = round(r["similarity"] * 100, 1)
                lines.append(f"[{sim}%] {r['document_title']}")
                if r.get("section"):
                    lines.append(f"  Section: {r['section']}")
                lines.append(f"  Doc ID: {r['document_id']}")
                lines.append(f"  {r['text'][:300]}...")
                lines.append("")
            return [TextContent(type="text", text="\n".join(lines))]

        elif name == "athenaeum_chat":
            lib_id = arguments["library_id"]
            message = arguments["message"]
            context_limit = arguments.get("context_limit", 8)
            data = _post(f"/api/libraries/{lib_id}/chat", {
                "message": message,
                "context_limit": context_limit,
            })
            parts = [data.get("answer", "No answer")]
            sources = data.get("sources", [])
            if sources:
                parts.append("\n--- Sources ---")
                for s in sources[:5]:
                    sim = round(s["similarity"] * 100, 1)
                    parts.append(f"[{s['index']}] {s['title']} ({sim}%)")
                    if s.get("section"):
                        parts.append(f"    Section: {s['section']}")
            suggestions = data.get("suggestions", [])
            if suggestions:
                parts.append("\n--- Follow-up questions ---")
                for i, q in enumerate(suggestions, 1):
                    parts.append(f"{i}. {q}")
            return [TextContent(type="text", text="\n".join(parts))]

        elif name == "athenaeum_browse":
            lib_id = arguments["library_id"]
            search = arguments.get("search")
            params = {}
            if search:
                params["search"] = search
            docs = _get(f"/api/libraries/{lib_id}/documents", params)
            topics = _get(f"/api/libraries/{lib_id}/topics")

            lines = [f"Library {lib_id}: {len(docs)} documents, {len(topics)} topics\n"]

            if topics:
                lines.append("--- Topics ---")
                for t in topics:
                    kw = ", ".join(t.get("keywords", [])[:5])
                    lines.append(f"  {t['name']} ({t['chunk_count']} chunks) — {kw}")
                lines.append("")

            lines.append("--- Documents ---")
            for d in docs[:30]:
                lines.append(f"  [{d['id']}] {d['title']} ({d['word_count']} words)")
                if d.get("section"):
                    lines.append(f"       Section: {d['section']}")

            if len(docs) > 30:
                lines.append(f"  ... and {len(docs) - 30} more")
            return [TextContent(type="text", text="\n".join(lines))]

        elif name == "athenaeum_read_document":
            lib_id = arguments["library_id"]
            doc_id = arguments["document_id"]
            doc = _get(f"/api/libraries/{lib_id}/documents/{doc_id}")
            header = f"# {doc['title']}"
            if doc.get("section"):
                header += f"\nSection: {doc['section']}"
            if doc.get("page_start"):
                header += f"\nPages: {doc['page_start']}-{doc.get('page_end', doc['page_start'])}"
            return [TextContent(type="text", text=f"{header}\n\n{doc['full_text']}")]

        elif name == "athenaeum_multi_search":
            lib_ids = arguments["library_ids"]
            query = arguments["query"]
            limit = arguments.get("limit", 10)
            data = _post("/api/search", {
                "query": query, "library_ids": lib_ids, "limit": limit,
            })
            results = data.get("results", [])
            lines = [f"Multi-search: \"{data.get('query', query)}\" across {len(lib_ids)} libraries — {len(results)} results\n"]
            for r in results:
                sim = round(r["similarity"] * 100, 1)
                lines.append(f"[{sim}%] {r['document_title']}  [{r['library_name']}]")
                if r.get("section"):
                    lines.append(f"  Section: {r['section']}")
                lines.append(f"  Doc ID: {r['document_id']} | Library: {r['library_slug']}")
                lines.append(f"  {r['text'][:300]}...")
                lines.append("")
            return [TextContent(type="text", text="\n".join(lines))]

        elif name == "athenaeum_multi_chat":
            lib_ids = arguments["library_ids"]
            message = arguments["message"]
            context_limit = arguments.get("context_limit", 8)
            data = _post("/api/chat", {
                "message": message,
                "library_ids": lib_ids,
                "context_limit": context_limit,
            })
            parts = [data.get("answer", "No answer")]
            sources = data.get("sources", [])
            if sources:
                parts.append("\n--- Sources ---")
                for s in sources[:5]:
                    sim = round(s["similarity"] * 100, 1)
                    lib_label = f" [{s.get('library_name', '')}]" if s.get("library_name") else ""
                    parts.append(f"[{s['index']}] {s['title']}{lib_label} ({sim}%)")
                    if s.get("section"):
                        parts.append(f"    Section: {s['section']}")
            suggestions = data.get("suggestions", [])
            if suggestions:
                parts.append("\n--- Follow-up questions ---")
                for i, q in enumerate(suggestions, 1):
                    parts.append(f"{i}. {q}")
            return [TextContent(type="text", text="\n".join(parts))]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except httpx.HTTPStatusError as e:
        return [TextContent(type="text", text=f"API error {e.response.status_code}: {e.response.text[:200]}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

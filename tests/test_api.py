"""API integration tests.

Run:  pytest tests/test_api.py -v
Req:  docker compose up -d db api   (live DB + API required)
"""

import os
import time
import pytest
import httpx

BASE = os.environ.get("TEST_API_URL", "http://127.0.0.1:8140")

# Auth headers to simulate Authelia SSO (for write operations)
AUTH_HEADERS = {
    "Remote-User": "test-user",
    "Remote-Groups": "admins",
    "Remote-Name": "Test User",
    "Remote-Email": "test@herakles.dev",
}

# Use a longer timeout for LLM-based endpoints
client = httpx.Client(base_url=BASE, timeout=120.0, headers=AUTH_HEADERS)


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def test_library():
    """Create a test library, yield it, then clean up."""
    slug = f"test-lib-{int(time.time())}"
    r = client.post("/api/libraries", json={
        "name": "Test Library",
        "slug": slug,
        "description": "Integration test library",
        "visibility": "public",
    })
    assert r.status_code == 201, f"Failed to create test library: {r.text}"
    lib = r.json()
    yield lib
    # Cleanup
    client.delete(f"/api/libraries/{lib['id']}")


@pytest.fixture(scope="module")
def uploaded_doc(test_library):
    """Upload a test text file to the test library and return the response."""
    lib_id = test_library["id"]
    content = """# Employment Law Overview

## Minimum Wage
The federal minimum wage is $7.25 per hour. Many states have higher minimum wages.
Illinois has a minimum wage of $14.00 per hour as of 2024.
Chicago has a minimum wage of $15.80 per hour for large employers.

## Overtime Pay
The Fair Labor Standards Act requires employers to pay overtime at 1.5 times the regular
rate for hours worked over 40 in a workweek. Some employees are exempt from overtime,
including executive, administrative, and professional employees.

## Family and Medical Leave
The Family and Medical Leave Act (FMLA) provides eligible employees with up to 12 weeks
of unpaid, job-protected leave per year for qualifying family and medical reasons.

## Workers' Compensation
Workers' compensation provides benefits to employees who are injured on the job.
Benefits typically include medical expenses, lost wages, and disability benefits.

## Anti-Discrimination Laws
Title VII of the Civil Rights Act prohibits employment discrimination based on race,
color, religion, sex, or national origin. The Americans with Disabilities Act (ADA)
prohibits discrimination against qualified individuals with disabilities.
"""
    files = {"file": ("test-employment-law.txt", content.encode(), "text/plain")}
    r = client.post(f"/api/libraries/{lib_id}/upload", files=files)
    assert r.status_code == 200, f"Upload failed: {r.text}"
    data = r.json()
    assert data["chunks_created"] > 0
    assert data["chunks_embedded"] > 0
    return data


# ── Health ──────────────────────────────────────────────────────────────────

class TestHealth:
    def test_health_endpoint(self):
        r = client.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "healthy"
        assert body["service"] == "athenaeum"


# ── Libraries ───────────────────────────────────────────────────────────────

class TestLibraries:
    def test_list_libraries(self):
        r = client.get("/api/libraries")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_and_delete_library(self):
        slug = f"crud-test-{int(time.time())}"
        r = client.post("/api/libraries", json={
            "name": "CRUD Test", "slug": slug, "description": "For testing",
        })
        assert r.status_code == 201
        lib = r.json()
        assert lib["slug"] == slug
        assert lib["name"] == "CRUD Test"
        assert lib["document_count"] == 0
        assert lib["chunk_count"] == 0
        lib_id = lib["id"]

        # Get by slug
        r = client.get(f"/api/libraries/by-slug/{slug}")
        assert r.status_code == 200
        assert r.json()["id"] == lib_id

        # Get by ID
        r = client.get(f"/api/libraries/{lib_id}")
        assert r.status_code == 200
        assert r.json()["slug"] == slug

        # Delete
        r = client.delete(f"/api/libraries/{lib_id}")
        assert r.status_code == 204

        # Verify deleted
        r = client.get(f"/api/libraries/{lib_id}")
        assert r.status_code == 404

    def test_create_duplicate_slug(self):
        slug = f"dup-test-{int(time.time())}"
        r1 = client.post("/api/libraries", json={"name": "Dup", "slug": slug})
        assert r1.status_code == 201

        r2 = client.post("/api/libraries", json={"name": "Dup 2", "slug": slug})
        assert r2.status_code == 409

        # Cleanup
        client.delete(f"/api/libraries/{r1.json()['id']}")

    def test_update_library(self):
        slug = f"update-test-{int(time.time())}"
        r = client.post("/api/libraries", json={"name": "Before", "slug": slug})
        lib_id = r.json()["id"]

        r = client.patch(f"/api/libraries/{lib_id}", json={"name": "After", "description": "Updated"})
        assert r.status_code == 200
        assert r.json()["name"] == "After"
        assert r.json()["description"] == "Updated"

        client.delete(f"/api/libraries/{lib_id}")

    def test_library_not_found(self):
        r = client.get("/api/libraries/99999")
        assert r.status_code == 404

    def test_slug_not_found(self):
        r = client.get("/api/libraries/by-slug/nonexistent-slug-12345")
        assert r.status_code == 404


# ── Upload ──────────────────────────────────────────────────────────────────

class TestUpload:
    def test_upload_text_file(self, test_library, uploaded_doc):
        """uploaded_doc fixture already validates the upload."""
        assert uploaded_doc["filename"] == "test-employment-law.txt"
        assert uploaded_doc["sections_created"] >= 1
        assert uploaded_doc["chunks_created"] >= 1
        assert uploaded_doc["chunks_embedded"] >= 1

    def test_upload_duplicate_skips(self, test_library, uploaded_doc):
        """Re-uploading same content should skip duplicate chunks."""
        lib_id = test_library["id"]
        content = """# Employment Law Overview

## Minimum Wage
The federal minimum wage is $7.25 per hour. Many states have higher minimum wages.
Illinois has a minimum wage of $14.00 per hour as of 2024.
Chicago has a minimum wage of $15.80 per hour for large employers.

## Overtime Pay
The Fair Labor Standards Act requires employers to pay overtime at 1.5 times the regular
rate for hours worked over 40 in a workweek. Some employees are exempt from overtime,
including executive, administrative, and professional employees.

## Family and Medical Leave
The Family and Medical Leave Act (FMLA) provides eligible employees with up to 12 weeks
of unpaid, job-protected leave per year for qualifying family and medical reasons.

## Workers' Compensation
Workers' compensation provides benefits to employees who are injured on the job.
Benefits typically include medical expenses, lost wages, and disability benefits.

## Anti-Discrimination Laws
Title VII of the Civil Rights Act prohibits employment discrimination based on race,
color, religion, sex, or national origin. The Americans with Disabilities Act (ADA)
prohibits discrimination against qualified individuals with disabilities.
"""
        files = {"file": ("test-employment-law.txt", content.encode(), "text/plain")}
        r = client.post(f"/api/libraries/{lib_id}/upload", files=files)
        assert r.status_code == 200
        data = r.json()
        # SHA-256 dedup should skip all sections
        assert data["sections_created"] == 0

    def test_upload_invalid_extension(self, test_library):
        lib_id = test_library["id"]
        files = {"file": ("test.exe", b"binary data", "application/octet-stream")}
        r = client.post(f"/api/libraries/{lib_id}/upload", files=files)
        assert r.status_code == 400
        assert "Unsupported file type" in r.json()["detail"]

    def test_upload_to_nonexistent_library(self):
        files = {"file": ("test.txt", b"hello world", "text/plain")}
        r = client.post("/api/libraries/99999/upload", files=files)
        assert r.status_code in (401, 404)

    def test_upload_empty_file(self, test_library):
        lib_id = test_library["id"]
        files = {"file": ("empty.txt", b"", "text/plain")}
        r = client.post(f"/api/libraries/{lib_id}/upload", files=files)
        assert r.status_code == 422


# ── Search ──────────────────────────────────────────────────────────────────

class TestSearch:
    def test_search_returns_results(self, test_library, uploaded_doc):
        lib_id = test_library["id"]
        r = client.get(f"/api/libraries/{lib_id}/search", params={"q": "minimum wage", "limit": 5})
        assert r.status_code == 200
        data = r.json()
        assert data["query"] == "minimum wage"
        assert len(data["results"]) > 0
        assert data["total"] > 0

    def test_search_result_structure(self, test_library, uploaded_doc):
        lib_id = test_library["id"]
        r = client.get(f"/api/libraries/{lib_id}/search", params={"q": "overtime pay", "limit": 3})
        data = r.json()
        if data["results"]:
            result = data["results"][0]
            assert "chunk_id" in result
            assert "document_id" in result
            assert "document_title" in result
            assert "text" in result
            assert "similarity" in result
            assert 0 <= result["similarity"] <= 1

    def test_search_relevance(self, test_library, uploaded_doc):
        """Top result for 'minimum wage' should mention wage."""
        lib_id = test_library["id"]
        r = client.get(f"/api/libraries/{lib_id}/search", params={"q": "minimum wage", "limit": 1})
        data = r.json()
        if data["results"]:
            text = data["results"][0]["text"].lower()
            assert "wage" in text or "minimum" in text

    def test_search_limit_param(self, test_library, uploaded_doc):
        lib_id = test_library["id"]
        r = client.get(f"/api/libraries/{lib_id}/search", params={"q": "law", "limit": 2})
        data = r.json()
        assert len(data["results"]) <= 2

    def test_search_nonexistent_library(self):
        r = client.get("/api/libraries/99999/search", params={"q": "test"})
        assert r.status_code == 404

    def test_search_missing_query(self, test_library):
        lib_id = test_library["id"]
        r = client.get(f"/api/libraries/{lib_id}/search")
        assert r.status_code == 422  # FastAPI validation — q is required


# ── Chat ────────────────────────────────────────────────────────────────────

class TestChat:
    def test_chat_basic(self, test_library, uploaded_doc):
        lib_id = test_library["id"]
        r = client.post(f"/api/libraries/{lib_id}/chat", json={
            "message": "What is the minimum wage?",
        })
        assert r.status_code == 200
        data = r.json()
        assert "answer" in data
        assert "sources" in data
        assert "suggestions" in data
        assert "conversation_id" in data
        assert len(data["answer"]) > 0
        assert len(data["sources"]) > 0

    def test_chat_response_structure(self, test_library, uploaded_doc):
        lib_id = test_library["id"]
        r = client.post(f"/api/libraries/{lib_id}/chat", json={
            "message": "Tell me about overtime",
        })
        data = r.json()
        # Check source structure
        if data["sources"]:
            src = data["sources"][0]
            assert "index" in src
            assert "title" in src
            assert "text" in src
            assert "similarity" in src
            assert "document_id" in src
            assert src["index"] >= 1

    def test_chat_conversation_persistence(self, test_library, uploaded_doc):
        lib_id = test_library["id"]
        # First message creates conversation
        r1 = client.post(f"/api/libraries/{lib_id}/chat", json={
            "message": "What is FMLA?",
        })
        data1 = r1.json()
        conv_id = data1["conversation_id"]
        assert conv_id

        # Follow-up in same conversation
        r2 = client.post(f"/api/libraries/{lib_id}/chat", json={
            "message": "How many weeks of leave?",
            "conversation_id": conv_id,
        })
        data2 = r2.json()
        assert data2["conversation_id"] == conv_id

        # Retrieve conversation
        r3 = client.get(f"/api/conversations/{conv_id}")
        assert r3.status_code == 200
        conv = r3.json()
        assert len(conv["messages"]) >= 4  # 2 user + 2 assistant

        # List conversations
        r4 = client.get(f"/api/libraries/{lib_id}/conversations")
        assert r4.status_code == 200
        convs = r4.json()
        conv_ids = [c["id"] for c in convs]
        assert conv_id in conv_ids

        # Delete conversation
        r5 = client.delete(f"/api/conversations/{conv_id}")
        assert r5.status_code == 204

    def test_chat_nonexistent_library(self):
        r = client.post("/api/libraries/99999/chat", json={"message": "hello"})
        assert r.status_code == 404

    def test_chat_context_limit(self, test_library, uploaded_doc):
        lib_id = test_library["id"]
        r = client.post(f"/api/libraries/{lib_id}/chat", json={
            "message": "Summarize employment law",
            "context_limit": 3,
        })
        data = r.json()
        assert len(data["sources"]) <= 3


# ── Browse ──────────────────────────────────────────────────────────────────

class TestBrowse:
    def test_list_documents(self, test_library, uploaded_doc):
        lib_id = test_library["id"]
        r = client.get(f"/api/libraries/{lib_id}/documents")
        assert r.status_code == 200
        docs = r.json()
        assert len(docs) >= 1
        doc = docs[0]
        assert "id" in doc
        assert "title" in doc
        assert "word_count" in doc

    def test_get_document(self, test_library, uploaded_doc):
        lib_id = test_library["id"]
        # Get document list first
        docs = client.get(f"/api/libraries/{lib_id}/documents").json()
        if docs:
            doc_id = docs[0]["id"]
            r = client.get(f"/api/libraries/{lib_id}/documents/{doc_id}")
            assert r.status_code == 200
            doc = r.json()
            assert "title" in doc
            assert "full_text" in doc
            assert len(doc["full_text"]) > 0

    def test_list_topics(self, test_library, uploaded_doc):
        lib_id = test_library["id"]
        r = client.get(f"/api/libraries/{lib_id}/topics")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_library_info(self, test_library, uploaded_doc):
        lib_id = test_library["id"]
        r = client.get(f"/api/libraries/{lib_id}/info")
        assert r.status_code == 200
        info = r.json()
        assert "library" in info
        assert "corpus" in info
        assert info["library"]["name"] == "Test Library"
        assert info["corpus"]["document_count"] >= 1
        assert info["corpus"]["chunk_count"] >= 1


# ── Settings ────────────────────────────────────────────────────────────────

class TestSettings:
    def test_settings_get(self):
        r = client.get("/api/settings")
        assert r.status_code == 200
        body = r.json()
        assert "provider" in body


# ── User ────────────────────────────────────────────────────────────────────

class TestMultiLibrary:
    """Tests for cross-library search and chat."""

    @pytest.fixture(scope="class")
    def second_library(self):
        """Create a second test library with different content."""
        slug = f"test-lib2-{int(time.time())}"
        r = client.post("/api/libraries", json={
            "name": "Second Test Library",
            "slug": slug,
            "description": "Second library for multi-library tests",
            "visibility": "public",
        })
        assert r.status_code == 201, f"Failed to create second library: {r.text}"
        lib = r.json()

        # Upload different content
        content = """# Workplace Safety Guide

## OSHA Requirements
The Occupational Safety and Health Administration (OSHA) requires employers to provide
a safe and healthful workplace. Employers must comply with OSHA standards and regulations.

## Hazard Communication
Employers must inform workers about chemical hazards through labels, safety data sheets,
and training. The Hazard Communication Standard is one of OSHA's most cited standards.

## Personal Protective Equipment
Employers must provide personal protective equipment (PPE) to workers when engineering
controls are not sufficient to reduce hazards. PPE includes hard hats, gloves, and goggles.
"""
        files = {"file": ("test-safety.txt", content.encode(), "text/plain")}
        r = client.post(f"/api/libraries/{lib['id']}/upload", files=files)
        assert r.status_code == 200, f"Upload to second library failed: {r.text}"

        yield lib
        client.delete(f"/api/libraries/{lib['id']}")

    def test_multi_search(self, test_library, uploaded_doc, second_library):
        r = client.post("/api/search", json={
            "query": "workplace requirements",
            "library_ids": [test_library["id"], second_library["id"]],
        })
        assert r.status_code == 200
        data = r.json()
        assert len(data["results"]) > 0
        # Results should have library attribution
        for result in data["results"]:
            assert "library_id" in result
            assert "library_name" in result
            assert "library_slug" in result

    def test_multi_search_structure(self, test_library, uploaded_doc, second_library):
        r = client.post("/api/search", json={
            "query": "safety",
            "library_ids": [test_library["id"], second_library["id"]],
            "limit": 5,
        })
        data = r.json()
        assert "query" in data
        assert "results" in data
        assert "total" in data
        if data["results"]:
            result = data["results"][0]
            assert "chunk_id" in result
            assert "document_id" in result
            assert "document_title" in result
            assert "text" in result
            assert "similarity" in result
            assert 0 <= result["similarity"] <= 1
            assert "library_id" in result
            assert "library_name" in result
            assert "library_slug" in result

    def test_multi_search_empty_ids(self):
        r = client.post("/api/search", json={
            "query": "test", "library_ids": [],
        })
        assert r.status_code == 400

    def test_multi_search_nonexistent_library(self, test_library, uploaded_doc):
        r = client.post("/api/search", json={
            "query": "test", "library_ids": [test_library["id"], 99999],
        })
        assert r.status_code == 404

    def test_multi_chat(self, test_library, uploaded_doc, second_library):
        r = client.post("/api/chat", json={
            "message": "What are the workplace requirements?",
            "library_ids": [test_library["id"], second_library["id"]],
        })
        assert r.status_code == 200
        data = r.json()
        assert "answer" in data
        assert "sources" in data
        assert "suggestions" in data
        assert "conversation_id" in data
        assert len(data["answer"]) > 0
        assert len(data["sources"]) > 0

    def test_multi_chat_conversation_persistence(self, test_library, uploaded_doc, second_library):
        lib_ids = [test_library["id"], second_library["id"]]
        r1 = client.post("/api/chat", json={
            "message": "Tell me about safety",
            "library_ids": lib_ids,
        })
        data1 = r1.json()
        conv_id = data1["conversation_id"]
        assert conv_id

        r2 = client.post("/api/chat", json={
            "message": "What about PPE specifically?",
            "library_ids": lib_ids,
            "conversation_id": conv_id,
        })
        data2 = r2.json()
        assert data2["conversation_id"] == conv_id

        # Verify conversation is listed in multi-library conversations
        r3 = client.get("/api/conversations")
        assert r3.status_code == 200
        convs = r3.json()
        conv_ids = [c["id"] for c in convs]
        assert conv_id in conv_ids

        # Cleanup
        client.delete(f"/api/conversations/{conv_id}")

    def test_multi_chat_sources_have_library(self, test_library, uploaded_doc, second_library):
        r = client.post("/api/chat", json={
            "message": "Compare employment law with workplace safety",
            "library_ids": [test_library["id"], second_library["id"]],
        })
        data = r.json()
        for source in data["sources"]:
            assert "library_id" in source
            assert "library_name" in source
            assert "library_slug" in source

    def test_multi_chat_empty_ids(self):
        r = client.post("/api/chat", json={
            "message": "test", "library_ids": [],
        })
        assert r.status_code == 400


class TestUser:
    def test_me_authenticated(self):
        r = client.get("/api/me")
        assert r.status_code == 200
        body = r.json()
        assert body["authenticated"] is True
        assert body["username"] == "test-user"

    def test_me_anonymous(self):
        anon = httpx.Client(base_url=BASE, timeout=30.0)
        r = anon.get("/api/me")
        assert r.status_code == 200
        body = r.json()
        assert body["authenticated"] is False

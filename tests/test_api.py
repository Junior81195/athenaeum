"""API endpoint smoke tests.

Run:  pytest tests/test_api.py -v
Req:  docker compose up -d db api   (live DB required)
"""

import pytest
import httpx


BASE = "http://127.0.0.1:8140"


# ── Health ──────────────────────────────────────────────────────────────


def test_health():
    r = httpx.get(f"{BASE}/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "healthy"
    assert body["service"] == "athenaeum"


# ── Libraries ───────────────────────────────────────────────────────────


def test_list_libraries():
    r = httpx.get(f"{BASE}/api/libraries")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_create_and_delete_library():
    # Create
    r = httpx.post(f"{BASE}/api/libraries", json={
        "name": "Test Library",
        "slug": "test-lib",
        "description": "For testing",
    })
    assert r.status_code == 201
    lib = r.json()
    assert lib["slug"] == "test-lib"
    lib_id = lib["id"]

    # Get by slug
    r = httpx.get(f"{BASE}/api/libraries/by-slug/test-lib")
    assert r.status_code == 200
    assert r.json()["id"] == lib_id

    # Delete
    r = httpx.delete(f"{BASE}/api/libraries/{lib_id}")
    assert r.status_code == 204


def test_create_duplicate_slug():
    httpx.post(f"{BASE}/api/libraries", json={
        "name": "Dup Test", "slug": "dup-test",
    })
    r = httpx.post(f"{BASE}/api/libraries", json={
        "name": "Dup Test 2", "slug": "dup-test",
    })
    assert r.status_code == 409
    # cleanup
    libs = httpx.get(f"{BASE}/api/libraries").json()
    for lib in libs:
        if lib["slug"] == "dup-test":
            httpx.delete(f"{BASE}/api/libraries/{lib['id']}")


# ── Settings ────────────────────────────────────────────────────────────


def test_settings_get():
    r = httpx.get(f"{BASE}/api/settings")
    assert r.status_code == 200
    body = r.json()
    assert "provider" in body

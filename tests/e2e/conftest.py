"""E2E fixtures: API base URL, auth, and profile saved via PUT /profile (DB)."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import httpx
import pytest

_TESTDATA = Path(__file__).resolve().parent / "testdata"


@pytest.fixture(scope="session")
def api_url() -> str:
    return os.environ.get("E2E_API_URL", "http://localhost:8080").rstrip("/")


@pytest.fixture(scope="session")
def e2e_client(api_url: str) -> httpx.Client:
    return httpx.Client(base_url=api_url, timeout=120.0)


@pytest.fixture
def registered_user(e2e_client: httpx.Client) -> dict:
    email = f"e2e-{uuid.uuid4()}@example.com"
    password = "password123"
    r = e2e_client.post("/auth/register", json={"email": email, "password": password})
    r.raise_for_status()
    r2 = e2e_client.post("/auth/login", json={"email": email, "password": password})
    r2.raise_for_status()
    token = r2.json()["accessToken"]
    r3 = e2e_client.get("/me", headers={"Authorization": f"Bearer {token}"})
    r3.raise_for_status()
    user_id = r3.json()["userId"]
    return {
        "email": email,
        "password": password,
        "token": token,
        "user_id": user_id,
    }


@pytest.fixture
def saved_profile(e2e_client: httpx.Client, registered_user: dict) -> None:
    """Load audit/brand text from testdata and persist with PUT /profile."""
    audit_text = (_TESTDATA / "AUDIT.md").read_text(encoding="utf-8")
    brand_text = (_TESTDATA / "BRAND.md").read_text(encoding="utf-8")
    r = e2e_client.put(
        "/profile",
        json={"auditText": audit_text, "brandText": brand_text},
        headers={"Authorization": f"Bearer {registered_user['token']}"},
    )
    r.raise_for_status()


@pytest.fixture
def auth_headers(registered_user: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {registered_user['token']}"}


@pytest.fixture
def chat_id(
    e2e_client: httpx.Client,
    auth_headers: dict[str, str],
    saved_profile: None,
) -> str:
    r = e2e_client.post("/chats", json={"postType": "single"}, headers=auth_headers)
    r.raise_for_status()
    return r.json()["id"]

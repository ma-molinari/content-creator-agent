"""E2E fixtures: API base URL, auth, profile files on host for PROFILE_DATA_ROOT volume."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import httpx
import pytest

PROFILE_ROOT = Path(__file__).resolve().parent / "testdata" / "profile"


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
def profile_files(registered_user: dict) -> None:
    """Create AUDIT.md and BRAND.md under instagram-audits/<user_uuid>/ (host path = compose volume)."""
    uid = registered_user["user_id"]
    d = PROFILE_ROOT / "instagram-audits" / uid
    d.mkdir(parents=True, exist_ok=True)
    (d / "AUDIT.md").write_text(
        "# E2E audit\n\nMinimal voice and audience for smoke test.\n",
        encoding="utf-8",
    )
    (d / "BRAND.md").write_text(
        "# E2E brand\n\nMinimal palette and tone for smoke test.\n",
        encoding="utf-8",
    )


@pytest.fixture
def auth_headers(registered_user: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {registered_user['token']}"}


@pytest.fixture
def chat_id(
    e2e_client: httpx.Client,
    auth_headers: dict[str, str],
    profile_files: None,
) -> str:
    r = e2e_client.post("/chats", json={"postType": "single"}, headers=auth_headers)
    r.raise_for_status()
    return r.json()["id"]

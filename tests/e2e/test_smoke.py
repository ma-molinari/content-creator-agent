"""Smoke E2E: register, profile, post message, poll until done, assert assistant + image."""

from __future__ import annotations

import time

import httpx


def test_full_post_creation_flow(
    e2e_client: httpx.Client,
    registered_user: dict,
    auth_headers: dict[str, str],
    chat_id: str,
) -> None:
    r = e2e_client.post(
        f"/chats/{chat_id}/messages",
        json={"content": "Create a short Instagram-style single image post about automated testing."},
        headers=auth_headers,
    )
    assert r.status_code == 202, r.text
    job_id = r.json()["jobId"]

    deadline = time.monotonic() + 120.0
    status: str | None = None
    err: str | None = None
    while time.monotonic() < deadline:
        rs = e2e_client.get(
            f"/chats/{chat_id}/jobs/{job_id}/status",
            headers=auth_headers,
        )
        rs.raise_for_status()
        data = rs.json()
        status = data.get("status", "")
        if status in ("done", "failed"):
            err = data.get("error")
            break
        time.sleep(3.0)
    assert status == "done", f"expected done, got {status!r} error={err!r}"

    r2 = e2e_client.get(f"/chats/{chat_id}", headers=auth_headers)
    r2.raise_for_status()
    chat = r2.json()
    contents = chat.get("contents") or []
    assistant_msgs = [c for c in contents if c.get("role") == "assistant"]
    assert assistant_msgs, "expected at least one assistant message"
    last = assistant_msgs[-1]
    assert (last.get("content") or "").strip(), "assistant content should be non-empty"
    images = last.get("images") or []
    assert images, "expected at least one image artifact"
    assert any((img.get("s3Key") or "").strip() for img in images), "expected s3Key on image"

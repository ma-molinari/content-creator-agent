"""Opt-in smoke test for a dedicated non-production hybrid environment."""

import io
import os
import time
import zipfile

import httpx
import pytest


pytestmark = pytest.mark.skipif(os.getenv("E2E_HYBRID") != "1", reason="requires an isolated environment with hybrid generation enabled")


def wait_for_job(client: httpx.Client, headers: dict[str, str], chat_id: str, job_id: str) -> None:
    deadline = time.monotonic() + 600
    while time.monotonic() < deadline:
        response = client.get(f"/chats/{chat_id}/jobs/{job_id}/status", headers=headers)
        response.raise_for_status()
        job = response.json()
        if job["status"] == "done":
            return
        if job["status"] == "failed":
            pytest.fail(f"Job failed: code={job.get('errorCode')!r} message={job.get('error')!r}")
        time.sleep(5)
    pytest.fail("Timed out waiting for the job")


def test_hybrid_creation_and_edit(e2e_client: httpx.Client, auth_headers: dict[str, str], saved_profile: None) -> None:
    headers = {**auth_headers, "X-Post-Client-Version": "1"}
    created = e2e_client.post("/chats", json={"postType": "single"}, headers=headers)
    created.raise_for_status()
    chat = created.json()
    chat_id = chat["id"]
    try:
        assert chat["postFormat"] == "structured_v1", "Hybrid flag or worker capability is not enabled"
        for mode, text in (
            ("create", "Crie um post único sobre testes automatizados com título e texto curtos."),
            ("edit", "Altere somente o título para: Testes automatizados com confiança."),
        ):
            payload = {"content": text, "mode": mode}
            if mode == "edit":
                payload["baseVersionId"] = current_version
            response = e2e_client.post(f"/chats/{chat_id}/messages", json=payload, headers=headers)
            assert response.status_code == 202, response.text
            wait_for_job(e2e_client, headers, chat_id, response.json()["jobId"])
            response = e2e_client.get(f"/chats/{chat_id}", headers=headers)
            response.raise_for_status()
            chat = response.json()
            if mode == "edit":
                assert chat["currentVersionId"] != current_version
            current_version = chat["currentVersionId"]
            assert current_version
        versions = [item for item in chat["contents"] if item.get("role") == "assistant" and item.get("versionId")]
        assert len(versions) == 2
        assert len({item["versionId"] for item in versions}) == 2
        for item in versions:
            assert item.get("images")
            response = e2e_client.get(f"/chats/{chat_id}/contents/{item['id']}/download", headers=headers)
            response.raise_for_status()
            with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
                assert any(name.lower().endswith((".jpg", ".jpeg")) for name in archive.namelist())
    finally:
        response = e2e_client.delete(f"/chats/{chat_id}", headers=headers)
        response.raise_for_status()

"""Worker capability handshake and isolated endpoint tests."""

import asyncio
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import BackgroundTasks, HTTPException

from app.job_payload import DispatchPayload
from app.main import capabilities, post_jobs, post_structured_jobs, post_structured_jobs_v2, post_structured_jobs_v3


def test_capability_requires_key(monkeypatch):
    monkeypatch.setattr("app.config.get_settings", lambda: SimpleNamespace(worker_api_key="secret"))
    assert capabilities("secret") == {"structuredPost": {"contractVersion": 1, "readSchemas": [1, 2], "writeSchemas": [1, 2], "decorationOperations": True, "referencePolicyVersion": 1}}
    with pytest.raises(HTTPException) as exc:
        capabilities("wrong")
    assert exc.value.status_code == 401


def test_structured_job_is_only_accepted_by_dedicated_endpoint(monkeypatch):
    monkeypatch.setattr("app.config.get_settings", lambda: SimpleNamespace(worker_api_key="secret"))
    payload = DispatchPayload(job_id=uuid4(), user_id=uuid4(), chat_id=uuid4(), post_format="structured_v1", generation_mode="create")
    tasks = BackgroundTasks()
    with pytest.raises(HTTPException) as exc:
        asyncio.run(post_jobs(payload, tasks, "secret"))
    assert exc.value.status_code == 400
    assert not tasks.tasks
    result = asyncio.run(post_structured_jobs(payload, tasks, "secret"))
    assert result["accepted"] is True
    assert len(tasks.tasks) == 1


def test_v3_requires_dedicated_endpoint(monkeypatch):
    monkeypatch.setattr("app.config.get_settings", lambda: SimpleNamespace(worker_api_key="secret"))
    payload = DispatchPayload(job_id=uuid4(), user_id=uuid4(), chat_id=uuid4(), post_format="structured_v1", generation_mode="create", target_schema_version=3)
    tasks = BackgroundTasks()
    with pytest.raises(HTTPException):
        asyncio.run(post_structured_jobs_v2(payload, tasks, "secret"))
    assert asyncio.run(post_structured_jobs_v3(payload, tasks, "secret"))["accepted"] is True

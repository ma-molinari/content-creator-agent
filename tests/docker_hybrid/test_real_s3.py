"""Safety checks for the real S3 rehearsal's delayed verification."""
from datetime import datetime, timedelta, timezone
import json
import uuid
from unittest.mock import MagicMock

import pytest

import real_s3


def test_verify_rejects_recent_marker_without_deleting(monkeypatch):
    client = MagicMock()
    client.head_object.return_value = {"LastModified": datetime.now(timezone.utc) - timedelta(hours=23)}
    job_id, chat_id = str(uuid.uuid4()), str(uuid.uuid4())
    row = json.dumps({"job_id": job_id, "chat_id": chat_id, "bucket": "test-bucket", "region": "us-east-2"})
    commands = MagicMock(return_value="")
    monkeypatch.setattr(real_s3, "volume_exists", lambda: True)
    monkeypatch.setattr(real_s3, "storage", lambda: (client, "test-bucket", "us-east-2"))
    monkeypatch.setattr(real_s3, "compose", commands)
    monkeypatch.setattr(real_s3, "sql", lambda *args, **kwargs: row)

    with pytest.raises(RuntimeError, match="24 horas"):
        real_s3.verify()

    client.put_object.assert_not_called()
    client.delete_object.assert_not_called()
    commands.assert_any_call("stop")
    assert not any(call.kwargs.get("reconcile") for call in commands.call_args_list)


def test_verify_rejects_changed_bucket_before_enabling_reconciliation(monkeypatch):
    client = MagicMock()
    row = json.dumps({"job_id": str(uuid.uuid4()), "chat_id": str(uuid.uuid4()),
                      "bucket": "original", "region": "us-east-2"})
    commands = MagicMock(return_value="")
    monkeypatch.setattr(real_s3, "volume_exists", lambda: True)
    monkeypatch.setattr(real_s3, "storage", lambda: (client, "different", "us-east-2"))
    monkeypatch.setattr(real_s3, "compose", commands)
    monkeypatch.setattr(real_s3, "sql", lambda *args, **kwargs: row)

    with pytest.raises(RuntimeError, match="bucket ou a região"):
        real_s3.verify()

    client.put_object.assert_not_called()
    client.delete_object.assert_not_called()
    assert not any(call.kwargs.get("reconcile") for call in commands.call_args_list)


def test_verify_checks_old_deletion_and_preserves_recent(monkeypatch):
    client = MagicMock()
    client.head_object.return_value = {"LastModified": datetime.now(timezone.utc) - timedelta(hours=25)}
    job_id, chat_id = str(uuid.uuid4()), str(uuid.uuid4())
    row = json.dumps({"job_id": job_id, "chat_id": chat_id, "bucket": "test-bucket", "region": "us-east-2"})
    commands = MagicMock(return_value="event=artifact_reconcile outcome=done")
    monkeypatch.setattr(real_s3, "volume_exists", lambda: True)
    monkeypatch.setattr(real_s3, "storage", lambda: (client, "test-bucket", "us-east-2"))
    monkeypatch.setattr(real_s3, "compose", commands)
    monkeypatch.setattr(real_s3, "sql", lambda query, **kwargs: row if "row_to_json" in query else "1")
    monkeypatch.setattr(real_s3, "missing", lambda *args: True)
    monkeypatch.setattr(real_s3, "gate_request", lambda *args: '{"connections": 1}')
    kill = MagicMock()
    monkeypatch.setattr(real_s3, "run", kill)

    real_s3.verify()

    recent, protected = (call.kwargs["Key"] for call in client.put_object.call_args_list)
    assert recent.startswith(f"slides/{job_id}/t18-recent-probe-")
    assert protected.startswith(f"slides/{job_id}/t18-referenced-probe-")
    client.head_object.assert_any_call(Bucket="test-bucket", Key=recent)
    client.head_object.assert_any_call(Bucket="test-bucket", Key=protected)
    client.delete_object.assert_any_call(Bucket="test-bucket", Key=recent)
    client.delete_object.assert_any_call(Bucket="test-bucket", Key=protected)
    assert client.delete_object.call_count == 2
    kill.assert_called_once_with("docker", "kill", real_s3.PROJECT + "-api-1")
    assert any(call.kwargs.get("reconcile") is True for call in commands.call_args_list)
    commands.assert_any_call("stop")

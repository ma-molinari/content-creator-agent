"""Exercise the opt-in E2E harness without external services."""

import io
import zipfile

import httpx

from test_hybrid import test_hybrid_creation_and_edit as _run_hybrid_e2e


def test_hybrid_harness_uses_versions_and_cleans_up():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("slide_01.jpeg", b"image")
    calls = []

    def handle(request):
        calls.append((request.method, request.url.path))
        assert request.headers["x-post-client-version"] == "1"
        path = request.url.path
        if path == "/chats" and request.method == "POST":
            return httpx.Response(201, json={"id": "chat", "postFormat": "structured_v1"})
        if path == "/chats/chat/messages":
            import json
            payload = json.loads(request.content)
            if payload["mode"] == "edit":
                assert payload["baseVersionId"] == "version1"
            return httpx.Response(202, json={"jobId": "job1" if payload["mode"] == "create" else "job2"})
        if "/status" in path:
            return httpx.Response(200, json={"status": "done"})
        if path == "/chats/chat" and request.method == "GET":
            is_edit = calls.count(("POST", "/chats/chat/messages")) == 2
            contents = [{"id": "content1", "role": "assistant", "versionId": "version1", "images": [{}]}]
            if is_edit:
                contents.append({"id": "content2", "role": "assistant", "versionId": "version2", "images": [{}]})
            return httpx.Response(200, json={"currentVersionId": "version2" if is_edit else "version1", "contents": contents})
        if path.endswith("/download"):
            return httpx.Response(200, content=buffer.getvalue())
        if path == "/chats/chat" and request.method == "DELETE":
            return httpx.Response(204)
        return httpx.Response(404)

    with httpx.Client(base_url="http://example.test", transport=httpx.MockTransport(handle)) as client:
        _run_hybrid_e2e(client, {"Authorization": "Bearer test"}, None)
    assert calls[-1] == ("DELETE", "/chats/chat")

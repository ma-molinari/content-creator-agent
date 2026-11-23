"""Run a disposable hybrid rehearsal using Docker, a fake S3, and a fake LLM."""
import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import uuid
import zipfile
import io

import httpx

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "docker_hybrid"
API_IMAGE = os.getenv("HYBRID_DOCKER_API_IMAGE", "content-creator-agent-api:latest")
WORKER_IMAGE = os.getenv("HYBRID_DOCKER_WORKER_IMAGE", "content-creator-agent-worker:latest")
PG_IMAGE = os.getenv("HYBRID_DOCKER_POSTGRES_IMAGE", "postgres:16-alpine")
S3_MODE = os.getenv("HYBRID_DOCKER_S3", "stub")
LOCALSTACK_IMAGE = os.getenv("HYBRID_DOCKER_LOCALSTACK_IMAGE", "localstack/localstack:3.8.1")
KEY = "local-rehearsal-key"
ACCESS_SECRET = "local-rehearsal-access-secret-32-characters"
REFRESH_SECRET = "local-rehearsal-refresh-secret-32-characters"


def docker(*args, check=True):
    return subprocess.run(["docker", *map(str, args)], check=check, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.strip()


def sql(container, query, **params):
    command = ["docker", "exec", "-i", container, "psql", "-U", "rehearsal", "-d", "rehearsal", "-tA", "-v", "ON_ERROR_STOP=1"]
    for key, value in params.items():
        command.extend(["-v", f"{key}={value}"])
    return subprocess.run(command, input=query, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.strip()


def wait_until(check, message, timeout=40):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if check():
                return
        except (httpx.HTTPError, subprocess.CalledProcessError):
            pass
        time.sleep(1)
    raise RuntimeError(message)


def main():
    if S3_MODE not in ("stub", "localstack"):
        raise ValueError("HYBRID_DOCKER_S3 must be stub or localstack")
    suffix = uuid.uuid4().hex[:10]
    network = "postmind-rehearsal-" + suffix
    names = {part: "postmind-" + part + "-" + suffix for part in ("postgres", "s3", "s3proxy", "api", "proxy", "worker")}
    arch = docker("image", "inspect", "--format", "{{.Architecture}}", API_IMAGE)
    if arch not in ("arm64", "amd64"):
        raise RuntimeError("Unsupported API image architecture: " + arch)
    temp_root = "/tmp" if sys.platform == "darwin" else None
    with tempfile.TemporaryDirectory(prefix="postmind-hybrid-", dir=temp_root) as directory:
        binary = Path(directory) / "api"
        env = {**os.environ, "GOOS": "linux", "GOARCH": arch, "CGO_ENABLED": "0"}
        subprocess.run(["go", "build", "-o", str(binary), "./cmd/server"], cwd=ROOT / "apps" / "api", env=env, check=True)
        try:
            docker("network", "create", network)
            docker("run", "-d", "--rm", "--name", names["postgres"], "--network", network, "--network-alias", "postgres", "-e", "POSTGRES_USER=rehearsal", "-e", "POSTGRES_PASSWORD=rehearsal", "-e", "POSTGRES_DB=rehearsal", PG_IMAGE)
            wait_until(lambda: subprocess.run(["docker", "exec", names["postgres"], "pg_isready", "-U", "rehearsal", "-d", "rehearsal"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0, "PostgreSQL did not become ready")
            if S3_MODE == "localstack":
                docker("run", "-d", "--rm", "--name", names["s3"], "--network", network, "--network-alias", "s3", "-e", "SERVICES=s3", "-e", "AWS_DEFAULT_REGION=us-east-1", LOCALSTACK_IMAGE)
                wait_until(lambda: subprocess.run(["docker", "exec", names["s3"], "awslocal", "s3api", "list-buckets"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0, "LocalStack did not become ready", timeout=90)
                docker("exec", names["s3"], "awslocal", "s3api", "create-bucket", "--bucket", "rehearsal")
                docker("run", "-d", "--rm", "--name", names["s3proxy"], "--network", network, "-v", f"{FIXTURES / 'localstack_time_proxy.py'}:/s3_proxy.py:ro", "--entrypoint", "python", WORKER_IMAGE, "/s3_proxy.py")
                wait_until(lambda: subprocess.run(["docker", "exec", names["s3proxy"], "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9000/__rehearsal/stats')"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0, "S3 proxy did not become ready")
                s3_port = 9000
            else:
                docker("run", "-d", "--rm", "--name", names["s3"], "--network", network, "-e", "REHEARSAL_AGE_SECONDS=172800", "-v", f"{FIXTURES / 's3_stub.py'}:/mock_s3.py:ro", "--entrypoint", "python", WORKER_IMAGE, "/mock_s3.py")
                s3_port = 9000
            endpoint_name = names["s3proxy"] if S3_MODE == "localstack" else names["s3"]
            inspect = json.loads(docker("inspect", endpoint_name))
            s3_ip = inspect[0]["NetworkSettings"]["Networks"][network]["IPAddress"]
            common_aws = ["-e", "AWS_REGION=us-east-1", "-e", "AWS_ACCESS_KEY_ID=localtest", "-e", "AWS_SECRET_ACCESS_KEY=localtest", "-e", "AWS_S3_BUCKET=rehearsal", "-e", "AWS_ENDPOINT_URL=http://" + s3_ip + ":" + str(s3_port)]

            def start_api(enabled, reconcile=False, visual_v2=False):
                docker("run", "-d", "--rm", "--name", names["api"], "--network", network, "--network-alias", "api", "-p", "127.0.0.1::8080", "-v", f"{binary}:/app/server:ro", "-e", "PORT=8080", "-e", "DATABASE_URL=postgres://rehearsal:rehearsal@postgres:5432/rehearsal?sslmode=disable", "-e", "JWT_SECRET=" + ACCESS_SECRET, "-e", "JWT_REFRESH_SECRET=" + REFRESH_SECRET, "-e", "COOKIE_SECURE=false", "-e", "WORKER_API_KEY=" + KEY, "-e", "WORKER_URL=http://worker:8000", "-e", "STRUCTURED_POSTS_ENABLED=" + str(enabled).lower(), "-e", "STRUCTURED_VISUAL_V2_ENABLED=" + str(visual_v2).lower(), "-e", "STRUCTURED_WORKER_URLS=http://worker:8000", "-e", "ARTIFACT_RECONCILE_ENABLED=" + str(reconcile).lower(), "-e", "ARTIFACT_RECONCILE_CRON=@every 1s", *common_aws, API_IMAGE)
                address = docker("port", names["api"], "8080/tcp").splitlines()[0]
                url = "http://" + address
                wait_until(lambda: httpx.get(url + "/health", timeout=2).status_code == 200, "API did not become ready")
                return url

            def stop_api(force=False):
                docker("kill" if force else "stop", names["api"])
                wait_until(lambda: subprocess.run(["docker", "inspect", names["api"]], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0,
                           "API container was not removed")

            api_url = start_api(True)
            docker("run", "-d", "--rm", "--name", names["proxy"], "--network", network, "--network-alias", "callback", "-v", f"{FIXTURES / 'callback_proxy.py'}:/callback_proxy.py:ro", "--entrypoint", "python", WORKER_IMAGE, "/callback_proxy.py")
            wait_until(lambda: subprocess.run(["docker", "exec", names["proxy"], "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8081/__rehearsal/stats')"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0, "Callback proxy did not become ready")
            docker("run", "-d", "--rm", "--name", names["worker"], "--network", network, "--network-alias", "worker", "-v", f"{ROOT / 'apps' / 'worker' / 'app'}:/app/app:ro", "-v", f"{FIXTURES / 'worker_stub.py'}:/mock_worker.py:ro", "-e", "OPENAI_API_KEY=local-mock", "-e", "GO_API_URL=http://callback:8081", "-e", "WORKER_API_KEY=" + KEY, *common_aws, "--entrypoint", "python", WORKER_IMAGE, "/mock_worker.py")
            wait_until(lambda: subprocess.run(["docker", "exec", names["worker"], "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0, "Worker did not become ready")

            with httpx.Client(base_url=api_url, timeout=30) as client:
                credentials = {"email": "rehearsal-" + uuid.uuid4().hex + "@example.com", "password": "password123"}
                def call(method, path, **kwargs):
                    for attempt in range(7):
                        response = client.request(method, path, **kwargs)
                        if response.status_code != 429 or attempt == 6:
                            response.raise_for_status()
                            return response
                        time.sleep(10)
                    raise RuntimeError("Limite de requisições persistiu")
                def wait_job(chat_id, job_id, headers, allow_conflict=False, allow_failure=False):
                    result = {}
                    def terminal():
                        result.update(call("GET", f"/chats/{chat_id}/jobs/{job_id}/status", headers=headers).json())
                        if result["status"] == "failed" and not allow_failure and not (allow_conflict and result.get("errorCode") == "VERSION_CONFLICT"):
                            raise RuntimeError("Job failed: " + str(result.get("errorCode")))
                        return result["status"] in ("done", "failed")
                    wait_until(terminal, "Job did not finish", timeout=120)
                    return result
                call("POST", "/auth/register", json=credentials)
                token = call("POST", "/auth/login", json=credentials).json()["accessToken"]
                headers = {"Authorization": "Bearer " + token, "X-Post-Client-Version": "1"}
                data = ROOT / "tests" / "e2e" / "testdata"
                call("PUT", "/profile", headers=headers, json={"auditText": (data / "AUDIT.md").read_text(), "brandText": (data / "BRAND.md").read_text()})
                chat = call("POST", "/chats", headers=headers, json={"postType": "single"}).json()
                assert chat["postFormat"] == "structured_v1"
                chat_id = chat["id"]
                png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/aXcAAAAASUVORK5CYII=")
                job = call("POST", f"/chats/{chat_id}/messages", headers=headers, data={"content": "Crie um post curto.", "mode": "create"}, files={"attachments": ("test.png", png, "image/png")}).json()
                wait_job(chat_id, job["jobId"], headers)
                initial = call("GET", f"/chats/{chat_id}", headers=headers).json()["currentVersionId"]
                assert initial
                old_client = client.get(f"/chats/{chat_id}", headers={"Authorization": "Bearer " + token})
                assert old_client.status_code == 426
                other = {"email": "other-" + uuid.uuid4().hex + "@example.com", "password": "password123"}
                call("POST", "/auth/register", json=other)
                other_token = call("POST", "/auth/login", json=other).json()["accessToken"]
                other_headers = {"Authorization": "Bearer " + other_token, "X-Post-Client-Version": "1"}
                forbidden = client.post(f"/chats/{chat_id}/messages", headers=other_headers, json={"content": "edite", "mode": "edit", "baseVersionId": initial})
                assert forbidden.status_code == 403
                assert call("GET", f"/chats/{chat_id}", headers=headers).json()["currentVersionId"] == initial
                if S3_MODE == "localstack":
                    objects = json.loads(docker("exec", names["s3"], "awslocal", "s3api", "list-objects-v2", "--bucket", "rehearsal"))
                    attachments = [item["Key"] for item in objects.get("Contents", []) if "/chat-attachments/" in item["Key"]]
                    assert len(attachments) == 1
                    docker("exec", names["s3"], "awslocal", "s3api", "delete-object", "--bucket", "rehearsal", "--key", attachments[0])
                else:
                    removed = docker("exec", names["s3"], "python", "-c", "import urllib.request; print(urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:9000/__rehearsal/remove-attachments', data=b'', method='POST')).read().decode())")
                    assert json.loads(removed)["removed"] == 1
                job = call("POST", f"/chats/{chat_id}/messages", headers=headers, json={"content": "Altere o título.", "mode": "edit", "baseVersionId": initial}).json()
                wait_job(chat_id, job["jobId"], headers)
                edited = call("GET", f"/chats/{chat_id}", headers=headers).json()
                assert edited["currentVersionId"] != initial
                base = edited["currentVersionId"]
                competing = []
                for number in (1, 2):
                    job = call("POST", f"/chats/{chat_id}/messages", headers=headers, json={"content": f"concorrente {number}", "mode": "edit", "baseVersionId": base}).json()
                    competing.append(job["jobId"])
                outcomes = [wait_job(chat_id, job_id, headers, allow_conflict=True) for job_id in competing]
                assert sorted(item["status"] for item in outcomes) == ["done", "failed"]
                assert next(item for item in outcomes if item["status"] == "failed")["errorCode"] == "VERSION_CONFLICT"
                edited = call("GET", f"/chats/{chat_id}", headers=headers).json()
                assert edited["currentVersionId"] != base
                responses = [item for item in edited["contents"] if item.get("versionId")]
                assert len(responses) == 3
                for item in responses:
                    blob = call("GET", f"/chats/{chat_id}/contents/{item['id']}/download", headers=headers).content
                    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
                        assert any(name.endswith(".jpg") for name in archive.namelist())
                # Promote the current V1 snapshot and then edit V2 through the actual API and worker.
                stop_api()
                client.base_url = httpx.URL(start_api(True, visual_v2=True))
                job = call("POST", f"/chats/{chat_id}/messages", headers=headers, json={"content": "Altere o título.", "mode": "edit", "baseVersionId": edited["currentVersionId"]}).json()
                wait_job(chat_id, job["jobId"], headers)
                promoted = call("GET", f"/chats/{chat_id}", headers=headers).json()["currentVersionId"]
                assert promoted != edited["currentVersionId"]
                job = call("POST", f"/chats/{chat_id}/messages", headers=headers, json={"content": "Altere o título novamente.", "mode": "edit", "baseVersionId": promoted}).json()
                wait_job(chat_id, job["jobId"], headers)
                v2_current = call("GET", f"/chats/{chat_id}", headers=headers).json()["currentVersionId"]
                assert v2_current != promoted
                reference = call("POST", "/profile/references", headers=headers, files={"file": ("reference.png", png, "image/png")}).json()["references"][0]
                reference_key = sql(names["postgres"], "SELECT s3_key FROM user_profile_references WHERE id = :'ref_id'::uuid", ref_id=reference["id"])
                docker("exec", names["worker"], "python", "-c", "import boto3,os,sys; boto3.client('s3').delete_object(Bucket=os.environ['AWS_S3_BUCKET'], Key=sys.argv[1])", reference_key)
                job = call("POST", f"/chats/{chat_id}/messages", headers=headers, json={"content": "Edite sem reaplicar o perfil.", "mode": "edit", "baseVersionId": v2_current}).json()
                wait_job(chat_id, job["jobId"], headers)
                v2_current = call("GET", f"/chats/{chat_id}", headers=headers).json()["currentVersionId"]
                job = call("POST", f"/chats/{chat_id}/messages", headers=headers, json={"content": "Aplicar referências visuais.", "mode": "edit", "baseVersionId": v2_current}).json()
                failed = wait_job(chat_id, job["jobId"], headers, allow_failure=True)
                assert failed["status"] == "failed" and failed.get("errorCode") == "VISUAL_REFERENCE_ERROR"
                assert call("GET", f"/chats/{chat_id}", headers=headers).json()["currentVersionId"] == v2_current
                call("DELETE", f"/profile/references/{reference['id']}", headers=headers)
                concurrent = []
                for number in (1, 2):
                    job = call("POST", f"/chats/{chat_id}/messages", headers=headers, json={"content": f"concorrente V2 {number}", "mode": "edit", "baseVersionId": v2_current}).json()
                    concurrent.append(job["jobId"])
                outcomes = [wait_job(chat_id, job_id, headers, allow_conflict=True) for job_id in concurrent]
                assert sorted(item["status"] for item in outcomes) == ["done", "failed"]
                assert next(item for item in outcomes if item["status"] == "failed")["errorCode"] == "VERSION_CONFLICT"
                v2_current = call("GET", f"/chats/{chat_id}", headers=headers).json()["currentVersionId"]
                job = call("POST", f"/chats/{chat_id}/messages", headers=headers, json={"content": "Crie um novo post.", "mode": "create"}).json()
                wait_job(chat_id, job["jobId"], headers)
                v2_root = call("GET", f"/chats/{chat_id}", headers=headers).json()["currentVersionId"]
                assert v2_root != v2_current
                versions = sql(names["postgres"], "SELECT string_agg(schema_version::text, ',' ORDER BY created_at) FROM post_versions WHERE chat_id = :'chat_id'::uuid", chat_id=chat_id)
                assert versions == "1,1,1,2,2,2,2,2", versions
                stop_api()
                client.base_url = httpx.URL(start_api(True))
                job = call("POST", f"/chats/{chat_id}/messages", headers=headers, json={"content": "Edite após rollback.", "mode": "edit", "baseVersionId": v2_root}).json()
                wait_job(chat_id, job["jobId"], headers)
                rolled_back_edit = call("GET", f"/chats/{chat_id}", headers=headers).json()["currentVersionId"]
                schema = sql(names["postgres"], "SELECT schema_version FROM post_versions WHERE id = :'version_id'::uuid", version_id=rolled_back_edit)
                assert schema == "2"
                docker("exec", names["worker"], "touch", "/tmp/visual-v2-incompatible")
                unavailable = client.post(f"/chats/{chat_id}/messages", headers=headers, json={"content": "Edite sem capacidade.", "mode": "edit", "baseVersionId": rolled_back_edit})
                assert unavailable.status_code == 503
                assert call("GET", f"/chats/{chat_id}", headers=headers).json()["currentVersionId"] == rolled_back_edit
                docker("exec", names["worker"], "rm", "/tmp/visual-v2-incompatible")
                job = call("POST", f"/chats/{chat_id}/messages", headers=headers, json={"content": "Nova raiz V1.", "mode": "create"}).json()
                wait_job(chat_id, job["jobId"], headers)
                new_root = call("GET", f"/chats/{chat_id}", headers=headers).json()["currentVersionId"]
                root_data = sql(names["postgres"], "SELECT schema_version, parent_version_id IS NULL FROM post_versions WHERE id = :'version_id'::uuid", version_id=new_root)
                assert root_data == "1|t"
                for item in call("GET", f"/chats/{chat_id}", headers=headers).json()["contents"]:
                    if item.get("versionId"):
                        blob = call("GET", f"/chats/{chat_id}/contents/{item['id']}/download", headers=headers).content
                        with zipfile.ZipFile(io.BytesIO(blob)) as archive:
                            assert any(name.endswith(".jpg") for name in archive.namelist())
                edited = call("GET", f"/chats/{chat_id}", headers=headers).json()
                stop_api()
                api_url = start_api(False)
                client.base_url = httpx.URL(api_url)
                current = call("GET", f"/chats/{chat_id}", headers=headers).json()["currentVersionId"]
                assert current == edited["currentVersionId"]
                legacy = call("POST", "/chats", headers=headers, json={"postType": "single"}).json()
                assert legacy["postFormat"] == "legacy_html"
                legacy_headers = {"Authorization": "Bearer " + token}
                legacy_job = call("POST", f"/chats/{legacy['id']}/messages", headers=legacy_headers, json={"content": "Crie um post legado."}).json()
                wait_job(legacy["id"], legacy_job["jobId"], legacy_headers)
                legacy_chat = call("GET", f"/chats/{legacy['id']}", headers=legacy_headers).json()
                legacy_reply = next(item for item in legacy_chat["contents"] if item.get("role") == "assistant")
                with zipfile.ZipFile(io.BytesIO(call("GET", f"/chats/{legacy['id']}/contents/{legacy_reply['id']}/download", headers=legacy_headers).content)) as archive:
                    assert any(name.endswith(".jpg") for name in archive.namelist())
                job = call("POST", f"/chats/{chat_id}/messages", headers=headers, json={"content": "Altere o título.", "mode": "edit", "baseVersionId": current}).json()
                wait_job(chat_id, job["jobId"], headers)
                assert call("GET", f"/chats/{chat_id}", headers=headers).json()["currentVersionId"] != current
                call("DELETE", f"/chats/{chat_id}", headers=headers)
                call("DELETE", f"/chats/{legacy['id']}", headers=headers)
            sys.path.insert(0, str(ROOT / "tools"))
            from summarize_job_metrics import summarize
            def api_logs():
                result = subprocess.run(["docker", "logs", names["api"]], check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                return (result.stdout + result.stderr).splitlines()
            assert summarize(api_logs())["jobs"]["structured_v1"]["done"] >= 1
            worker_output = subprocess.run(["docker", "logs", names["worker"]], check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            visual_metrics = summarize((worker_output.stdout + worker_output.stderr).splitlines())["visual_v2"]
            assert visual_metrics["structured_validation"]["outcomes"]["success"] >= 1
            assert visual_metrics["structured_render"]["outcomes"]["success"] >= 1
            assert visual_metrics["structured_publication"]["outcomes"]["success"] >= 1
            assert visual_metrics["visual_direction"]["reasons"]["fetch"] >= 1
            def callback_stats():
                output = docker("exec", names["proxy"], "python", "-c", "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8081/__rehearsal/stats').read().decode())")
                return json.loads(output)
            wait_until(lambda: callback_stats()["completion_attempts"] >= 6, "Callback retry not observed", timeout=15)
            assert callback_stats()["responses_dropped"] == 1

            def object_count():
                if S3_MODE == "localstack":
                    objects = json.loads(docker("exec", names["s3"], "awslocal", "s3api", "list-objects-v2", "--bucket", "rehearsal"))
                    return len(objects.get("Contents", []))
                output = docker("exec", names["s3"], "python", "-c", "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:9000/__rehearsal/count').read().decode())")
                return json.loads(output)["count"]
            assert object_count() > 0
            docker("exec", names["postgres"], "psql", "-U", "rehearsal", "-d", "rehearsal", "-c", "UPDATE chat_cleanup_tasks SET created_at = NOW() - INTERVAL '48 hours'")
            def s3_proxy_stats():
                data = docker("exec", names["s3proxy"], "python", "-c", "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:9000/__rehearsal/stats').read().decode())")
                return json.loads(data)
            stop_api()
            before_pause = s3_proxy_stats()["forwarded_requests"] if S3_MODE == "localstack" else 0
            docker("pause", names["s3"])
            try:
                start_api(False, reconcile=True)
                if S3_MODE == "localstack":
                    wait_until(lambda: s3_proxy_stats()["forwarded_requests"] > before_pause, "Reconciliation did not reach the paused S3", timeout=15)
                else:
                    time.sleep(3)
                stop_api(force=True)
            finally:
                docker("unpause", names["s3"], check=False)
            start_api(False, reconcile=True)
            wait_until(lambda: object_count() == 0, "Reconciliation did not remove simulated objects", timeout=40)
            wait_until(lambda: summarize(api_logs())["reconcile"]["done_runs"] >= 1, "Reconciliation metric not found", timeout=10)
            count = docker("exec", names["postgres"], "psql", "-U", "rehearsal", "-d", "rehearsal", "-tAc", "SELECT count(*) FROM chat_cleanup_tasks")
            assert int(count) >= 1
            if S3_MODE == "localstack":
                assert s3_proxy_stats()["aged_timestamps"] > 0
            print("Ensaio Docker concluído: segurança, assets, concorrência, callback, rollback e reconciliação (S3=" + S3_MODE + ").")
        except Exception:
            for part in ("api", "worker"):
                result = subprocess.run(["docker", "logs", names[part]], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                print(f"Logs do serviço descartável {part}:\n" + "\n".join((result.stdout + result.stderr).splitlines()[-30:]), file=sys.stderr)
            raise
        finally:
            for name in reversed(list(names.values())):
                docker("rm", "-f", name, check=False)
            docker("network", "rm", network, check=False)


if __name__ == "__main__":
    main()

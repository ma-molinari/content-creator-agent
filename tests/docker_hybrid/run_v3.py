"""Exercita API, worker, PostgreSQL, LocalStack e Openverse/LLM simulados."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import uuid

import httpx

from run import API_IMAGE, KEY, LOCALSTACK_IMAGE, PG_IMAGE, ROOT, WORKER_IMAGE, docker, wait_until


def main():
    suffix = uuid.uuid4().hex[:10]
    network = "postmind-v3-" + suffix
    names = {part: "postmind-v3-" + part + "-" + suffix for part in ("pg", "s3", "worker", "api")}
    arch = docker("image", "inspect", "--format", "{{.Architecture}}", API_IMAGE)
    with tempfile.TemporaryDirectory(prefix="postmind-v3-", dir="/tmp" if sys.platform == "darwin" else None) as directory:
        binary = Path(directory) / "api"
        subprocess.run(["go", "build", "-o", str(binary), "./cmd/server"], cwd=ROOT / "apps" / "api", check=True,
                       env={**os.environ, "GOOS": "linux", "GOARCH": arch, "CGO_ENABLED": "0"})
        try:
            docker("network", "create", network)
            docker("run", "-d", "--rm", "--name", names["pg"], "--network", network, "--network-alias", "postgres",
                   "-e", "POSTGRES_USER=rehearsal", "-e", "POSTGRES_PASSWORD=rehearsal", "-e", "POSTGRES_DB=rehearsal", PG_IMAGE)
            wait_until(lambda: subprocess.run(["docker", "exec", names["pg"], "pg_isready", "-U", "rehearsal"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0, "Postgres indisponível")
            docker("run", "-d", "--rm", "--name", names["s3"], "--network", network, "--network-alias", "localstack", "-e", "SERVICES=s3", LOCALSTACK_IMAGE)
            wait_until(lambda: subprocess.run(["docker", "exec", names["s3"], "awslocal", "s3api", "list-buckets"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0, "LocalStack indisponível", timeout=90)
            docker("exec", names["s3"], "awslocal", "s3api", "create-bucket", "--bucket", "rehearsal")
            aws = ["-e", "AWS_REGION=us-east-1", "-e", "AWS_ACCESS_KEY_ID=localtest", "-e", "AWS_SECRET_ACCESS_KEY=localtest",
                   "-e", "AWS_S3_BUCKET=rehearsal", "-e", "AWS_ENDPOINT_URL=http://localstack:4566", "-e", "AWS_S3_FORCE_PATH_STYLE=true"]
            docker("run", "-d", "--rm", "--name", names["worker"], "--network", network, "--network-alias", "worker",
                   "-v", f"{ROOT / 'apps/worker/app'}:/app/app:ro", "-v", f"{ROOT / 'tests/docker_hybrid/worker_v3_stub.py'}:/stub.py:ro",
                   "-e", "OPENAI_API_KEY=local-mock", "-e", "GO_API_URL=http://api:8081", "-e", "WORKER_API_KEY=" + KEY,
                   *aws, "--entrypoint", "python", WORKER_IMAGE, "/stub.py")
            wait_until(lambda: subprocess.run(["docker", "exec", names["worker"], "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0, "Worker indisponível")
            docker("run", "-d", "--rm", "--name", names["api"], "--network", network, "--network-alias", "api", "-p", "127.0.0.1::8080",
                   "-v", f"{binary}:/app/server:ro", "-e", "PORT=8080", "-e", "DATABASE_URL=postgres://rehearsal:rehearsal@postgres:5432/rehearsal?sslmode=disable",
                   "-e", "JWT_SECRET=local-rehearsal-access-secret-32-characters", "-e", "JWT_REFRESH_SECRET=local-rehearsal-refresh-secret-32-characters",
                   "-e", "COOKIE_SECURE=false", "-e", "WORKER_API_KEY=" + KEY, "-e", "WORKER_URL=http://worker:8000",
                   "-e", "STRUCTURED_POSTS_ENABLED=true", "-e", "STRUCTURED_STOCK_IMAGES_ENABLED=true", "-e", "STRUCTURED_WORKER_URLS=http://worker:8000", *aws, API_IMAGE)
            address = docker("port", names["api"], "8080/tcp").splitlines()[0]
            api = "http://" + address
            wait_until(lambda: httpx.get(api + "/health", timeout=2).status_code == 200, "API indisponível")
            with httpx.Client(base_url=api, timeout=30) as client:
                def call(method, path, **kwargs):
                    for _ in range(8):
                        result = client.request(method, path, **kwargs)
                        if result.status_code != 429:
                            result.raise_for_status()
                            return result
                        time.sleep(10)
                    raise RuntimeError("Limite de requisições persistiu")

                credentials = {"email": uuid.uuid4().hex + "@test.invalid", "password": "password123"}
                call("POST", "/auth/register", json=credentials)
                token = call("POST", "/auth/login", json=credentials).json()["accessToken"]
                headers = {"Authorization": "Bearer " + token, "X-Post-Client-Version": "1"}
                call("PUT", "/profile", headers=headers, json={"auditText": "Perfil educativo", "brandText": "Marca acolhedora"})
                chat_id = call("POST", "/chats", headers=headers, json={"postType": "single"}).json()["id"]

                def run_job(content, mode, base=None):
                    payload = {"content": content, "mode": mode}
                    if base: payload["baseVersionId"] = base
                    job = call("POST", f"/chats/{chat_id}/messages", headers=headers, json=payload).json()["jobId"]
                    result = {}
                    def terminal():
                        result.update(call("GET", f"/chats/{chat_id}/jobs/{job}/status", headers=headers).json())
                        if result["status"] == "failed": raise RuntimeError("Job falhou: " + str(result.get("errorCode")))
                        return result["status"] == "done"
                    wait_until(terminal, "Job não concluiu", timeout=120)
                    thread = call("GET", f"/chats/{chat_id}", headers=headers).json()
                    raw = docker("exec", names["worker"], "python", "-c", "import boto3,os,sys; print(boto3.client('s3').get_object(Bucket=os.environ['AWS_S3_BUCKET'],Key='slides/'+sys.argv[1]+'/document.json')['Body'].read().decode())", job)
                    return job, thread, json.loads(raw)

                first_job, first, first_doc = run_job("Crie um post", "create")
                assert first_doc["schemaVersion"] == 3 and first_doc["slides"][0]["background"]["type"] == "image"
                first_asset = first_doc["slides"][0]["background"]["assetId"]
                assert first_doc["credits"][first_asset]["creator"] == "Pessoa autora"
                assert any("commons.wikimedia.org" in message["content"] for message in first["contents"])
                _, edited, edit_doc = run_job("Altere o título", "edit", first["currentVersionId"])
                assert edit_doc["slides"][0]["background"]["assetId"] == first_asset
                assert edit_doc["slides"][0]["elements"][0]["content"] == "Título editado"
                _, final, final_doc = run_job("Troque a imagem", "edit", edited["currentVersionId"])
                new_asset = final_doc["slides"][0]["background"]["assetId"]
                assert new_asset != first_asset and final_doc["credits"][new_asset]["sourceUrl"].endswith("segunda")
                assert final_doc["slides"][0]["elements"][0]["content"] == "Título editado"
                raw = docker("exec", names["worker"], "python", "-c", "import boto3,os,sys; print(boto3.client('s3').get_object(Bucket=os.environ['AWS_S3_BUCKET'],Key='slides/'+sys.argv[1]+'/document.json')['Body'].read().decode())", first_job)
                assert json.loads(raw) == first_doc
                stale = client.post(f"/chats/{chat_id}/messages", headers=headers, json={"content": "Editar", "mode": "edit", "baseVersionId": first["currentVersionId"]})
                assert stale.status_code == 409
                assert final["currentVersionId"] != first["currentVersionId"]
                failure_job = call("POST", f"/chats/{chat_id}/messages", headers=headers, json={"content": "Troque a imagem indisponível", "mode": "edit", "baseVersionId": final["currentVersionId"]}).json()["jobId"]
                failure = {}
                def failed():
                    failure.update(call("GET", f"/chats/{chat_id}/jobs/{failure_job}/status", headers=headers).json())
                    return failure["status"] in ("done", "failed")
                wait_until(failed, "Job com provedor indisponível não concluiu", timeout=120)
                assert failure["status"] == "failed" and failure.get("errorCode") == "IMAGE_SEARCH_FAILED"
                assert call("GET", f"/chats/{chat_id}", headers=headers).json()["currentVersionId"] == final["currentVersionId"]
                print("V3: criação, edição, troca, créditos, histórico, conflito e falha do provedor validados com LocalStack e Openverse simulado.")
        except Exception:
            for part in ("api", "worker"):
                result = subprocess.run(["docker", "logs", names[part]], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                print(f"Logs {part}:\n" + "\n".join((result.stdout + result.stderr).splitlines()[-30:]), file=sys.stderr)
            raise
        finally:
            for name in reversed(list(names.values())): docker("rm", "-f", name, check=False)
            docker("network", "rm", network, check=False)


if __name__ == "__main__":
    main()

"""Isolated real-S3 callback and 24-hour reconciliation rehearsal.

Run prepare once, keep the isolated Docker volume, then run verify after it is ready.
Never point this rehearsal at production or another Docker Compose project.
"""
import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

import boto3
from botocore.exceptions import ClientError
import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from summarize_job_metrics import summarize

PROJECT = "postmind-t18-real-s3"
COMPOSE = ["docker", "compose", "-p", PROJECT, "-f", str(ROOT / "docker-compose.yml"),
           "-f", str(ROOT / "tests/docker_hybrid/real_s3.compose.yml")]


def run(*command, env=None):
    return subprocess.run(command, check=True, cwd=ROOT, env=env, text=True, capture_output=True).stdout.strip()


def compose(*args, reconcile=False, proxy=False):
    env = {**os.environ, "T18_RECONCILE_ENABLED": str(reconcile).lower(),
           "T18_HTTPS_PROXY": "http://s3-gate:3128" if proxy else ""}
    return run(*COMPOSE, *args, env=env)


def read_env(path):
    from dotenv import dotenv_values
    return dotenv_values(path)


def storage():
    api, worker = [read_env(ROOT / path) for path in ("apps/api/.env", "apps/worker/.env")]
    for key in ("AWS_REGION", "AWS_S3_BUCKET", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"):
        if not api.get(key) or api.get(key) != worker.get(key):
            raise RuntimeError(f"{key} ausente ou diferente entre API e worker")
    for values in (api, worker):
        if any(values.get(key) for key in ("AWS_ENDPOINT_URL", "AWS_ENDPOINT_URL_S3", "AWS_S3_PUBLIC_ENDPOINT")):
            raise RuntimeError("O ensaio exige S3 AWS real sem endpoint customizado")
    region = worker["AWS_REGION"]
    client = boto3.client("s3", region_name=region, endpoint_url=f"https://s3.{region}.amazonaws.com",
                          aws_access_key_id=worker["AWS_ACCESS_KEY_ID"], aws_secret_access_key=worker["AWS_SECRET_ACCESS_KEY"])
    return client, worker["AWS_S3_BUCKET"], region


def sql(query, **params):
    command = ["docker", "exec", "-i", PROJECT + "-postgres-1", "psql", "-U", "t18",
               "-d", "content_creator", "-v", "ON_ERROR_STOP=1", "-tA"]
    for name, value in params.items():
        command.extend(["-v", f"{name}={value}"])
    return subprocess.run(command, input=query, check=True, cwd=ROOT, text=True, capture_output=True).stdout.strip()


def wait(check, message, timeout=180):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            value = check()
            if value:
                return value
        except (httpx.HTTPError, subprocess.CalledProcessError):
            pass
        time.sleep(2)
    raise RuntimeError(message)


def status(client, headers, chat_id, job_id):
    response = client.get(f"/chats/{chat_id}/jobs/{job_id}/status", headers=headers)
    response.raise_for_status()
    value = response.json()
    if value["status"] == "failed":
        raise RuntimeError(f"Job falhou: {value.get('errorCode')}")
    return value["status"] == "done"


def proxy_stats():
    result = run("docker", "exec", PROJECT + "-callback-1", "python", "-c",
                 "import urllib.request; print(urllib.request.urlopen('http://localhost:8081/__rehearsal/stats').read().decode())")
    return json.loads(result)


def volume_exists():
    return subprocess.run(["docker", "volume", "inspect", PROJECT + "_pgdata"], stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL).returncode == 0


def prepare():
    client, bucket, region = storage()
    if volume_exists():
        raise RuntimeError("Volume de ensaio já existe; execute verify ou investigue antes de reiniciar")
    client.head_bucket(Bucket=bucket)
    print("Iniciando ambiente isolado para callback e preparação da reconciliação.", flush=True)
    compose("up", "-d", "--no-build", "postgres", "api", "worker")
    address = compose("port", "api", "8080").splitlines()[0]
    base = "http://" + address
    wait(lambda: httpx.get(base + "/health", timeout=3).status_code == 200, "API indisponível")
    wait(lambda: run("docker", "exec", PROJECT + "-worker-1", "python", "-c",
                     "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" ) == "",
         "Worker indisponível")
    with httpx.Client(base_url=base, timeout=30) as api:
        def request(method, path, **kwargs):
            response = api.request(method, path, **kwargs)
            response.raise_for_status()
            return response
        credentials = {"email": f"t18-{uuid.uuid4()}@example.com", "password": "password123"}
        request("POST", "/auth/register", json=credentials)
        token = request("POST", "/auth/login", json=credentials).json()["accessToken"]
        headers = {"Authorization": "Bearer " + token, "X-Post-Client-Version": "1"}
        data = ROOT / "tests/e2e/testdata"
        request("PUT", "/profile", headers=headers,
                json={"auditText": (data / "AUDIT.md").read_text(), "brandText": (data / "BRAND.md").read_text()})
        chat = request("POST", "/chats", headers=headers, json={"postType": "single"}).json()
        if chat["postFormat"] != "structured_v1":
            raise RuntimeError("O chat não usa o formato estruturado")
        chat_id = str(uuid.UUID(chat["id"]))
        result = request("POST", f"/chats/{chat_id}/messages", headers=headers,
                         json={"mode": "create", "content": "Crie um post único sobre testes automatizados."}).json()
        job_id = str(uuid.UUID(result["jobId"]))
        wait(lambda: status(api, headers, chat_id, job_id), "Job não concluiu", timeout=600)
        stats = wait(lambda: (s if (s := proxy_stats())["completion_attempts"] >= 2 else None),
                     "Retentativa de callback não observada")
        if stats["responses_dropped"] != 1:
            raise RuntimeError("A resposta esperada não foi descartada")
        chat = request("GET", f"/chats/{chat_id}", headers=headers).json()
        versions = [item for item in chat["contents"] if item.get("versionId")]
        if len(versions) != 1 or chat["currentVersionId"] != versions[0]["versionId"]:
            raise RuntimeError("O callback não preservou uma única versão no chat")
        if sql("SELECT count(*) FROM post_versions WHERE job_id = :'job_id'::uuid", job_id=job_id) != "1":
            raise RuntimeError("O callback não preservou uma única versão no banco")
        request("DELETE", f"/chats/{chat_id}", headers=headers)
    if sql("SELECT count(*) FROM chat_cleanup_tasks WHERE chat_id = :'chat_id'::uuid", chat_id=chat_id) != "1":
        raise RuntimeError("Inventário do chat não encontrado")
    key = f"slides/{job_id}/t18-reconciliation-probe.bin"
    # Persist the marker before upload, so an interrupted prepare retains its identity.
    sql("CREATE TABLE t18_rehearsal (job_id uuid PRIMARY KEY, chat_id uuid NOT NULL, bucket text NOT NULL, region text NOT NULL)")
    sql("INSERT INTO t18_rehearsal VALUES (:'job_id'::uuid, :'chat_id'::uuid, :'bucket', :'region')",
        job_id=job_id, chat_id=chat_id, bucket=bucket, region=region)
    client.put_object(Bucket=bucket, Key=key, Body=b"postmind-t18-probe", IfNoneMatch="*")
    created = client.head_object(Bucket=bucket, Key=key)["LastModified"]
    ready = created + timedelta(hours=24, minutes=1)
    print("Callback: resposta descartada após commit, retentativa observada e uma versão persistida.")
    print("Objeto de reconciliação criado. Executar verify após:", ready.isoformat())
    print("Mantenha o volume Docker isolado; sem ele não será possível continuar o ensaio.")
    compose("stop")


def missing(client, bucket, key):
    try:
        client.head_object(Bucket=bucket, Key=key)
        return False
    except ClientError as exc:
        if exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode") == 404:
            return True
        raise


def gate_request(path, method="GET"):
    code = ("import urllib.request; "
            f"request=urllib.request.Request('http://localhost:3128{path}', method='{method}'); "
            "print(urllib.request.urlopen(request).read().decode())")
    return run("docker", "exec", PROJECT + "-s3-gate-1", "python", "-c", code)


def verify():
    client, bucket, region = storage()
    if not volume_exists():
        raise RuntimeError("Volume do ensaio não existe; não é seguro continuar")
    recent = protected = reference_id = None
    compose("up", "-d", "--no-build", "postgres", "api", "worker")
    try:
        row = json.loads(sql("SELECT row_to_json(t)::text FROM t18_rehearsal t"))
        if row["bucket"] != bucket or row["region"] != region:
            raise RuntimeError("O bucket ou a região diferem do ensaio preparado")
        job_id = str(uuid.UUID(row["job_id"]))
        chat_id = str(uuid.UUID(row["chat_id"]))
        key = f"slides/{job_id}/t18-reconciliation-probe.bin"
        head = client.head_object(Bucket=bucket, Key=key)
        eligible = head["LastModified"] + timedelta(hours=24, minutes=1)
        if datetime.now(timezone.utc) < eligible:
            raise RuntimeError("A janela de 24 horas ainda não terminou: " + eligible.isoformat())
        prefix = f"slides/{job_id}/"
        recent = prefix + f"t18-recent-probe-{uuid.uuid4()}.bin"
        protected = prefix + f"t18-referenced-probe-{uuid.uuid4()}.bin"
        client.put_object(Bucket=bucket, Key=recent, Body=b"postmind-t18-recent", IfNoneMatch="*")
        client.put_object(Bucket=bucket, Key=protected, Body=b"postmind-t18-referenced", IfNoneMatch="*")
        reference_id = str(uuid.uuid4())
        sql("""INSERT INTO user_profile_references (id, user_id, s3_key)
               SELECT :'ref_id'::uuid, id, :'s3_key' FROM users LIMIT 1;
               UPDATE chat_cleanup_tasks SET object_keys =
               (object_keys::jsonb || jsonb_build_array(:'s3_key'::text))::text
               WHERE chat_id = :'chat_id'::uuid;""",
            ref_id=reference_id, s3_key=protected, chat_id=chat_id)
        if sql("SELECT count(*) FROM user_profile_references WHERE id = :'ref_id'::uuid", ref_id=reference_id) != "1":
            raise RuntimeError("Não foi possível preparar a referência protegida")
        compose("up", "-d", "--no-deps", "--force-recreate", "s3-gate")
        wait(lambda: gate_request("/__rehearsal/stats") != "", "Proxy S3 indisponível")
        compose("up", "-d", "--no-deps", "--force-recreate", "api", reconcile=True, proxy=True)
        wait(lambda: json.loads(gate_request("/__rehearsal/stats"))["connections"] > 0,
             "A reconciliação não iniciou uma chamada ao S3", timeout=60)
        run("docker", "kill", PROJECT + "-api-1")
        gate_request("/__rehearsal/release", "POST")
        compose("up", "-d", "--no-deps", "--force-recreate", "api", reconcile=True, proxy=True)
        wait(lambda: missing(client, bucket, key), "A reconciliação não removeu o objeto antigo", timeout=120)
        def reconcile_metrics():
            values = summarize(compose("logs", "--no-color", "api").splitlines())["reconcile"]
            return values if values["done_runs"] else None
        metrics = wait(reconcile_metrics, "Métrica de reconciliação concluída não encontrada", timeout=30)
        if not all(metrics[field] > 0 for field in ("done_runs", "inventories", "prefixes", "listed_objects", "attempted_objects")):
            raise RuntimeError("Métricas não comprovam a reconciliação esperada")
        client.head_object(Bucket=bucket, Key=recent)
        client.head_object(Bucket=bucket, Key=protected)
        if sql("SELECT count(*) FROM chat_cleanup_tasks WHERE chat_id = :'chat_id'::uuid", chat_id=chat_id) != "1":
            raise RuntimeError("Inventário do chat não foi preservado")
        print("Reconciliação retomada após interrupção: objeto antigo removido; objeto recente, referência e inventário preservados.")
        print("Métricas agregadas:", json.dumps(metrics, ensure_ascii=False))
    finally:
        try:
            if reference_id:
                sql("DELETE FROM user_profile_references WHERE id = :'ref_id'::uuid", ref_id=reference_id)
            for artifact in (recent, protected):
                if artifact:
                    client.delete_object(Bucket=bucket, Key=artifact)
        finally:
            compose("stop")
    print("Para remover o volume isolado após registrar as evidências: docker compose -p postmind-t18-real-s3 -f docker-compose.yml -f tests/docker_hybrid/real_s3.compose.yml down -v")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "verify"))
    arguments = parser.parse_args()
    try:
        {"prepare": prepare, "verify": verify}[arguments.action]()
    except Exception as exc:
        print(f"Ensaio interrompido: {type(exc).__name__}: {exc}")
        raise SystemExit(1) from None

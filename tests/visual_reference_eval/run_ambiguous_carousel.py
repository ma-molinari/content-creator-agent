"""Run one synthetic carousel with conflicting references on an isolated stack."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import time
import uuid
from urllib.parse import urlparse

import boto3
from botocore.config import Config
from dotenv import dotenv_values
import httpx
from PIL import Image
import io

from run import AUDIT, BRAND, CASES, ROOT, make_reference


def prepare_references(output: Path, sources: list[Path] | None) -> list[Path]:
    paths = []
    if sources:
        if len(sources) > 8:
            raise ValueError("Use no máximo oito referências")
        for index, source in enumerate(sources, 1):
            if not source.is_file() or Image.open(source).format != "PNG":
                raise ValueError("Cada referência deve ser um arquivo PNG válido")
            target = output / f"referencia-{index}.png"
            shutil.copyfile(source, target)
            paths.append(target)
    else:
        for name, palette in CASES.items():
            target = output / f"referencia-{name}.png"
            make_reference(target, palette)
            paths.append(target)
    return paths


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--output", required=True)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--references", nargs="+", type=Path, help="Arquivos PNG autorizados; omitido usa referências sintéticas")
    group.add_argument("--no-references", action="store_true", help="Executa um controle sem referências")
    parser.add_argument("--audit", default=AUDIT)
    parser.add_argument("--brand", default=BRAND)
    parser.add_argument("--prompt", default="Crie um carrossel de três slides sobre pausas curtas durante o trabalho.")
    args = parser.parse_args()
    parsed = urlparse(args.api_url)
    if parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "localhost"):
        raise ValueError("A API deve ser local e isolada")
    output = Path(args.output).resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError("Use um diretório de saída vazio")
    output.mkdir(parents=True, exist_ok=True)
    api, worker = [dotenv_values(ROOT / name) for name in ("apps/api/.env", "apps/worker/.env")]
    keys = ("AWS_REGION", "AWS_S3_BUCKET", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY")
    if any(not api.get(key) or api.get(key) != worker.get(key) for key in keys):
        raise ValueError("Configuração S3 ausente ou divergente")
    if any(values.get(key) for values in (api, worker) for key in ("AWS_ENDPOINT_URL", "AWS_ENDPOINT_URL_S3", "AWS_S3_PUBLIC_ENDPOINT")):
        raise ValueError("O ensaio exige S3 AWS real sem endpoint customizado")
    region, bucket = worker["AWS_REGION"], worker["AWS_S3_BUCKET"]
    s3 = boto3.client("s3", region_name=region, endpoint_url=f"https://s3.{region}.amazonaws.com",
                      config=Config(connect_timeout=5, read_timeout=10, retries={"max_attempts": 2}),
                      aws_access_key_id=worker["AWS_ACCESS_KEY_ID"], aws_secret_access_key=worker["AWS_SECRET_ACCESS_KEY"])
    reference_paths = [] if args.no_references else prepare_references(output, args.references)
    reference_ids = []
    active = False
    chat_id = job_id = None
    with httpx.Client(base_url=args.api_url, timeout=30) as client:
        def request(method, path, **kwargs):
            for attempt in range(13):
                response = client.request(method, path, **kwargs)
                if response.status_code != 429 or attempt == 12:
                    response.raise_for_status()
                    return response
                time.sleep(10)
            raise RuntimeError("Limite de requisições persistiu")

        credentials = {"email": f"visual-carousel-{uuid.uuid4()}@example.com", "password": "TesteVisual123!"}
        request("POST", "/auth/register", json=credentials)
        token = request("POST", "/auth/login", json=credentials).json()["accessToken"]
        headers = {"Authorization": "Bearer " + token, "X-Post-Client-Version": "1"}
        request("PUT", "/profile", headers=headers, json={"auditText": args.audit, "brandText": args.brand})
        try:
            for path in reference_paths:
                with path.open("rb") as image:
                    refs = request("POST", "/profile/references", headers=headers, files={"file": (path.name, image, "image/png")}).json()["references"]
                reference_ids = [item["id"] for item in refs]
            chat = request("POST", "/chats", headers=headers, json={"postType": "carousel"}).json()
            chat_id = chat["id"]
            if chat["postFormat"] != "structured_v1":
                raise RuntimeError("A stack não criou um chat híbrido")
            job = request("POST", f"/chats/{chat_id}/messages", headers=headers,
                          json={"content": args.prompt, "mode": "create"}).json()
            job_id = str(uuid.UUID(job["jobId"]))
            active = True
            for _ in range(100):
                status = request("GET", f"/chats/{chat_id}/jobs/{job_id}/status", headers=headers).json()
                if status["status"] in ("done", "failed"):
                    active = False
                    if status["status"] == "failed":
                        raise RuntimeError(f"Job falhou: {status.get('errorCode')}")
                    break
                time.sleep(6)
            if active:
                raise RuntimeError("Job ainda ativo; preserve a stack e investigue antes de removê-la")
            result = request("GET", f"/chats/{chat_id}", headers=headers).json()
            images = [image for item in result["contents"] if item.get("versionId") for image in item.get("images", [])]
            if len(images) != 3:
                raise RuntimeError("O carrossel não possui três slides")
            for index, image in enumerate(images, 1):
                response = httpx.get(image["url"], timeout=30)
                response.raise_for_status()
                if Image.open(io.BytesIO(response.content)).size != (1080, 1350):
                    raise RuntimeError("Dimensões inesperadas")
                (output / f"slide-{index}.jpeg").write_bytes(response.content)
            snapshot = json.loads(s3.get_object(Bucket=bucket, Key=f"slides/{job_id}/document.json")["Body"].read())
            (output / "documento.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n")
            print("Carrossel gerado e baixado.", flush=True)
        finally:
            if not active:
                if chat_id:
                    request("DELETE", f"/chats/{chat_id}", headers=headers)
                if job_id:
                    objects = [{"Key": item["Key"]} for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=f"slides/{job_id}/") for item in page.get("Contents", [])]
                    if objects and s3.delete_objects(Bucket=bucket, Delete={"Objects": objects, "Quiet": True}).get("Errors"):
                        raise RuntimeError("Falha parcial na limpeza dos objetos do ensaio")
                for reference_id in reference_ids:
                    request("DELETE", f"/profile/references/{reference_id}", headers=headers)


if __name__ == "__main__":
    main()

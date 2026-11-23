"""Generate synthetic control and reference samples on a local isolated hybrid stack."""
from __future__ import annotations

import argparse
import io
import json
from pathlib import Path
import time
import uuid
from urllib.parse import urlparse

import boto3
from botocore.config import Config
from dotenv import dotenv_values
import httpx
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
PROMPT = 'Crie um post único com uma dica breve sobre fazer pausas durante o trabalho.'
AUDIT = 'Perfil educativo para adultos interessados em hábitos simples de bem-estar e rotina de trabalho.'
BRAND = 'Marca educativa, com linguagem clara, acolhedora e objetiva. Prefere textos curtos e legíveis.'
CASES = {
    'roxo': {'background': '#291044', 'foreground': '#ffffff', 'accent': '#d5f542', 'alignment': 'left'},
    'claro': {'background': '#fff5e9', 'foreground': '#12315d', 'accent': '#f26930', 'alignment': 'center'},
}


def resolved_color(snapshot: dict, color: object) -> str:
    if isinstance(color, str):
        return color
    if not isinstance(color, dict) or len(color) != 1:
        raise ValueError('Cor estruturada inválida no snapshot')
    if 'hex' in color:
        return color['hex']
    return snapshot['palette'][color['token']]


def make_reference(path: Path, palette: dict[str, str]) -> None:
    image = Image.new('RGB', (1080, 1350), palette['background'])
    draw = ImageDraw.Draw(image)
    font_path = '/System/Library/Fonts/Supplemental/Arial.ttf'
    if not Path(font_path).exists():
        font_path = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    heading = ImageFont.truetype(font_path, 94)
    body = ImageFont.truetype(font_path, 48)
    is_center = palette['alignment'] == 'center'
    draw.rounded_rectangle((75, 75, 1005, 125), radius=18, fill=palette['accent'])
    if is_center:
        title = 'Pequenas pausas,\ngrandes efeitos'
        paragraph = 'Alguns minutos de descanso\npodem ajudar na sua rotina.'
        title_width = draw.multiline_textbbox((0, 0), title, font=heading, spacing=24)[2]
        body_width = draw.multiline_textbbox((0, 0), paragraph, font=body, spacing=20)[2]
        draw.multiline_text(((1080 - title_width) / 2, 250), title, font=heading,
                            fill=palette['foreground'], align='center', spacing=24)
        draw.multiline_text(((1080 - body_width) / 2, 650), paragraph, font=body,
                            fill=palette['foreground'], align='center', spacing=20)
    else:
        draw.multiline_text((95, 250), 'Pequenas pausas,\ngrandes efeitos', font=heading,
                            fill=palette['foreground'], spacing=24)
        draw.multiline_text((95, 650), 'Alguns minutos de descanso\npodem ajudar na sua rotina.', font=body,
                            fill=palette['foreground'], spacing=20)
    draw.rounded_rectangle((95, 1120, 455, 1190), radius=20, fill=palette['accent'])
    image.save(path, 'PNG', optimize=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--api-url', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    parsed = urlparse(args.api_url)
    if parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', 'localhost'):
        raise ValueError('A API deve ser local e isolada')
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    api_env, worker_env = [dotenv_values(ROOT / p) for p in ('apps/api/.env', 'apps/worker/.env')]
    for key in ('AWS_REGION', 'AWS_S3_BUCKET', 'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY'):
        if not api_env.get(key) or api_env.get(key) != worker_env.get(key):
            raise ValueError(f'{key} ausente ou divergente')
    if any(env.get(key) for env in (api_env, worker_env) for key in ('AWS_ENDPOINT_URL', 'AWS_ENDPOINT_URL_S3', 'AWS_S3_PUBLIC_ENDPOINT')):
        raise ValueError('O ensaio exige o S3 AWS real, sem endpoint customizado')
    storage = boto3.client('s3', region_name=worker_env['AWS_REGION'],
                           endpoint_url=f"https://s3.{worker_env['AWS_REGION']}.amazonaws.com",
                           config=Config(connect_timeout=5, read_timeout=10, retries={'max_attempts': 2}),
                           aws_access_key_id=worker_env['AWS_ACCESS_KEY_ID'],
                           aws_secret_access_key=worker_env['AWS_SECRET_ACCESS_KEY'])
    bucket = worker_env['AWS_S3_BUCKET']
    for name, palette in CASES.items():
        make_reference(output / f'referencia-{name}.png', palette)
    credentials = {'email': f'visual-eval-{uuid.uuid4()}@example.com', 'password': 'TesteVisual123!'}
    result_file = output / 'resultados.json'
    if result_file.exists() and not args.resume:
        raise RuntimeError('Os resultados já existem; use --resume para preservar as amostras')
    results = json.loads(result_file.read_text()) if args.resume and result_file.exists() else []
    reference_id = None
    active = False
    with httpx.Client(base_url=args.api_url, timeout=30) as client:
        def request(method, path, **kwargs):
            for attempt in range(13):
                response = client.request(method, path, **kwargs)
                if response.status_code != 429 or attempt == 12:
                    response.raise_for_status()
                    return response
                time.sleep(10)
            raise RuntimeError('Limite de requisições persistiu')

        def clear_reference():
            nonlocal reference_id
            if reference_id:
                request('DELETE', f'/profile/references/{reference_id}', headers=headers)
                reference_id = None

        def generate(label: str, number: int) -> None:
            nonlocal active
            if any(item['condition'] == label and item['sample'] == number for item in results):
                print(f'{label} {number}: amostra existente preservada', flush=True)
                return
            chat = request('POST', '/chats', headers=headers, json={'postType': 'single'}).json()
            chat_id = chat['id']
            if chat['postFormat'] != 'structured_v1':
                raise RuntimeError('A stack não criou um chat híbrido')
            terminal = False
            job_id = None
            try:
                job = request('POST', f'/chats/{chat_id}/messages', headers=headers,
                              json={'content': PROMPT, 'mode': 'create'}).json()
                job_id = str(uuid.UUID(job['jobId']))
                active = True
                deadline = time.monotonic() + 600
                while time.monotonic() < deadline:
                    status = request('GET', f'/chats/{chat_id}/jobs/{job_id}/status', headers=headers).json()
                    if status['status'] in ('done', 'failed'):
                        terminal, active = True, False
                        if status['status'] == 'failed':
                            failure_file = output / 'falhas.json'
                            failures = json.loads(failure_file.read_text()) if failure_file.exists() else []
                            failures.append({'condition': label, 'sample': number, 'errorCode': status.get('errorCode')})
                            failure_file.write_text(json.dumps(failures, ensure_ascii=False, indent=2) + '\n')
                            raise RuntimeError(f"Job {label}/{number} falhou: {status.get('errorCode')}")
                        break
                    time.sleep(6)
                if not terminal:
                    raise RuntimeError(f'Tempo limite para {label}/{number}; preserve a stack e seus dados')
                result = request('GET', f'/chats/{chat_id}', headers=headers).json()
                images = [image for item in result['contents'] if item.get('versionId') for image in item.get('images', [])]
                if len(images) != 1:
                    raise RuntimeError('O resultado não possui exatamente um slide')
                response = httpx.get(images[0]['url'], timeout=30)
                if response.status_code != 200:
                    raise RuntimeError(f'Download da imagem falhou: HTTP {response.status_code}')
                image = Image.open(io.BytesIO(response.content))
                if image.size != (1080, 1350):
                    raise RuntimeError('Dimensões inesperadas')
                (output / f'{label}-{number}.jpeg').write_bytes(response.content)
                snapshot = json.loads(storage.get_object(Bucket=bucket, Key=f'slides/{job_id}/document.json')['Body'].read())
                manifest = json.loads(storage.get_object(Bucket=bucket, Key=f'slides/{job_id}/assets.json')['Body'].read())
                slide = snapshot['slides'][0]
                styles = [{'role': item['role'], **item['style'], 'color': resolved_color(snapshot, item['style']['color'])}
                          for item in slide['elements'] if item['type'] == 'text']
                decorations = [{'index': index, 'kind': item['kind'], 'color': resolved_color(snapshot, item['color']),
                                'width': item['width'], 'thickness': item['thickness'], 'corner': item['corner']}
                               for index, item in enumerate(slide['elements']) if item['type'] == 'decoration']
                results.append({'condition': label, 'sample': number, 'layout': slide['layout'], 'schemaVersion': snapshot['schemaVersion'],
                                'background': resolved_color(snapshot, slide['background']['color']), 'textStyles': styles,
                                'decorations': decorations,
                                'embeddedAssetCount': len(manifest)})
                (output / 'resultados.json').write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n')
                print(f'{label} {number}: concluído', flush=True)
            finally:
                if terminal or job_id is None:
                    request('DELETE', f'/chats/{chat_id}', headers=headers)
                    if job_id:
                        prefix = f'slides/{job_id}/'
                        objects = [{'Key': item['Key']} for page in storage.get_paginator('list_objects_v2').paginate(Bucket=bucket, Prefix=prefix) for item in page.get('Contents', [])]
                        if objects:
                            result = storage.delete_objects(Bucket=bucket, Delete={'Objects': objects, 'Quiet': True})
                            if result.get('Errors'):
                                raise RuntimeError('Falha parcial na limpeza dos objetos do ensaio')

        request('POST', '/auth/register', json=credentials)
        token = request('POST', '/auth/login', json=credentials).json()['accessToken']
        headers = {'Authorization': 'Bearer ' + token, 'X-Post-Client-Version': '1'}
        request('PUT', '/profile', headers=headers, json={'auditText': AUDIT, 'brandText': BRAND})
        try:
            for number in (1, 2):
                generate('controle', number)
            for name in CASES:
                path = output / f'referencia-{name}.png'
                with path.open('rb') as image:
                    response = request('POST', '/profile/references', headers=headers,
                                       files={'file': (path.name, image, 'image/png')})
                references = response.json()['references']
                if len(references) != 1:
                    raise RuntimeError('Quantidade inesperada de referências')
                reference_id = references[0]['id']
                for number in (1, 2):
                    generate(name, number)
                clear_reference()
        finally:
            if not active:
                clear_reference()
    print('Ensaio concluído; amostras disponíveis no diretório de saída.', flush=True)


if __name__ == '__main__':
    main()

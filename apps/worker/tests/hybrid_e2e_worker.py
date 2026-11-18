"""Run the real worker graph against a local Go API with external services simulated."""
import asyncio
import importlib
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.job_payload import DispatchPayload, initial_state
from app.main import _run_job
from app.post_document import PostDocumentV1
from app.post_operations import apply_operations

pipeline = importlib.import_module("app.nodes.structured_pipeline")
graph_module = importlib.import_module("app.graph")
config_module = importlib.import_module("app.config")
root = Path(os.environ["HYBRID_E2E_STORE"])
settings = SimpleNamespace(aws_region="test", aws_access_key_id="test", aws_secret_access_key="test", aws_s3_bucket="test", go_api_url=os.environ["HYBRID_E2E_API"], worker_api_key=os.environ["HYBRID_E2E_KEY"])


class FileS3:
    def put_object(self, *, Bucket, Key, Body, ContentType, IfNoneMatch):
        assert IfNoneMatch == "*"
        path = root / Key
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as output:
            output.write(Body)
        Path(str(path) + ".type").write_text(ContentType)

    def get_object(self, *, Bucket, Key):
        path = root / Key
        return {"Body": path.open("rb"), "ContentType": Path(str(path) + ".type").read_text()}

    def head_object(self, *, Bucket, Key):
        assert (root / Key).exists()
        return {}


async def no_progress(*_args, **_kwargs):
    pass


async def generate(**_kwargs):
    return PostDocumentV1.model_validate({"schemaVersion": 1, "postType": "single", "slides": [{
        "id": "s", "layout": "hero", "background": {"type": "solid", "color": "#000000"},
        "elements": [{"id": "title", "type": "text", "role": "heading", "content": "Original", "style": {"color": "#ffffff", "size": "large"}}],
    }]})


async def edit(*, document, authorized_assets, **_kwargs):
    return apply_operations(document, [{"op": "set_text", "slideId": "s", "elementId": "title", "content": "Editado"}], authorized_assets)


async def render(_document, _assets):
    return ([{"filename": "slide_01.html", "html": "<html>simulado</html>"}], [{"filename": "slide_01.jpeg", "jpeg_bytes": b"\xff\xd8\xffsimulado"}])


pipeline.get_settings = lambda: settings
config_module.get_settings = lambda: settings
pipeline.boto3.client = lambda *_args, **_kwargs: FileS3()
pipeline.report_job_progress = no_progress
graph_module.report_job_progress = no_progress
pipeline.generate_structured_post = generate
pipeline.plan_structured_edit = edit
pipeline.render_structured_post = render
payload = DispatchPayload.model_validate(json.load(sys.stdin))
asyncio.run(_run_job(initial_state(payload)))

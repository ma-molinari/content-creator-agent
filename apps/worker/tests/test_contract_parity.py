"""Shared contract cases consumed by both the API and the worker."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.post_document import PostDocumentV1


CASES = json.loads(
    (Path(__file__).resolve().parents[3] / "tests/fixtures/structured_documents.json").read_text()
)


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["name"])
def test_shared_document_contract(case):
    if case["valid"]:
        PostDocumentV1.model_validate(case["document"])
    else:
        with pytest.raises(ValidationError):
            PostDocumentV1.model_validate(case["document"])

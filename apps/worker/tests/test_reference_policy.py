"""Explicit reference selection and preservation of already published images."""

import pytest

from app.post_document import PostDocumentV1
from app.post_document_v2 import promote_v1
from app.reference_policy import ReferenceSelectionError, selected_references, validate_reference_usage


REFS = {"ref-a": "users/u/ref-a.png", "ref-b": "users/u/ref-b.png"}
KEYS = [REFS["ref-a"], REFS["ref-b"]]


@pytest.mark.parametrize("prompt", [
    "Crie um post seguindo as referências visuais",
    "Use as referências como inspiração para o estilo",
    "Inclua as referências de estilo no post",
    "Inclua uma barra inspirada na referência",
    "Não inclua a imagem de referência",
    "Altere apenas o texto",
])
def test_style_requests_do_not_select_references(prompt):
    assert selected_references(prompt, REFS, KEYS) == set()


@pytest.mark.parametrize("prompt,expected", [
    ("Inclua a primeira imagem de referência no post", {"ref-a"}),
    ("Insira a referência 2 no slide", {"ref-b"}),
    ("Coloque ambas as referências no post", {"ref-a", "ref-b"}),
    ("Use a referência 1 como imagem", {"ref-a"}),
    ("Inclua a primeira imagem de referência na segunda página", {"ref-a"}),
])
def test_explicit_reference_selection(prompt, expected):
    assert selected_references(prompt, REFS, KEYS) == expected


def test_ambiguous_or_unavailable_reference_fails_closed():
    with pytest.raises(ReferenceSelectionError, match="qual"):
        selected_references("Inclua a referência no post", REFS, KEYS)
    with pytest.raises(ReferenceSelectionError, match="disponível"):
        selected_references("Inclua a terceira referência no post", REFS, KEYS)
    with pytest.raises(ReferenceSelectionError, match="qual"):
        selected_references("Ponha a referência escolhida no post", REFS, KEYS)


def base():
    return PostDocumentV1.model_validate({"schemaVersion": 1, "postType": "single", "slides": [{
        "id": "s", "layout": "hero", "background": {"type": "solid", "color": "#000000"},
        "elements": [{"id": "i", "type": "image", "assetId": "ref-a", "fit": "contain"}]}]})


@pytest.mark.parametrize("v2", [False, True])
def test_preserves_existing_reference_but_rejects_new_usage(v2):
    doc = promote_v1(base()) if v2 else base()
    validate_reference_usage(doc, doc, set(REFS), set())
    with pytest.raises(ReferenceSelectionError):
        validate_reference_usage(doc, None, set(REFS), set())
    validate_reference_usage(doc, None, set(REFS), {"ref-a"})


def test_explicit_selection_must_appear_in_output():
    with pytest.raises(ReferenceSelectionError, match="solicitada"):
        validate_reference_usage(base(), base(), set(REFS), {"ref-b"})
    with pytest.raises(ReferenceSelectionError, match="solicitada"):
        validate_reference_usage(base(), base(), set(REFS), {"ref-a"})

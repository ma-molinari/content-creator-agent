"""Keep style references separate from images explicitly requested in a post."""

from __future__ import annotations

import re
import unicodedata
from typing import Mapping

from app.post_document import ImageElement, PostDocumentV1
from app.post_document_v2 import PostDocumentV2


class ReferenceSelectionError(Exception):
    """A reference inclusion request needs a clearer selection."""


def _normalize(value: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", value.lower()) if not unicodedata.combining(c))


def selected_references(request: str, references: Mapping[str, str], ordered_keys: list[str]) -> set[str]:
    """Recognize conservative, explicit inclusion requests; style requests grant nothing."""
    text = _normalize(request)
    noun = r"(?:(?:imagem(?:s)?|foto(?:s)?)(?:\s+(?:de|da|das))?\s+)?referencia(?:s)?(?:\s+visual(?:is)?)?"
    modifiers = r"(?:(?:a|as|o|os|minha|minhas|primeira|segunda|terceira|quarta|quinta|sexta|setima|oitava|todas|ambas)\s+)*"
    include = re.search(rf"\b(?:inclu\w*|insir\w*|inser\w*|colo(?:c|qu)\w*|adicion\w*|incorpor\w*)\s+{modifiers}{noun}\b", text)
    use = re.search(rf"\b(?:use|usar|utilize|utilizar)\s+{modifiers}{noun}\b[^.!?]{{0,60}}\b(?:como imagem|como foto|no slide|no post|na arte)\b", text)
    if not include and not use:
        if (re.search(r"\breferencia(?:s)?\b", text)
                and re.search(r"\b(?:ponha|mostre|exiba|inclu\w*|insir\w*|inser\w*|colo(?:c|qu)\w*|adicion\w*|incorpor\w*)\b", text)
                and re.search(r"\b(?:no post|no slide|na arte|como imagem|como foto)\b", text)
                and not re.search(r"\b(?:nao|nunca|sem|evite|evitar)\b", text)):
            raise ReferenceSelectionError("Especifique qual imagem de referência deseja incluir no post.")
        return set()
    match = include or use
    assert match is not None
    phrase = match.group(0)
    tail = text[match.end():].split(".", 1)[0].split("!", 1)[0].split("?", 1)[0]
    if re.match(r"\s+(?:de estilo|de inspiracao|como inspiracao|como orientacao|como base|para inspiracao)\b", tail):
        return set()
    if re.search(r"\b(?:nao|nunca|evite|evitar)\s+(?:inclu\w*|insir\w*|inser\w*|colo(?:c|qu)\w*|adicion\w*|incorpor\w*|use|usar|utilize|utilizar)\b", text):
        return set()
    if re.search(r"\b(?:nao|nunca|sem|evite|evitar)\b", text):
        raise ReferenceSelectionError("Especifique claramente se deseja incluir alguma imagem de referência.")
    ordered = [asset_id for key in ordered_keys for asset_id, source in references.items() if source == key]
    ordered += sorted(set(references) - set(ordered))
    if not ordered:
        raise ReferenceSelectionError("Adicione uma imagem de referência antes de solicitar sua inclusão.")
    if re.search(r"\b(?:todas|ambas)\b", phrase):
        return set(ordered)
    words = ("primeira", "segunda", "terceira", "quarta", "quinta", "sexta", "setima", "oitava")
    indexes = {index for index, word in enumerate(words) if re.search(rf"\b{word}\b", phrase)}
    number = re.search(r"\breferencia(?:s)?\s*(?:numero\s*)?([1-8])\b", phrase + tail[:15])
    if number:
        indexes.add(int(number.group(1)) - 1)
    if indexes:
        if any(index >= len(ordered) for index in indexes):
            raise ReferenceSelectionError("A imagem de referência indicada não está disponível.")
        return {ordered[index] for index in indexes}
    if len(ordered) == 1:
        return {ordered[0]}
    raise ReferenceSelectionError("Especifique qual imagem de referência deseja incluir no post.")


def validate_reference_usage(
    document: PostDocumentV1 | PostDocumentV2,
    base: PostDocumentV1 | PostDocumentV2 | None,
    reference_ids: set[str], selected: set[str],
) -> None:
    """Allow unchanged inherited images, but never introduce an unselected reference."""
    previous = {(slide.id, item.id): item.asset_id for slide in base.slides for item in slide.elements
                if isinstance(item, ImageElement)} if base else {}
    for slide in document.slides:
        for item in slide.elements:
            if (isinstance(item, ImageElement) and item.asset_id in reference_ids - selected
                    and previous.get((slide.id, item.id)) != item.asset_id):
                raise ReferenceSelectionError("A imagem de referência só pode ser incluída mediante pedido explícito.")
    used = {item.asset_id for slide in document.slides for item in slide.elements if isinstance(item, ImageElement)}
    if not selected.issubset(used):
        raise ReferenceSelectionError("Não foi possível incluir a imagem de referência solicitada. Reformule o pedido.")
    if base:
        added = {item.asset_id for slide in document.slides for item in slide.elements
                 if isinstance(item, ImageElement) and previous.get((slide.id, item.id)) != item.asset_id}
        if not selected.issubset(added):
            raise ReferenceSelectionError("Não foi possível incluir a imagem de referência solicitada. Reformule o pedido.")

"""Atomic typed edits for version 2 structured documents."""

from typing import AbstractSet, Annotated, Literal, Union

from pydantic import Field, TypeAdapter, model_validator
from typing_extensions import Self

from app.post_document import Color, Identifier, _StrictModel
from app.post_document_v2 import ColorRef, Decoration, PostDocumentV2, SolidBackgroundV2, TextStyleV2, validate_authorized_assets
from app.post_operations import SetImage, SetLayout, SetText


class SetPaletteColor(_StrictModel):
    op: Literal["set_palette_color"]
    token: Literal["background", "text", "accent"]
    color: Color


class InsertDecoration(_StrictModel):
    op: Literal["insert_decoration"]
    slide_id: Identifier = Field(alias="slideId")
    after_element_id: Identifier | None = Field(alias="afterElementId")
    decoration: Decoration


class DecorationChanges(_StrictModel):
    kind: Literal["bar", "line"] | None = None
    color: ColorRef | None = None
    width: Literal["short", "medium", "full"] | None = None
    thickness: Literal["thin", "medium", "thick"] | None = None
    corner: Literal["square", "rounded"] | None = None

    @model_validator(mode="after")
    def nonempty(self) -> Self:
        if not self.model_fields_set or any(getattr(self, key) is None for key in self.model_fields_set):
            raise ValueError("decoration changes must not be empty or null")
        return self


class UpdateDecoration(_StrictModel):
    op: Literal["update_decoration"]
    slide_id: Identifier = Field(alias="slideId")
    element_id: Identifier = Field(alias="elementId")
    changes: DecorationChanges


class RemoveDecoration(_StrictModel):
    op: Literal["remove_decoration"]
    slide_id: Identifier = Field(alias="slideId")
    element_id: Identifier = Field(alias="elementId")


class SetBackgroundV2(_StrictModel):
    op: Literal["set_background"]
    slide_id: Identifier = Field(alias="slideId")
    background: SolidBackgroundV2


class SetTextStyleV2(_StrictModel):
    op: Literal["set_text_style"]
    slide_id: Identifier = Field(alias="slideId")
    element_id: Identifier = Field(alias="elementId")
    style: TextStyleV2

    @model_validator(mode="after")
    def complete_style(self) -> Self:
        if self.style.model_fields_set != {"color", "size", "font", "weight", "alignment"}:
            raise ValueError("complete text style is required")
        return self


OperationV2 = Annotated[Union[SetText, SetImage, SetLayout, SetBackgroundV2, SetTextStyleV2,
                              SetPaletteColor, InsertDecoration, UpdateDecoration, RemoveDecoration],
                        Field(discriminator="op")]
_adapter = TypeAdapter(Annotated[list[OperationV2], Field(min_length=1, max_length=100)])


def apply_operations_v2(document: PostDocumentV2, raw_operations: list[dict], authorized_assets: AbstractSet[str]) -> PostDocumentV2:
    operations = _adapter.validate_python(raw_operations, strict=True)
    data = PostDocumentV2.model_validate_json(document.model_dump_json(by_alias=True)).model_dump(mode="json", by_alias=True)
    changed_tokens = set()
    for operation in operations:
        if isinstance(operation, SetPaletteColor):
            data["palette"][operation.token] = operation.color
            changed_tokens.add(operation.token)
            continue
        slide = next((item for item in data["slides"] if item["id"] == operation.slide_id), None)
        if slide is None:
            raise ValueError("slide not found")
        if isinstance(operation, SetBackgroundV2):
            slide["background"] = operation.background.model_dump(mode="json", by_alias=True)
        elif isinstance(operation, SetLayout):
            slide["layout"] = operation.layout
        elif isinstance(operation, InsertDecoration):
            if operation.after_element_id is None:
                index = 0
            else:
                index = next((i + 1 for i, item in enumerate(slide["elements"]) if item["id"] == operation.after_element_id), -1)
                if index < 0:
                    raise ValueError("insertion target not found")
            slide["elements"].insert(index, operation.decoration.model_dump(mode="json", by_alias=True))
        else:
            element = next((item for item in slide["elements"] if item["id"] == operation.element_id), None)
            if element is None:
                raise ValueError("element not found")
            if isinstance(operation, SetText) and element["type"] == "text":
                element["content"] = operation.content
            elif isinstance(operation, SetTextStyleV2) and element["type"] == "text":
                element["style"] = operation.style.model_dump(mode="json", by_alias=True)
            elif isinstance(operation, SetImage) and element["type"] == "image":
                element.update(assetId=operation.asset_id, fit=operation.fit)
            elif isinstance(operation, UpdateDecoration) and element["type"] == "decoration":
                element.update(operation.changes.model_dump(mode="json", by_alias=True, exclude_unset=True))
            elif isinstance(operation, RemoveDecoration) and element["type"] == "decoration":
                slide["elements"].remove(element)
            else:
                raise ValueError("operation does not match element type")
    result = PostDocumentV2.model_validate(data)
    validate_authorized_assets(result, authorized_assets)
    refs = [slide["background"]["color"] for slide in data["slides"]]
    refs.extend(element["style"]["color"] if element["type"] == "text" else element["color"]
                for slide in data["slides"] for element in slide["elements"] if element["type"] in ("text", "decoration"))
    if any(not any(ref.get("token") == token for ref in refs) for token in changed_tokens):
        raise ValueError("palette token has no visible consumers")
    return result

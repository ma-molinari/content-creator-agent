"""Typed, atomic operations on structured post documents."""

from __future__ import annotations

from typing import AbstractSet, Annotated, Literal, Union

from pydantic import Field, TypeAdapter

from app.post_document import Identifier, ImageElement, PostDocumentV1, SolidBackground, TextStyle, _StrictModel


class SetText(_StrictModel):
    op: Literal["set_text"]
    slide_id: Identifier = Field(alias="slideId")
    element_id: Identifier = Field(alias="elementId")
    content: str


class SetBackground(_StrictModel):
    op: Literal["set_background"]
    slide_id: Identifier = Field(alias="slideId")
    background: SolidBackground


class SetTextStyle(_StrictModel):
    op: Literal["set_text_style"]
    slide_id: Identifier = Field(alias="slideId")
    element_id: Identifier = Field(alias="elementId")
    style: TextStyle


class SetImage(_StrictModel):
    op: Literal["set_image"]
    slide_id: Identifier = Field(alias="slideId")
    element_id: Identifier = Field(alias="elementId")
    asset_id: Identifier = Field(alias="assetId")
    fit: Literal["cover", "contain"]


class SetLayout(_StrictModel):
    op: Literal["set_layout"]
    slide_id: Identifier = Field(alias="slideId")
    layout: Literal["hero", "editorial", "quote"]


class InsertImage(_StrictModel):
    op: Literal["insert_image"]
    slide_id: Identifier = Field(alias="slideId")
    after_element_id: Identifier | None = Field(alias="afterElementId")
    image: ImageElement


Operation = Annotated[Union[SetText, SetBackground, SetTextStyle, SetImage, SetLayout, InsertImage], Field(discriminator="op")]
_operations_adapter = TypeAdapter(Annotated[list[Operation], Field(min_length=1, max_length=100)])


def apply_operations(document: PostDocumentV1, raw_operations: list[dict], authorized_assets: AbstractSet[str]) -> PostDocumentV1:
    operations = _operations_adapter.validate_python(raw_operations, strict=True)
    data = document.model_dump(mode="json", by_alias=True)
    # Validate the base again because frozen models can still contain mutable lists.
    PostDocumentV1.model_validate(data)
    for operation in operations:
        slide = next((item for item in data["slides"] if item["id"] == operation.slide_id), None)
        if slide is None:
            raise ValueError("slide not found")
        if isinstance(operation, SetBackground):
            slide["background"] = operation.background.model_dump(mode="json", by_alias=True)
        elif isinstance(operation, SetLayout):
            slide["layout"] = operation.layout
        elif isinstance(operation, InsertImage):
            if operation.image.asset_id not in authorized_assets:
                raise ValueError("image asset is not authorized")
            if operation.after_element_id is None:
                index = 0
            else:
                index = next((i + 1 for i, item in enumerate(slide["elements"]) if item["id"] == operation.after_element_id), -1)
                if index < 0:
                    raise ValueError("insertion target not found")
            slide["elements"].insert(index, operation.image.model_dump(mode="json", by_alias=True))
        else:
            element = next((item for item in slide["elements"] if item["id"] == operation.element_id), None)
            if element is None:
                raise ValueError("element not found")
            if isinstance(operation, SetText) and element["type"] == "text":
                element["content"] = operation.content
            elif isinstance(operation, SetTextStyle) and element["type"] == "text":
                element["style"] = operation.style.model_dump(mode="json", by_alias=True)
            elif isinstance(operation, SetImage) and element["type"] == "image":
                if operation.asset_id not in authorized_assets:
                    raise ValueError("image asset is not authorized")
                element["assetId"] = operation.asset_id
                element["fit"] = operation.fit
            else:
                raise ValueError("operation does not match element type")
    return PostDocumentV1.model_validate(data)

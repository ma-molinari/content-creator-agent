"""Version 2 document contract and lossless promotion from version 1."""

from __future__ import annotations

from typing import AbstractSet, Annotated, Literal, Union

from pydantic import Field, field_validator, model_validator
from typing_extensions import Self

from app.post_document import Color, Identifier, ImageElement, PostDocumentV1, TextElement, _StrictModel


class TokenColor(_StrictModel):
    token: Literal["background", "text", "accent"]


class HexColor(_StrictModel):
    hex: Color


ColorRef = Union[TokenColor, HexColor]


class Palette(_StrictModel):
    background: Color
    text: Color
    accent: Color


class SolidBackgroundV2(_StrictModel):
    type: Literal["solid"]
    color: ColorRef


class TextStyleV2(_StrictModel):
    color: ColorRef
    size: Literal["small", "medium", "large"]
    font: Literal["plus_jakarta_sans", "inter"] = "plus_jakarta_sans"
    weight: Literal["regular", "medium", "bold"] = "regular"
    alignment: Literal["left", "center", "right"] = "left"


class TextElementV2(TextElement):
    style: TextStyleV2


class Decoration(_StrictModel):
    id: Identifier
    type: Literal["decoration"]
    kind: Literal["bar", "line"]
    color: ColorRef
    width: Literal["short", "medium", "full"]
    thickness: Literal["thin", "medium", "thick"]
    corner: Literal["square", "rounded"]

    @model_validator(mode="after")
    def line_corner(self) -> Self:
        if self.kind == "line" and self.corner != "square":
            raise ValueError("lines must have square corners")
        return self


ElementV2 = Annotated[Union[TextElementV2, ImageElement, Decoration], Field(discriminator="type")]


class SlideV2(_StrictModel):
    id: Identifier
    layout: Literal["hero", "editorial", "quote"]
    background: SolidBackgroundV2
    elements: list[ElementV2] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def validate_elements(self) -> Self:
        ids = [element.id for element in self.elements]
        if len(ids) != len(set(ids)):
            raise ValueError("element IDs must be unique within each slide")
        if sum(isinstance(element, Decoration) for element in self.elements) > 4:
            raise ValueError("at most four decorations are allowed per slide")
        return self


class PostDocumentV2(_StrictModel):
    schema_version: Literal[2] = Field(alias="schemaVersion")
    post_type: Literal["single", "carousel"] = Field(alias="postType")
    palette: Palette
    slides: list[SlideV2] = Field(min_length=1, max_length=20)

    @field_validator("schema_version", mode="before")
    @classmethod
    def strict_version(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("schema version must be an integer")
        return value

    @model_validator(mode="after")
    def validate_structure(self) -> Self:
        if self.post_type == "single" and len(self.slides) != 1:
            raise ValueError("single posts must contain exactly one slide")
        ids = [slide.id for slide in self.slides]
        if len(ids) != len(set(ids)):
            raise ValueError("slide IDs must be unique")
        return self


def validate_authorized_assets(document: PostDocumentV2, authorized_assets: AbstractSet[str]) -> None:
    if any(isinstance(element, ImageElement) and element.asset_id not in authorized_assets
           for slide in document.slides for element in slide.elements):
        raise ValueError("image asset is not authorized")


def promote_v1(document: PostDocumentV1) -> PostDocumentV2:
    # Round-trip validates the base and resolves defaults without mutating the original.
    base = PostDocumentV1.model_validate_json(document.model_dump_json(by_alias=True))
    data = base.model_dump(mode="json", by_alias=True)
    text_color = next((element.style.color for slide in base.slides for element in slide.elements
                       if isinstance(element, TextElement)), "#000000")
    data["schemaVersion"] = 2
    data["palette"] = {"background": base.slides[0].background.color, "text": text_color, "accent": text_color}
    for slide in data["slides"]:
        slide["background"]["color"] = {"hex": slide["background"]["color"]}
        for element in slide["elements"]:
            if element["type"] == "text":
                element["style"]["color"] = {"hex": element["style"]["color"]}
    return PostDocumentV2.model_validate(data)

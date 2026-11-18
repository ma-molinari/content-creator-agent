"""Provisional, versioned contract for structured Instagram posts."""

from __future__ import annotations

import re
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from typing_extensions import Self


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, populate_by_name=False)


Identifier = Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$")]
Color = Annotated[str, Field(pattern=r"^#[0-9a-fA-F]{6}$")]


class SolidBackground(_StrictModel):
    type: Literal["solid"]
    color: Color


class TextStyle(_StrictModel):
    color: Color
    size: Literal["small", "medium", "large"]
    font: Literal["plus_jakarta_sans", "inter"] = "plus_jakarta_sans"
    weight: Literal["regular", "medium", "bold"] = "regular"
    alignment: Literal["left", "center", "right"] = "left"


class TextElement(_StrictModel):
    id: Identifier
    type: Literal["text"]
    role: Literal["heading", "body", "caption", "cta"]
    content: str = Field(min_length=1, max_length=2000)
    style: TextStyle

    @field_validator("content")
    @classmethod
    def plain_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text content must not be blank")
        if re.search(r"<\s*/?\s*[a-zA-Z!][^>]*>|(?:https?://|www\.)", value, re.IGNORECASE):
            raise ValueError("text content must not contain HTML or URLs")
        return value


class ImageElement(_StrictModel):
    id: Identifier
    type: Literal["image"]
    asset_id: Identifier = Field(alias="assetId")
    fit: Literal["cover", "contain"]


Element = Annotated[Union[TextElement, ImageElement], Field(discriminator="type")]


class Slide(_StrictModel):
    id: Identifier
    layout: Literal["hero", "editorial", "quote"]
    background: SolidBackground
    elements: list[Element] = Field(min_length=1, max_length=12)


class PostDocumentV1(_StrictModel):
    schema_version: Literal[1] = Field(alias="schemaVersion")
    post_type: Literal["single", "carousel"] = Field(alias="postType")
    slides: list[Slide] = Field(min_length=1, max_length=20)

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
        slide_ids = [slide.id for slide in self.slides]
        if len(slide_ids) != len(set(slide_ids)):
            raise ValueError("slide IDs must be unique")
        for slide in self.slides:
            element_ids = [element.id for element in slide.elements]
            if len(element_ids) != len(set(element_ids)):
                raise ValueError("element IDs must be unique within each slide")
        return self

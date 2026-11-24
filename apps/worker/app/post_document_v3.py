"""Version 3 contract: image backgrounds and durable image provenance."""

from __future__ import annotations

from typing import AbstractSet, Annotated, Literal, Union
from urllib.parse import urlsplit

from pydantic import Field, field_validator, model_validator
from typing_extensions import Self

from app.post_document import Identifier, PostDocumentV1, _StrictModel
from app.post_document_v2 import PostDocumentV2, SlideV2, SolidBackgroundV2, promote_v1


class FocalBox(_StrictModel):
    """Subject bounds as integer percentages of the uncropped source image."""
    left: int = Field(ge=0, le=100)
    top: int = Field(ge=0, le=100)
    right: int = Field(ge=0, le=100)
    bottom: int = Field(ge=0, le=100)

    @model_validator(mode="after")
    def nonempty(self) -> Self:
        if self.right <= self.left or self.bottom <= self.top:
            raise ValueError("invalid focal box")
        return self


class ImageBackgroundV3(_StrictModel):
    type: Literal["image"]
    asset_id: Identifier = Field(alias="assetId")
    focal_box: FocalBox | None = Field(default=None, alias="focalBox")


class ImageCreditV3(_StrictModel):
    title: str = Field(max_length=500)
    creator: str | None = Field(default=None, max_length=500)
    source_url: str = Field(alias="sourceUrl", min_length=1, max_length=2048)
    license: Literal["cc0"]
    license_url: str = Field(alias="licenseUrl", min_length=1, max_length=2048)

    @field_validator("source_url", "license_url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        try:
            parsed = urlsplit(value)
            if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.port not in (None, 443):
                raise ValueError("invalid attribution URL")
        except ValueError as exc:
            raise ValueError("invalid attribution URL") from exc
        return value


BackgroundV3 = Annotated[Union[SolidBackgroundV2, ImageBackgroundV3], Field(discriminator="type")]


class SlideV3(SlideV2):
    background: BackgroundV3


class PostDocumentV3(PostDocumentV2):
    schema_version: Literal[3] = Field(alias="schemaVersion")
    slides: list[SlideV3] = Field(min_length=1, max_length=20)
    credits: dict[Identifier, ImageCreditV3] = Field(default_factory=dict, max_length=240)

    @model_validator(mode="after")
    def validate_credits(self) -> Self:
        used = used_asset_ids(self)
        if not set(self.credits).issubset(used):
            raise ValueError("credit references an unused asset")
        return self


def used_asset_ids(document: PostDocumentV3) -> set[str]:
    ids = {element.asset_id for slide in document.slides for element in slide.elements if element.type == "image"}
    ids.update(slide.background.asset_id for slide in document.slides if isinstance(slide.background, ImageBackgroundV3))
    return ids


def validate_authorized_assets(document: PostDocumentV3, authorized: AbstractSet[str]) -> None:
    if not used_asset_ids(document).issubset(authorized):
        raise ValueError("image asset is not authorized")


def promote_to_v3(document: PostDocumentV1 | PostDocumentV2) -> PostDocumentV3:
    """Promote a validated prior version without mutating its snapshot."""
    base = promote_v1(document) if isinstance(document, PostDocumentV1) else document
    data = PostDocumentV2.model_validate_json(base.model_dump_json(by_alias=True)).model_dump(mode="json", by_alias=True)
    data["schemaVersion"] = 3
    data["credits"] = {}
    return PostDocumentV3.model_validate(data)

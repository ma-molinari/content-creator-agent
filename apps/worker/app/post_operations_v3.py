"""Apply existing typed operations while retaining V3 backgrounds and credits."""

from typing import AbstractSet

from app.post_document_v2 import PostDocumentV2
from app.post_document_v3 import PostDocumentV3, validate_authorized_assets
from app.post_operations_v2 import apply_operations_v2


def apply_operations_v3(document: PostDocumentV3, operations: list[dict], authorized_assets: AbstractSet[str]) -> PostDocumentV3:
    base = PostDocumentV3.model_validate_json(document.model_dump_json(by_alias=True))
    validate_authorized_assets(base, authorized_assets)
    data = base.model_dump(mode="json", by_alias=True)
    original_backgrounds = {slide["id"]: slide["background"] for slide in data["slides"]}
    data["schemaVersion"] = 2
    credits = data.pop("credits")
    for slide in data["slides"]:
        if slide["background"]["type"] == "image":
            slide["background"] = {"type": "solid", "color": {"token": "background"}}
    projected = PostDocumentV2.model_validate(data)
    changed = apply_operations_v2(projected, operations, authorized_assets).model_dump(mode="json", by_alias=True)
    changed_backgrounds = {op.get("slideId") for op in operations if op.get("op") == "set_background"}
    for slide in changed["slides"]:
        if slide["id"] not in changed_backgrounds:
            slide["background"] = original_backgrounds[slide["id"]]
    used = {item["assetId"] for slide in changed["slides"] for item in slide["elements"] if item["type"] == "image"}
    used.update(slide["background"]["assetId"] for slide in changed["slides"] if slide["background"]["type"] == "image")
    changed["schemaVersion"] = 3
    changed["credits"] = {key: value for key, value in credits.items() if key in used}
    result = PostDocumentV3.model_validate(changed)
    validate_authorized_assets(result, authorized_assets)
    return result

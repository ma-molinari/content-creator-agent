"""Apply an image-background replacement without mutating the base version."""

from typing import AbstractSet

from app.post_document_v3 import ImageCreditV3, PostDocumentV3, validate_authorized_assets


def set_stock_background(document: PostDocumentV3, *, slide_id: str, asset_id: str,
                         credit: ImageCreditV3, authorized_assets: AbstractSet[str]) -> PostDocumentV3:
    if asset_id not in authorized_assets:
        raise ValueError("image asset is not authorized")
    data = PostDocumentV3.model_validate_json(document.model_dump_json(by_alias=True)).model_dump(mode="json", by_alias=True)
    slide = next((item for item in data["slides"] if item["id"] == slide_id), None)
    if slide is None:
        raise ValueError("slide not found")
    slide["background"] = {"type": "image", "assetId": asset_id}
    data["credits"][asset_id] = credit.model_dump(mode="json", by_alias=True)
    # Remove unused provenance only from the new snapshot; the base remains intact.
    used = {element["assetId"] for item in data["slides"] for element in item["elements"] if element["type"] == "image"}
    used.update(item["background"]["assetId"] for item in data["slides"] if item["background"]["type"] == "image")
    data["credits"] = {key: value for key, value in data["credits"].items() if key in used}
    result = PostDocumentV3.model_validate(data)
    validate_authorized_assets(result, authorized_assets)
    return result

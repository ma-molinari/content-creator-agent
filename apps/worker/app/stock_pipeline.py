"""Plan and apply an Openverse image to a versioned structured document."""

from typing import AbstractSet, Literal

import httpx

from app.post_document_v3 import PostDocumentV3
from app.stock_edits import set_stock_background
from app.stock_planning import StockPlan, plan_stock_action
from app.stock_selection import select_stock_image


async def apply_stock_image(document: PostDocumentV3, *, request: str, mode: Literal["create", "edit"],
                            authorized_assets: AbstractSet[str], client: httpx.AsyncClient,
                            plan: StockPlan | None = None) -> tuple[PostDocumentV3, dict[str, bytes]]:
    plan = plan or await plan_stock_action(request=request, mode=mode, slide_count=len(document.slides))
    if plan.action == "none":
        return document, {}
    slide = document.slides[plan.slide_number - 1]
    excluded = frozenset(credit.source_url for credit in document.credits.values()) if mode == "edit" else frozenset()
    image = await select_stock_image(plan.query, client=client, exclude_sources=excluded)
    result = set_stock_background(document, slide_id=slide.id, asset_id=image.asset_id, credit=image.credit,
                                  authorized_assets=authorized_assets | {image.asset_id})
    return result, {image.asset_id: image.content}

"""Plan and apply an Openverse image to a versioned structured document."""

from typing import AbstractSet, Literal

import httpx

from app.post_document_v3 import PostDocumentV3
from app.openverse import ImageSearchError
from app.stock_edits import set_stock_background
from app.stock_planning import StockPlan, plan_stock_action
from app.stock_selection import NoSuitableImageError, select_stock_image


async def apply_stock_image(document: PostDocumentV3, *, request: str, mode: Literal["create", "edit"],
                            authorized_assets: AbstractSet[str], client: httpx.AsyncClient,
                            plan: StockPlan | None = None) -> tuple[PostDocumentV3, dict[str, bytes], bool]:
    plan = plan or await plan_stock_action(request=request, mode=mode, slide_count=len(document.slides))
    if plan.action == "none":
        return document, {}, False
    slide = document.slides[plan.slide_number - 1]
    excluded = frozenset(credit.source_url for credit in document.credits.values()) if mode == "edit" else frozenset()
    queries = list(dict.fromkeys(query.strip() for query in [plan.query, *plan.fallback_queries] if query.strip()))
    image = None
    for query in queries:
        try:
            image = await select_stock_image(query, client=client, exclude_sources=excluded, relevance_query=plan.query)
            break
        except NoSuitableImageError:
            continue
        except ImageSearchError:
            if mode == "create" and not plan.image_required:
                return document, {}, True
            raise
    if image is None:
        if mode == "create" and not plan.image_required:
            return document, {}, True
        if mode == "edit":
            raise NoSuitableImageError("Não foi encontrada uma fotografia adequada. Sua versão atual foi preservada; tente outro termo.")
        raise NoSuitableImageError("Não foi encontrada uma fotografia adequada. Tente outro termo ou solicite o post sem imagem.")
    result = set_stock_background(document, slide_id=slide.id, asset_id=image.asset_id, credit=image.credit,
                                  authorized_assets=authorized_assets | {image.asset_id}, focal_box=image.focal_box)
    return result, {image.asset_id: image.content}, False

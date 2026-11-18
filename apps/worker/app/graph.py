"""LangGraph V2 pipeline: structured contracts → JSON+HTML slides → render → S3 → callback."""

import inspect
from collections.abc import Callable
from typing import Any

from langgraph.graph import END, StateGraph

from app.job_progress import report_job_progress
from app.nodes.attachment_analyze import attachment_analyze
from app.nodes.build_generation_plan import build_generation_plan
from app.nodes.finalize import finalize
from app.nodes.generate_or_edit_slides import generate_or_edit_slides
from app.nodes.intent_detect import intent_detect, route_after_intent
from app.nodes.load_existing_slides import load_existing_slides, route_after_load_existing
from app.nodes.prepare_input import prepare_input
from app.nodes.profile_overview import profile_overview
from app.nodes.render_and_contrast import render_and_contrast
from app.nodes.security_validate import route_after_security, security_validate
from app.nodes.structured_pipeline import structured_pipeline
from app.nodes.upload_assets import upload_assets
from app.nodes.validate_attachment_usage import (
    route_after_attachment_usage,
    validate_attachment_usage,
)
from app.nodes.validate_design import route_after_validate_design, validate_design
from app.nodes.validate_slide_package import (
    route_after_slide_package,
    validate_slide_package,
)
from app.state import AgentState

_PROGRESS: dict[str, tuple[str, int]] = {
    "prepare_input": ("preparing_input", 5),
    "security_validate": ("validating_prompt", 10),
    "profile_overview": ("reading_profile", 15),
    "intent_detect": ("detecting_intent", 20),
    "load_existing_slides": ("loading_existing_slides", 25),
    "attachment_analyze": ("analyzing_attachments", 30),
    "build_generation_plan": ("planning_generation", 40),
    "generate_or_edit_slides": ("generating_slides", 55),
    "validate_slide_package": ("validating_output", 70),
    "validate_design": ("validating_design", 75),
    "validate_attachment_usage": ("validating_attachments", 80),
    "render_and_contrast": ("rendering_slides", 88),
    "upload_assets": ("uploading_assets", 95),
    "finalize": ("finalizing", 98),
}


def _with_progress(name: str, fn: Callable[..., Any]) -> Callable[[AgentState], Any]:
    async def wrapped(state: AgentState) -> dict[str, object]:
        stage, progress = _PROGRESS[name]
        await report_job_progress(state, stage=stage, progress=progress)
        result = fn(state)
        if inspect.isawaitable(result):
            result = await result
        return result

    return wrapped


def build_graph():
    builder = StateGraph(AgentState)
    builder.add_node("prepare_input", _with_progress("prepare_input", prepare_input))
    builder.add_node(
        "security_validate",
        _with_progress("security_validate", security_validate),
    )
    builder.add_node("profile_overview", _with_progress("profile_overview", profile_overview))
    builder.add_node("structured_pipeline", structured_pipeline)
    builder.add_node("intent_detect", _with_progress("intent_detect", intent_detect))
    builder.add_node(
        "load_existing_slides",
        _with_progress("load_existing_slides", load_existing_slides),
    )
    builder.add_node("attachment_analyze", _with_progress("attachment_analyze", attachment_analyze))
    builder.add_node(
        "build_generation_plan",
        _with_progress("build_generation_plan", build_generation_plan),
    )
    builder.add_node(
        "generate_or_edit_slides",
        _with_progress("generate_or_edit_slides", generate_or_edit_slides),
    )
    builder.add_node(
        "validate_slide_package",
        _with_progress("validate_slide_package", validate_slide_package),
    )
    builder.add_node("validate_design", _with_progress("validate_design", validate_design))
    builder.add_node(
        "validate_attachment_usage",
        _with_progress("validate_attachment_usage", validate_attachment_usage),
    )
    builder.add_node(
        "render_and_contrast",
        _with_progress("render_and_contrast", render_and_contrast),
    )
    builder.add_node("upload_assets", _with_progress("upload_assets", upload_assets))
    builder.add_node("finalize", _with_progress("finalize", finalize))

    builder.set_entry_point("prepare_input")
    builder.add_edge("prepare_input", "security_validate")
    builder.add_conditional_edges(
        "security_validate",
        route_after_security,
        {"ok": "profile_overview", "rejected": "finalize"},
    )
    builder.add_conditional_edges(
        "profile_overview",
        lambda state: "structured" if state.get("post_format") == "structured_v1" else "legacy",
        {"structured": "structured_pipeline", "legacy": "intent_detect"},
    )
    builder.add_edge("structured_pipeline", END)
    builder.add_conditional_edges(
        "intent_detect",
        route_after_intent,
        {
            "fail": "finalize",
            "edit": "load_existing_slides",
            "new": "attachment_analyze",
        },
    )
    builder.add_conditional_edges(
        "load_existing_slides",
        route_after_load_existing,
        {"continue": "attachment_analyze", "fail": "finalize"},
    )
    builder.add_edge("attachment_analyze", "build_generation_plan")
    builder.add_edge("build_generation_plan", "generate_or_edit_slides")
    builder.add_edge("generate_or_edit_slides", "validate_slide_package")
    builder.add_conditional_edges(
        "validate_slide_package",
        route_after_slide_package,
        {
            "continue": "validate_design",
            "retry": "generate_or_edit_slides",
            "fail": "finalize",
        },
    )
    builder.add_conditional_edges(
        "validate_design",
        route_after_validate_design,
        {
            "continue": "validate_attachment_usage",
            "retry": "generate_or_edit_slides",
            "fail": "finalize",
        },
    )
    builder.add_conditional_edges(
        "validate_attachment_usage",
        route_after_attachment_usage,
        {"continue": "render_and_contrast", "retry": "generate_or_edit_slides", "fail": "finalize"},
    )
    builder.add_edge("render_and_contrast", "upload_assets")
    builder.add_edge("upload_assets", "finalize")
    builder.add_edge("finalize", END)
    return builder.compile()


graph = build_graph()

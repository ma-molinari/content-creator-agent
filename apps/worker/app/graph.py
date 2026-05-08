"""LangGraph V2 pipeline: structured contracts → JSON+HTML slides → render → S3 → callback."""

from langgraph.graph import END, StateGraph

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


def build_graph():
    builder = StateGraph(AgentState)
    builder.add_node("prepare_input", prepare_input)
    builder.add_node("security_validate", security_validate)
    builder.add_node("profile_overview", profile_overview)
    builder.add_node("intent_detect", intent_detect)
    builder.add_node("load_existing_slides", load_existing_slides)
    builder.add_node("attachment_analyze", attachment_analyze)
    builder.add_node("build_generation_plan", build_generation_plan)
    builder.add_node("generate_or_edit_slides", generate_or_edit_slides)
    builder.add_node("validate_slide_package", validate_slide_package)
    builder.add_node("validate_design", validate_design)
    builder.add_node("validate_attachment_usage", validate_attachment_usage)
    builder.add_node("render_and_contrast", render_and_contrast)
    builder.add_node("upload_assets", upload_assets)
    builder.add_node("finalize", finalize)

    builder.set_entry_point("prepare_input")
    builder.add_edge("prepare_input", "security_validate")
    builder.add_conditional_edges(
        "security_validate",
        route_after_security,
        {"ok": "profile_overview", "rejected": "finalize"},
    )
    builder.add_edge("profile_overview", "intent_detect")
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
        {"continue": "validate_design", "retry": "generate_or_edit_slides", "fail": "finalize"},
    )
    builder.add_conditional_edges(
        "validate_design",
        route_after_validate_design,
        {"continue": "validate_attachment_usage", "retry": "generate_or_edit_slides", "fail": "finalize"},
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

"""LangGraph pipeline: profile → brief → slides → parse → design QA → render → S3 → callback."""

from langgraph.graph import END, StateGraph

from app.nodes.describe_references import describe_references
from app.nodes.detect_intent import detect_intent
from app.nodes.edit_slides import edit_slides
from app.nodes.finalize import finalize
from app.nodes.generate_slides import generate_slides
from app.nodes.load_profile import load_profile
from app.nodes.optimize_prompt import optimize_prompt
from app.nodes.design_validate import design_validate, route_after_design
from app.nodes.parse_validate import parse_validate, route_after_parse
from app.nodes.prompt_security_validate import prompt_security_validate, route_after_prompt_security
from app.nodes.render_to_jpeg import render_to_jpeg
from app.nodes.upload_assets import upload_assets
from app.nodes.validate_brief import route_after_validate_brief, validate_brief
from app.state import AgentState


def build_graph():
    builder = StateGraph(AgentState)
    builder.add_node("load_profile", load_profile)
    builder.add_node("prompt_security_validate", prompt_security_validate)
    builder.add_node("describe_references", describe_references)
    builder.add_node("optimize_prompt", optimize_prompt)
    builder.add_node("validate_brief", validate_brief)
    builder.add_node("detect_intent", detect_intent)
    builder.add_node("generate_slides", generate_slides)
    builder.add_node("edit_slides", edit_slides)
    builder.add_node("parse_validate", parse_validate)
    builder.add_node("design_validate", design_validate)
    builder.add_node("render_to_jpeg", render_to_jpeg)
    builder.add_node("upload_assets", upload_assets)
    builder.add_node("finalize", finalize)

    builder.set_entry_point("load_profile")
    builder.add_edge("load_profile", "prompt_security_validate")
    builder.add_conditional_edges(
        "prompt_security_validate",
        route_after_prompt_security,
        {"ok": "describe_references", "rejected": "finalize"},
    )
    builder.add_edge("describe_references", "detect_intent")

    def route_after_detect_intent(state: AgentState) -> str:
        if state.get("refinement_context_unavailable"):
            return "fail"
        if state.get("is_refinement"):
            return "edit"
        return "new"

    builder.add_conditional_edges(
        "detect_intent",
        route_after_detect_intent,
        {
            "fail": "finalize",
            "edit": "edit_slides",
            "new": "optimize_prompt",
        },
    )
    builder.add_edge("optimize_prompt", "validate_brief")
    builder.add_conditional_edges(
        "validate_brief",
        route_after_validate_brief,
        {"ok": "generate_slides", "retry": "optimize_prompt", "fail": "finalize"},
    )
    builder.add_edge("generate_slides", "parse_validate")
    builder.add_edge("edit_slides", "parse_validate")
    builder.add_conditional_edges(
        "parse_validate",
        route_after_parse,
        {
            "retry_edit": "edit_slides",
            "retry_new": "generate_slides",
            "continue": "design_validate",
            "fail": "finalize",
        },
    )
    builder.add_conditional_edges(
        "design_validate",
        route_after_design,
        {
            "retry_edit": "edit_slides",
            "retry_new": "generate_slides",
            "continue": "render_to_jpeg",
            "fail": "finalize",
        },
    )
    builder.add_edge("render_to_jpeg", "upload_assets")
    builder.add_edge("upload_assets", "finalize")
    builder.add_edge("finalize", END)
    return builder.compile()


graph = build_graph()

"""LangGraph pipeline: profile → brief → slides → parse → render → S3 → callback."""

from langgraph.graph import END, StateGraph

from app.nodes.describe_references import describe_references
from app.nodes.finalize import finalize
from app.nodes.generate_slides import generate_slides
from app.nodes.load_profile import load_profile
from app.nodes.optimize_prompt import optimize_prompt
from app.nodes.parse_validate import parse_validate, route_after_parse
from app.nodes.render_to_jpeg import render_to_jpeg
from app.nodes.upload_assets import upload_assets
from app.state import AgentState


def build_graph():
    builder = StateGraph(AgentState)
    builder.add_node("load_profile", load_profile)
    builder.add_node("describe_references", describe_references)
    builder.add_node("optimize_prompt", optimize_prompt)
    builder.add_node("generate_slides", generate_slides)
    builder.add_node("parse_validate", parse_validate)
    builder.add_node("render_to_jpeg", render_to_jpeg)
    builder.add_node("upload_assets", upload_assets)
    builder.add_node("finalize", finalize)

    builder.set_entry_point("load_profile")
    builder.add_edge("load_profile", "describe_references")
    builder.add_edge("describe_references", "optimize_prompt")
    builder.add_edge("optimize_prompt", "generate_slides")
    builder.add_edge("generate_slides", "parse_validate")
    builder.add_conditional_edges(
        "parse_validate",
        route_after_parse,
        {"retry": "generate_slides", "continue": "render_to_jpeg"},
    )
    builder.add_edge("render_to_jpeg", "upload_assets")
    builder.add_edge("upload_assets", "finalize")
    builder.add_edge("finalize", END)
    return builder.compile()


graph = build_graph()

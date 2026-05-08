"""Static checks on LangGraph wiring (no runtime import of app.graph — Python 3.9 compat)."""

from __future__ import annotations

import ast
from pathlib import Path


def _load_graph_ast() -> ast.Module:
    root = Path(__file__).resolve().parents[1]
    src = (root / "app" / "graph.py").read_text(encoding="utf-8")
    return ast.parse(src)


def _collect_edges(tree: ast.Module) -> tuple[list[tuple[str, str]], list[tuple[str, dict[str, str]]]]:
    edges: list[tuple[str, str]] = []
    conditionals: list[tuple[str, dict[str, str]]] = []

    class Visitor(ast.NodeVisitor):
        def visit_Call(self, node: ast.Call) -> None:
            func = node.func
            if not isinstance(func, ast.Attribute):
                self.generic_visit(node)
                return
            if func.attr == "add_edge" and len(node.args) >= 2:
                a0, a1 = node.args[0], node.args[1]
                if isinstance(a0, ast.Constant) and isinstance(a1, ast.Constant):
                    if isinstance(a0.value, str) and isinstance(a1.value, str):
                        edges.append((a0.value, a1.value))
            elif func.attr == "add_conditional_edges" and len(node.args) >= 3:
                src_node, mapping = node.args[0], node.args[2]
                if not isinstance(src_node, ast.Constant) or not isinstance(src_node.value, str):
                    self.generic_visit(node)
                    return
                if not isinstance(mapping, ast.Dict):
                    self.generic_visit(node)
                    return
                routes: dict[str, str] = {}
                for k, v in zip(mapping.keys, mapping.values):
                    if (
                        isinstance(k, ast.Constant)
                        and isinstance(k.value, str)
                        and isinstance(v, ast.Constant)
                        and isinstance(v.value, str)
                    ):
                        routes[k.value] = v.value
                conditionals.append((src_node.value, routes))
            self.generic_visit(node)

    Visitor().visit(tree)
    return edges, conditionals


def test_graph_isr_ordering() -> None:
    tree = _load_graph_ast()
    edges, conditionals = _collect_edges(tree)

    assert ("prepare_input", "security_validate") in edges
    assert ("profile_overview", "intent_detect") in edges
    assert ("attachment_analyze", "build_generation_plan") in edges
    assert ("build_generation_plan", "generate_or_edit_slides") in edges
    assert ("generate_or_edit_slides", "validate_slide_package") in edges
    assert ("render_and_contrast", "upload_assets") in edges

    security = next(m for loc, m in conditionals if loc == "security_validate")
    assert security["ok"] == "profile_overview"
    assert security["rejected"] == "finalize"

    detect = next(m for loc, m in conditionals if loc == "intent_detect")
    assert detect["fail"] == "finalize"
    assert detect["edit"] == "load_existing_slides"
    assert detect["new"] == "attachment_analyze"

    pkg = next(m for loc, m in conditionals if loc == "validate_slide_package")
    assert pkg["continue"] == "validate_design"
    assert pkg["retry"] == "generate_or_edit_slides"
    assert pkg["fail"] == "finalize"

    design = next(m for loc, m in conditionals if loc == "validate_design")
    assert design["continue"] == "validate_attachment_usage"
    assert design["retry"] == "generate_or_edit_slides"

    attach = next(m for loc, m in conditionals if loc == "validate_attachment_usage")
    assert attach["continue"] == "render_and_contrast"
    assert attach["retry"] == "generate_or_edit_slides"

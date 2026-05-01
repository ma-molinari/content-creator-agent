"""Tests for slide_design_checks and design_validate node."""

from __future__ import annotations

import unittest

from app.nodes.design_validate import design_validate, route_after_design
from app.slide_design_checks import check_remote_assets, collect_design_violations
from app.state import AgentState


def _minimal_valid_slide(variant: str = "inter") -> str:
    if variant == "inter":
        gf = "@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap');"
        ff = "'Inter', system-ui, sans-serif"
    else:
        gf = "@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap');"
        ff = "'Roboto', sans-serif"
    return f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8"/><style>
{gf}
body {{ margin:0;padding:0;width:1080px;height:1350px;overflow:hidden;
font-family:{ff};font-weight:500;}}
</style></head><body><main><p>Conteúdo de teste.</p></main></body></html>"""


class TestSlideDesignChecks(unittest.TestCase):
    def test_valid_inter_slide_passes(self) -> None:
        self.assertEqual(collect_design_violations(_minimal_valid_slide("inter")), [])

    def test_valid_roboto_slide_passes(self) -> None:
        """Alternate GF family loaded and used passes without Inter."""
        self.assertEqual(collect_design_violations(_minimal_valid_slide("roboto")), [])

    def test_script_rejected(self) -> None:
        html = _minimal_valid_slide().replace("</body>", "<script>x</script></body>")
        msgs = collect_design_violations(html)
        self.assertTrue(any("script" in m.lower() for m in msgs))

    def test_remote_image_rejected(self) -> None:
        html = _minimal_valid_slide().replace(
            "<main>",
            '<main><img src="https://example.com/x.png" alt=""/>',
        )
        msgs = collect_design_violations(html)
        self.assertTrue(any("remota" in m.lower() or "proibida" in m.lower() for m in msgs))

    def test_multiple_remote_assets_all_reported(self) -> None:
        """All forbidden remote URLs are reported in one pass (no early return)."""
        html = (
            _minimal_valid_slide()
            .replace("<main>", '<main><img src="https://example.com/x.png" alt=""/>')
            .replace(
                "body { margin:0;padding:0;width:1080px;height:1350px;overflow:hidden;",
                "body { margin:0;padding:0;width:1080px;height:1350px;overflow:hidden;"
                "background-image:url(https://cdn.example.com/bg.jpg);",
            )
        )
        msgs = check_remote_assets(html)
        self.assertGreaterEqual(len(msgs), 2)

    def test_missing_inter_rejected(self) -> None:
        html = _minimal_valid_slide().replace("'Inter', system-ui", "system-ui")
        msgs = collect_design_violations(html)
        self.assertTrue(any("tipografia" in m.lower() for m in msgs))

    def test_missing_viewport_rejected(self) -> None:
        html = _minimal_valid_slide().replace("1080px", "100vw")
        msgs = collect_design_violations(html)
        self.assertTrue(any("1080" in m or "viewport" in m.lower() for m in msgs))

    def test_external_stylesheet_rejected(self) -> None:
        html = _minimal_valid_slide().replace(
            "<head>",
            '<head><link rel="stylesheet" href="https://cdn.example.com/a.css"/>',
        )
        msgs = collect_design_violations(html)
        self.assertTrue(any("link" in m.lower() or "google fonts" in m.lower() for m in msgs))


class TestDesignValidateNode(unittest.TestCase):
    def test_continue_when_clean(self) -> None:
        slide = {"filename": "slide_01.html", "html": _minimal_valid_slide()}
        base: AgentState = {
            "job_id": "j1",
            "user_id": "u",
            "chat_id": "c",
            "raw_message": "",
            "audit_text": "",
            "brand_text": "",
            "reprompt_context": "",
            "profile_text": "",
            "optimized_brief": "",
            "raw_slide_output": "",
            "slides_html": [slide],
            "rendered_slides": [],
            "artifacts": [],
            "retry_count": 0,
            "errors": [],
            "design_retry_count": 2,
        }
        out = design_validate(base)
        self.assertEqual(out.get("design_retry_count"), 0)
        self.assertEqual(route_after_design({**base, **out}), "continue")

    def test_retry_on_failure(self) -> None:
        bad_html = _minimal_valid_slide().replace("1080px", "100vw")
        slide = {"filename": "slide_01.html", "html": bad_html}
        base: AgentState = {
            "job_id": "j1",
            "user_id": "u",
            "chat_id": "c",
            "raw_message": "",
            "audit_text": "",
            "brand_text": "",
            "reprompt_context": "",
            "profile_text": "",
            "optimized_brief": "",
            "raw_slide_output": "",
            "slides_html": [slide],
            "rendered_slides": [],
            "artifacts": [],
            "retry_count": 0,
            "errors": [],
        }
        out = design_validate(base)
        self.assertEqual(out.get("slides_html"), [])
        self.assertEqual(out.get("design_retry_count"), 1)
        self.assertTrue(any("design_validate:" in (e or "") for e in (out.get("errors") or [])))
        routed = route_after_design({**base, **out})
        self.assertEqual(routed, "retry")

    def test_route_fail_when_retries_exhausted(self) -> None:
        bad_html = _minimal_valid_slide().replace("1080px", "100vw")
        slide = {"filename": "slide_01.html", "html": bad_html}
        base: AgentState = {
            "job_id": "j1",
            "user_id": "u",
            "chat_id": "c",
            "raw_message": "",
            "audit_text": "",
            "brand_text": "",
            "reprompt_context": "",
            "profile_text": "",
            "optimized_brief": "",
            "raw_slide_output": "",
            "slides_html": [slide],
            "rendered_slides": [],
            "artifacts": [],
            "retry_count": 0,
            "errors": [],
            "design_retry_count": 2,
        }
        out = design_validate(base)
        self.assertEqual(out.get("design_retry_count"), 3)
        self.assertEqual(route_after_design({**base, **out}), "fail")


if __name__ == "__main__":
    unittest.main()

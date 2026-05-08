"""Tests for slide_design_checks and design_validate node."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from app.config import get_settings
from app.nodes.design_validate import design_validate, route_after_design
from app.slide_design_checks import (
    check_reference_colors,
    check_remote_assets,
    collect_design_violations,
)
from app.state import AgentState

_PJS_GF_URL = "https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:ital,wght@0,200..800;1,200..800&display=swap"

_SETTINGS_ENV = {
    "OPENAI_API_KEY": "test-openai-key",
    "AWS_REGION": "us-east-1",
    "AWS_ACCESS_KEY_ID": "test-access",
    "AWS_SECRET_ACCESS_KEY": "test-secret",
    "AWS_S3_BUCKET": "post-mind-test",
    "GO_API_URL": "http://api.test",
    "WORKER_API_KEY": "test-worker-key",
}


def _minimal_valid_slide(variant: str = "default") -> str:
    if variant == "default":
        gf = f"@import url('{_PJS_GF_URL}');"
        ff = "'Plus Jakarta Sans', system-ui, sans-serif"
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
    def test_valid_plus_jakarta_sans_slide_passes(self) -> None:
        self.assertEqual(collect_design_violations(_minimal_valid_slide("default")), [])

    def test_valid_roboto_slide_passes(self) -> None:
        """Alternate GF family loaded and used passes without Plus Jakarta Sans."""
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

    def test_configured_s3_attachment_url_allowed(self) -> None:
        get_settings.cache_clear()
        with patch.dict(os.environ, _SETTINGS_ENV, clear=False):
            html = _minimal_valid_slide().replace(
                "<main>",
                '<main><img src="https://post-mind-test.s3.us-east-1.amazonaws.com/users/u/chat-attachments/a.jpg?X-Amz-Signature=abc" alt=""/>',
            )
            self.assertEqual(check_remote_assets(html), [])
        get_settings.cache_clear()

    def test_unconfigured_s3_bucket_rejected(self) -> None:
        get_settings.cache_clear()
        with patch.dict(os.environ, _SETTINGS_ENV, clear=False):
            html = _minimal_valid_slide().replace(
                "<main>",
                '<main><img src="https://other-bucket.s3.us-east-1.amazonaws.com/users/u/chat-attachments/a.jpg" alt=""/>',
            )
            msgs = check_remote_assets(html)
            self.assertTrue(any("proibida" in m.lower() for m in msgs))
        get_settings.cache_clear()

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

    def test_missing_default_font_rejected(self) -> None:
        """Slide without Plus Jakarta Sans and without any other GF family triggers tipografia error."""
        html = _minimal_valid_slide().replace("'Plus Jakarta Sans', system-ui", "system-ui")
        msgs = collect_design_violations(html)
        self.assertTrue(any("tipografia" in m.lower() for m in msgs))

    def test_inter_without_pjs_rejected(self) -> None:
        """Inter import alone (legacy font) is not sufficient — must use Plus Jakarta Sans or explicit alternate."""
        html = (
            "<!DOCTYPE html><html lang='pt-BR'><head><meta charset='utf-8'/><style>"
            "@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap');"
            "body{margin:0;padding:0;width:1080px;height:1350px;overflow:hidden;"
            "font-family:'Inter',system-ui,sans-serif;font-weight:500;}"
            "</style></head><body><main><p>Conteúdo.</p></main></body></html>"
        )
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


class TestCheckReferenceColors(unittest.TestCase):
    _prescription = "Paleta: #1a1a2e (fundo escuro), #e94560 (accent), #0f3460 (mid-dark)"

    def _slide_with_colors(self, *hex_values: str) -> str:
        color_css = " ".join(f"color:{h};" for h in hex_values)
        return (
            f"<!DOCTYPE html><html><head><style>"
            f"@import url('{_PJS_GF_URL}');"
            f"body{{margin:0;padding:0;width:1080px;height:1350px;overflow:hidden;"
            f"font-family:'Plus Jakarta Sans',sans-serif;{color_css}}}"
            f"</style></head><body><main><p>ok</p></main></body></html>"
        )

    def test_matching_reference_color_passes(self) -> None:
        """Slide containing a hex close to one in the prescription emits no warning."""
        html = self._slide_with_colors("#1a1a2e", "#ffffff")
        self.assertEqual(check_reference_colors(html, self._prescription), [])

    def test_approximate_color_match_passes(self) -> None:
        """Color within ±15 per channel is accepted (#1a1a2e → #201f35: diffs 6,5,7)."""
        html = self._slide_with_colors("#201f35", "#ffffff")
        self.assertEqual(check_reference_colors(html, self._prescription), [])

    def test_no_reference_colors_warns(self) -> None:
        """Slide with completely unrelated palette triggers the warning."""
        html = self._slide_with_colors("#aabbcc", "#ddeeff")
        msgs = check_reference_colors(html, self._prescription)
        self.assertTrue(any("referências visuais" in m.lower() for m in msgs))

    def test_empty_prescription_skipped(self) -> None:
        """Empty prescription blob produces no violations."""
        html = self._slide_with_colors("#aabbcc")
        self.assertEqual(check_reference_colors(html, ""), [])

    def test_few_hex_in_prescription_skipped(self) -> None:
        """Fewer than 3 hex values in prescription — check is skipped."""
        html = self._slide_with_colors("#aabbcc")
        self.assertEqual(check_reference_colors(html, "apenas #ff0000 aqui"), [])


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
        self.assertEqual(routed, "retry_new")

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

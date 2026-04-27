"""Unit tests for split_optimize_response."""

import unittest

from app.parse_optimize_output import split_optimize_response


class TestSplitOptimizeResponse(unittest.TestCase):
    def test_both_tags_full_brief(self) -> None:
        raw = """
<brief_para_gerador>
## Objetivo
Vender o produto.
</brief_para_gerador>
<mensagem_usuario>
Resumo do ângulo.

## Perguntas em aberto
1. Público-alvo?
</mensagem_usuario>
""".strip()
        brief, msg = split_optimize_response(raw)
        self.assertIn("## Objetivo", brief)
        self.assertIn("Vender o produto", brief)
        self.assertIsNotNone(msg)
        assert msg is not None
        self.assertIn("Resumo", msg)
        self.assertIn("Perguntas", msg)

    def test_only_brief_tag(self) -> None:
        raw = "<brief_para_gerador>\nSó o brief.\n</brief_para_gerador>"
        brief, msg = split_optimize_response(raw)
        self.assertEqual(brief, "Só o brief.")
        self.assertIsNone(msg)

    def test_only_message_tag_treated_as_legacy_brief(self) -> None:
        """No brief tag: entire output (minus optional outer fence) becomes optimized_brief."""
        raw = "<mensagem_usuario>\nApenas chat.\n</mensagem_usuario>"
        brief, msg = split_optimize_response(raw)
        self.assertIn("mensagem_usuario", brief)
        self.assertIn("Apenas chat", brief)
        self.assertIsNotNone(msg)
        self.assertIn("Apenas chat", msg or "")

    def test_no_tags_legacy_full_string(self) -> None:
        raw = "## Objetivo\n\nSem XML."
        brief, msg = split_optimize_response(raw)
        self.assertEqual(brief, raw)
        self.assertIsNone(msg)

    def test_whitespace_stripped(self) -> None:
        raw = "  <brief_para_gerador>  \nX\n  </brief_para_gerador>  \n  "
        brief, _ = split_optimize_response(raw)
        self.assertEqual(brief, "X")

    def test_empty_brief_tag_falls_back_to_raw(self) -> None:
        raw = (
            "<brief_para_gerador>   \n  </brief_para_gerador>\n"
            "<mensagem_usuario>Olá</mensagem_usuario>"
        )
        brief, msg = split_optimize_response(raw)
        self.assertIn("brief_para_gerador", brief)
        self.assertEqual(msg, "Olá")

    def test_outer_markdown_fence_stripped(self) -> None:
        raw = """```markdown
<brief_para_gerador>
## T
</brief_para_gerador>
<mensagem_usuario>
Hi
</mensagem_usuario>
```"""
        brief, msg = split_optimize_response(raw)
        self.assertIn("## T", brief)
        self.assertEqual(msg, "Hi")

    def test_inner_fence_on_user_message(self) -> None:
        raw = """<brief_para_gerador>## A</brief_para_gerador>
<mensagem_usuario>
```text
Ola
```
</mensagem_usuario>"""
        _, msg = split_optimize_response(raw)
        self.assertEqual(msg, "Ola")

    def test_empty_message_tag(self) -> None:
        raw = (
            "<brief_para_gerador>## A</brief_para_gerador>"
            "<mensagem_usuario></mensagem_usuario>"
        )
        _, msg = split_optimize_response(raw)
        self.assertIsNone(msg)

    def test_case_insensitive_tags(self) -> None:
        raw = (
            "<BRIEF_PARA_GERADOR>low</BRIEF_PARA_GERADOR>"
            "<MENSAGEM_USUARIO>u</MENSAGEM_USUARIO>"
        )
        brief, msg = split_optimize_response(raw)
        self.assertEqual(brief, "low")
        self.assertEqual(msg, "u")

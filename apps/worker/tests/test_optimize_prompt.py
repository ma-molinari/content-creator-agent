"""optimize_prompt node: LLM wiring and output mapping (LLM mocked)."""

from __future__ import annotations

from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import AIMessage

from app.nodes.optimize_prompt import optimize_prompt


def _state(**kwargs: object) -> dict:
    base: dict = {
        "job_id": "j1",
        "user_id": "u",
        "chat_id": "c",
        "raw_message": "Post sobre produto saudável.",
        "audit_text": "",
        "brand_text": "",
        "profile_text": "## AUDIT\na\n\n## BRAND\nb",
        "optimized_brief": "",
        "raw_slide_output": "",
        "slides_html": [],
        "rendered_slides": [],
        "artifacts": [],
        "retry_count": 0,
        "errors": [],
    }
    base.update(kwargs)
    return base


class TestOptimizePrompt(IsolatedAsyncioTestCase):
    async def test_maps_split_output_to_state(self) -> None:
        settings = MagicMock()
        settings.openai_api_key = "k"
        settings.openai_chat_model = "gpt-test"

        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=AIMessage(content="model raw"))

        with (
            patch("app.nodes.optimize_prompt.get_settings", return_value=settings),
            patch("app.nodes.optimize_prompt.read_prompt_md", return_value="SYS"),
            patch("app.nodes.optimize_prompt.ChatOpenAI", return_value=mock_llm),
            patch(
                "app.nodes.optimize_prompt.split_optimize_response",
                return_value=("Brief corpo", "Mensagem ao utilizador"),
            ),
        ):
            out = await optimize_prompt(_state())  # type: ignore[arg-type]

        self.assertEqual(out.get("optimized_brief"), "Brief corpo")
        self.assertEqual(out.get("assistant_text"), "Mensagem ao utilizador")
        mock_llm.ainvoke.assert_awaited_once()
        call_msgs = mock_llm.ainvoke.await_args[0][0]
        human = call_msgs[1].content
        self.assertIn("<perfil_usuario>", human)
        self.assertIn("</perfil_usuario>", human)
        self.assertIn("<pedido_usuario>", human)
        self.assertIn("</pedido_usuario>", human)
        self.assertIn("Post sobre produto saudável.", human)


if __name__ == "__main__":
    import unittest

    unittest.main()

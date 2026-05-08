"""Unit tests for slide count inference and token budget helpers."""

import unittest
from types import SimpleNamespace

from app.generate_slides_tokens import compute_max_output_tokens
from app.nodes.validate_slide_package import route_after_slide_package, validate_slide_package
from app.slide_count_inference import infer_requested_slide_count


def _html_slide(body: str = "x" * 100) -> str:
    return f"<!DOCTYPE html><html><head><title>t</title></head><body><p>{body}</p></body></html>"


def _slide_package(n: int) -> dict:
    return {
        "slides": [
            {"filename": f"slide_{i:02d}.html", "slide_number": i, "html": _html_slide()}
            for i in range(1, n + 1)
        ]
    }


class TestInferRequestedSlideCount(unittest.TestCase):
    def test_carrossel_de_n(self) -> None:
        self.assertEqual(infer_requested_slide_count("quero um carrossel de 6 slides"), 6)
        self.assertEqual(infer_requested_slide_count("Carrossel de 10 para o feed"), 10)

    def test_carrousel_with_number_word(self) -> None:
        self.assertEqual(
            infer_requested_slide_count("crie um carrousel de dois slides sobre nostalgia"),
            2,
        )
        self.assertEqual(infer_requested_slide_count("make a carousel with two slides"), 2)

    def test_n_slides(self) -> None:
        self.assertEqual(infer_requested_slide_count("faz 5 slides sobre marketing"), 5)
        self.assertEqual(infer_requested_slide_count("make 6 slides about AI"), 6)

    def test_none_when_no_number(self) -> None:
        self.assertIsNone(infer_requested_slide_count("quero um carrossel legal"))

    def test_none_when_conflicting(self) -> None:
        self.assertIsNone(
            infer_requested_slide_count("6 slides no primeiro post e 10 slides no segundo")
        )


class TestComputeMaxOutputTokens(unittest.TestCase):
    def test_formula_and_cap(self) -> None:
        s = SimpleNamespace(
            generate_slides_max_tokens=None,
            generate_slides_tokens_base=1500,
            generate_slides_tokens_per_slide=1200,
            generate_slides_max_tokens_cap=5000,
        )
        # 2 slides: 1500 + 2400 = 3900
        self.assertEqual(compute_max_output_tokens(2, s), 3900)  # type: ignore[arg-type]
        # cap
        out = compute_max_output_tokens(10, s)  # type: ignore[arg-type]
        self.assertEqual(out, 5000)

    def test_override(self) -> None:
        s = SimpleNamespace(
            generate_slides_max_tokens=4000,
            generate_slides_tokens_base=1,
            generate_slides_tokens_per_slide=1,
            generate_slides_max_tokens_cap=20000,
        )
        self.assertEqual(compute_max_output_tokens(99, s), 4000)  # type: ignore[arg-type]


class TestValidateSlidePackageCount(unittest.TestCase):
    def test_accepts_when_count_matches(self) -> None:
        state = {
            "job_id": "j1",
            "slide_package": _slide_package(3),
            "errors": [],
            "retry_count": 0,
            "requested_slide_count": 3,
        }
        out = validate_slide_package(state)  # type: ignore[arg-type]
        self.assertEqual(len(out["slides_html"]), 3)
        self.assertEqual(route_after_slide_package({**state, **out}), "continue")

    def test_retries_when_count_mismatch(self) -> None:
        state = {
            "job_id": "j1",
            "slide_package": _slide_package(2),
            "errors": [],
            "retry_count": 0,
            "requested_slide_count": 3,
        }
        out = validate_slide_package(state)  # type: ignore[arg-type]
        self.assertEqual(out.get("slides_html"), [])
        err_joined = " ".join(out.get("errors") or [])
        self.assertIn("esperados 3 slides", err_joined)
        self.assertEqual(out.get("retry_count"), 1)
        st2 = {**state, **out}
        self.assertEqual(route_after_slide_package(st2), "retry")

    def test_exhausted_retries_routes_to_fail(self) -> None:
        state = {
            "job_id": "j1",
            "slide_package": _slide_package(1),
            "errors": ["prev"],
            "retry_count": 3,
            "requested_slide_count": 2,
        }
        out = validate_slide_package(state)  # type: ignore[arg-type]
        self.assertEqual(out.get("slides_html"), [])
        st2 = {**state, **out}
        self.assertEqual(route_after_slide_package(st2), "fail")


if __name__ == "__main__":
    unittest.main()

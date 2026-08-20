"""Unit tests for OpenRouter-backed AI filtering behavior."""

# pyright: reportMissingImports=false

from __future__ import annotations

import os
import sys
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError

# Ensure backend modules are importable when running from repository root.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import filter.ai_filter as ai_filter_module
from utils.open_router import JudgeResult, OpenRouterJudgeAgent


class OpenRouterJudgeAgentTests(unittest.TestCase):
    def test_judge_returns_false_when_api_key_missing(self) -> None:
        agent = OpenRouterJudgeAgent(api_key=None)

        result = agent.judge("Any article")

        self.assertFalse(result.is_ai_related)
        self.assertEqual(result.confidence, 0.0)
        self.assertIn("missing", result.reason.lower())

    def test_judge_parses_valid_json_and_clamps_confidence(self) -> None:
        agent = OpenRouterJudgeAgent(api_key="sk-test")
        mock_response = {
            "choices": [
                {
                    "message": {
                        "content": '{"label": true, "confidence": 1.4, "reason": "Mainly about AI."}'
                    }
                }
            ]
        }

        with patch.object(agent, "_post_chat_completion", return_value=mock_response):
            result = agent.judge("AI startup launches a new model")

        self.assertTrue(result.is_ai_related)
        self.assertEqual(result.confidence, 1.0)
        self.assertEqual(result.reason, "Mainly about AI.")

    def test_judge_returns_false_on_non_json_content(self) -> None:
        agent = OpenRouterJudgeAgent(api_key="sk-test")
        mock_response = {
            "choices": [
                {
                    "message": {
                        "content": "This article looks AI-related but I cannot output JSON now."
                    }
                }
            ]
        }

        with patch.object(agent, "_post_chat_completion", return_value=mock_response):
            result = agent.judge("Some text")

        self.assertFalse(result.is_ai_related)
        self.assertEqual(result.confidence, 0.0)

    def test_judge_retries_on_5xx_then_succeeds(self) -> None:
        agent = OpenRouterJudgeAgent(api_key="sk-test", max_retries=1, retry_backoff_seconds=0)
        first_error = HTTPError(
            url="https://openrouter.ai/api/v1/chat/completions",
            code=500,
            msg="server error",
            hdrs=None,
            fp=BytesIO(b'{"error":{"message":"temporary error"}}'),
        )
        success_response = {
            "choices": [{"message": {"content": '{"label": true, "confidence": 0.8, "reason": "AI-focused."}'}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 12, "total_tokens": 112},
        }

        with patch.object(agent, "_post_chat_completion", side_effect=[first_error, success_response]):
            result = agent.judge("AI launch article")

        self.assertTrue(result.is_ai_related)
        self.assertEqual(result.model, "openrouter/auto")
        self.assertEqual(result.total_tokens, 112)

    def test_judge_falls_back_to_auto_on_404_model_not_found(self) -> None:
        agent = OpenRouterJudgeAgent(api_key="sk-test", model="qwen/not-available")
        not_found = HTTPError(
            url="https://openrouter.ai/api/v1/chat/completions",
            code=404,
            msg="not found",
            hdrs=None,
            fp=BytesIO(b'{"error":{"message":"No endpoints found"}}'),
        )
        success_response = {
            "choices": [{"message": {"content": '{"label": false, "confidence": 0.7, "reason": "Not mainly AI."}'}}]
        }

        with patch.object(agent, "_post_chat_completion", side_effect=[not_found, success_response]) as mocked:
            result = agent.judge("General startup funding article")

        self.assertFalse(result.is_ai_related)
        self.assertEqual(result.model, "openrouter/auto")
        self.assertEqual(mocked.call_count, 2)

    def test_judge_retries_on_url_error_then_fails(self) -> None:
        agent = OpenRouterJudgeAgent(api_key="sk-test", max_retries=1, retry_backoff_seconds=0)
        with patch.object(agent, "_post_chat_completion", side_effect=URLError("network down")):
            result = agent.judge("Any text")

        self.assertFalse(result.is_ai_related)
        self.assertEqual(result.reason, "Request failed")


class AIFilterOpenRouterFallbackTests(unittest.TestCase):
    def test_filter_articles_uses_llm_fallback_for_low_keyword_score(self) -> None:
        articles = [
            {
                "title": "Semiconductor firm ships new accelerator",
                "text": "The company says the chip boosts inference throughput for enterprise workloads.",
            }
        ]

        judge_result = JudgeResult(
            is_ai_related=True,
            confidence=0.83,
            reason="Primary focus is AI inference hardware.",
            model="openrouter/auto",
        )

        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "sk-or-test"}, clear=False):
            with patch("filter.ai_filter.OpenRouterJudgeAgent") as mock_judge_cls:
                mock_judge_cls.return_value.judge.return_value = judge_result

                kept = ai_filter_module.filter_articles(articles, threshold=0.9)

        self.assertEqual(len(kept), 1)
        self.assertIn("keyword_score", kept[0])
        mock_judge_cls.assert_called_once_with(api_key="sk-or-test")
        mock_judge_cls.return_value.judge.assert_called_once()

    def test_filter_articles_skips_llm_when_keyword_threshold_is_met(self) -> None:
        articles = [
            {
                "title": "Machine learning model reaches state-of-the-art",
                "text": "Researchers report advances in model efficiency.",
            }
        ]

        with patch("filter.ai_filter.OpenRouterJudgeAgent") as mock_judge_cls:
            kept = ai_filter_module.filter_articles(articles, threshold=0.01)

        self.assertEqual(len(kept), 1)
        self.assertIn("keyword_score", kept[0])
        mock_judge_cls.assert_not_called()

    def test_filter_articles_rejects_low_confidence_llm_positive(self) -> None:
        articles = [
            {
                "title": "New hardware benchmark announced",
                "text": "Brief mention of AI in one sentence.",
            }
        ]

        judge_result = JudgeResult(
            is_ai_related=True,
            confidence=0.2,
            reason="Maybe AI-related",
            model="openrouter/auto",
        )

        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "sk-or-test"}, clear=False):
            with patch("filter.ai_filter.OpenRouterJudgeAgent") as mock_judge_cls:
                mock_judge_cls.return_value.judge.return_value = judge_result
                kept = ai_filter_module.filter_articles(articles, threshold=0.9)

        self.assertEqual(len(kept), 0)

    def test_filter_articles_respects_llm_fallback_cap(self) -> None:
        articles = [
            {"title": "A", "text": "No keywords here"},
            {"title": "B", "text": "No keywords here either"},
        ]

        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "sk-or-test"}, clear=False):
            with patch("filter.ai_filter.LLM_FALLBACK_MAX_CALLS", 1):
                with patch("filter.ai_filter.OpenRouterJudgeAgent") as mock_judge_cls:
                    mock_judge_cls.return_value.judge.return_value = JudgeResult(
                        is_ai_related=False,
                        confidence=0.0,
                        reason="Not AI",
                        model="openrouter/auto",
                    )
                    kept, stats = ai_filter_module.filter_articles(
                        articles,
                        threshold=0.9,
                        return_stats=True,
                    )

        self.assertEqual(len(kept), 0)
        self.assertEqual(stats["llm_fallback_called"], 1)
        self.assertEqual(stats["llm_fallback_skipped_capped"], 1)


if __name__ == "__main__":
    unittest.main()

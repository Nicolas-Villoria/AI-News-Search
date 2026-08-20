"""utils/open_router.py - OpenRouter-backed LLM judge for AI relevance.

This module exposes a tiny agent wrapper used by the AI filter fallback path.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any
from urllib import error, request

from utils.helpers import get_logger


logger = get_logger(__name__)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "openrouter/auto"
DEFAULT_TIMEOUT_SECONDS = 25
DEFAULT_MAX_RETRIES = 2
DEFAULT_RETRY_BACKOFF_SECONDS = 0.5
MAX_ARTICLE_CHARS = 12000


SYSTEM_INSTRUCTIONS = (
	"You are a strict classifier for AI-related news. "
	"Return JSON only."
)


JUDGE_PROMPT_TEMPLATE = (
		"Classify whether the following article text is substantially about AI.\n\n"
		"Rules:\n"
		"- Label true only if AI is a primary topic, product, method, regulation, or impact.\n"
		"- Label false if AI is only a passing mention.\n"
		"- If uncertain, prefer false.\n\n"
		"Return valid JSON with this exact schema:\n"
		"{{\n"
		'  "label": true or false,\n'
		'  "confidence": number from 0.0 to 1.0,\n'
		'  "reason": "one short sentence"\n'
		"}}\n\n"
		"Article:\n"
		"<<<ARTICLE>>>\n"
		"{article_text}\n"
		"<<<END_ARTICLE>>>"
)


@dataclass(slots=True)
class JudgeResult:
	is_ai_related: bool
	confidence: float
	reason: str
	model: str
	prompt_tokens: int | None = None
	completion_tokens: int | None = None
	total_tokens: int | None = None


class OpenRouterJudgeAgent:
	"""Minimal OpenRouter agent with a single judging method."""

	def __init__(
		self,
		api_key: str | None,
		model: str | None = None,
		timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
		max_retries: int = DEFAULT_MAX_RETRIES,
		retry_backoff_seconds: float = DEFAULT_RETRY_BACKOFF_SECONDS,
	) -> None:
		self.api_key = (api_key or "").strip()
		self.model = (model or os.environ.get("OPENROUTER_MODEL") or DEFAULT_MODEL).strip()
		self.timeout_seconds = timeout_seconds
		self.max_retries = max_retries
		self.retry_backoff_seconds = retry_backoff_seconds
		self._warned_missing_key = False

	def _missing_key_result(self) -> JudgeResult:
		if not self._warned_missing_key:
			logger.warning(
				"OPENROUTER_API_KEY is not set. LLM fallback is disabled; article will be treated as non-AI."
			)
			self._warned_missing_key = True
		return JudgeResult(
			is_ai_related=False,
			confidence=0.0,
			reason="OpenRouter API key missing",
			model=self.model,
		)

	@staticmethod
	def _truncate_article_text(article_text: str, max_chars: int = MAX_ARTICLE_CHARS) -> str:
		"""Trim prompt text at sentence boundary to keep requests compact."""
		text = (article_text or "").strip()
		if len(text) <= max_chars:
			return text

		cutoff = text[:max_chars]
		punctuation_idx = max(cutoff.rfind("."), cutoff.rfind("!"), cutoff.rfind("?"))
		newline_idx = cutoff.rfind("\n")
		breakpoint = max(punctuation_idx, newline_idx)
		if breakpoint >= int(max_chars * 0.7):
			return cutoff[: breakpoint + 1].strip()
		return cutoff.strip()

	def _sleep_before_retry(self, attempt: int) -> None:
		backoff = self.retry_backoff_seconds * (2**attempt)
		time.sleep(backoff)

	def _post_chat_completion(self, payload: dict[str, Any]) -> dict[str, Any]:
		body = json.dumps(payload).encode("utf-8")
		req = request.Request(
			OPENROUTER_API_URL,
			data=body,
			headers={
				"Authorization": f"Bearer {self.api_key}",
				"Content-Type": "application/json",
				"Accept": "application/json",
			},
			method="POST",
		)
		with request.urlopen(req, timeout=self.timeout_seconds) as resp:
			return json.loads(resp.read().decode("utf-8"))

	@staticmethod
	def _extract_json_object(content: str) -> dict[str, Any] | None:
		text = content.strip()

		if text.startswith("```"):
			text = text.strip("`")
			if text.startswith("json"):
				text = text[4:].strip()

		try:
			parsed = json.loads(text)
			if isinstance(parsed, dict):
				return parsed
		except json.JSONDecodeError:
			pass

		start = text.find("{")
		end = text.rfind("}")
		if start == -1 or end == -1 or end <= start:
			return None

		try:
			parsed = json.loads(text[start : end + 1])
			if isinstance(parsed, dict):
				return parsed
		except json.JSONDecodeError:
			return None
		return None

	def judge(self, article_text: str) -> JudgeResult:
		if not self.api_key:
			return self._missing_key_result()

		truncated_text = self._truncate_article_text(article_text)
		user_prompt = JUDGE_PROMPT_TEMPLATE.format(article_text=truncated_text)
		model_candidates = [self.model]
		if self.model != DEFAULT_MODEL:
			model_candidates.append(DEFAULT_MODEL)

		for model_name in model_candidates:
			payload = {
				"model": model_name,
				"temperature": 0,
				"messages": [
					{"role": "system", "content": SYSTEM_INSTRUCTIONS},
					{"role": "user", "content": user_prompt},
				],
				"response_format": {"type": "json_object"},
			}

			for attempt in range(self.max_retries + 1):
				try:
					data = self._post_chat_completion(payload)
					content = (
						data.get("choices", [{}])[0]
						.get("message", {})
						.get("content", "")
					)
					parsed = self._extract_json_object(content)
					if not parsed:
						logger.warning("OpenRouter judge returned non-JSON content; defaulting to false")
						return JudgeResult(
							is_ai_related=False,
							confidence=0.0,
							reason="Non-JSON response from model",
							model=model_name,
						)

					label = bool(parsed.get("label", False))
					confidence_raw = parsed.get("confidence", 0.0)
					reason = str(parsed.get("reason", "No reason provided"))

					try:
						confidence = float(confidence_raw)
					except (TypeError, ValueError):
						confidence = 0.0

					usage = data.get("usage", {}) or {}
					prompt_tokens = usage.get("prompt_tokens")
					completion_tokens = usage.get("completion_tokens")
					total_tokens = usage.get("total_tokens")
					logger.debug(
						"OpenRouter judge success (model=%s, prompt_tokens=%s, completion_tokens=%s, total_tokens=%s)",
						model_name,
						prompt_tokens,
						completion_tokens,
						total_tokens,
					)

					confidence = max(0.0, min(confidence, 1.0))
					return JudgeResult(
						is_ai_related=label,
						confidence=confidence,
						reason=reason,
						model=model_name,
						prompt_tokens=prompt_tokens,
						completion_tokens=completion_tokens,
						total_tokens=total_tokens,
					)

				except error.HTTPError as exc:
					details = exc.read().decode("utf-8", errors="ignore")
					if exc.code == 404 and model_name != DEFAULT_MODEL:
						logger.warning(
							"OpenRouter model '%s' not available (404). Falling back to '%s'.",
							model_name,
							DEFAULT_MODEL,
						)
						break
					if exc.code >= 500 and attempt < self.max_retries:
						logger.warning(
							"OpenRouter HTTPError %s (attempt %s/%s). Retrying...",
							exc.code,
							attempt + 1,
							self.max_retries + 1,
						)
						self._sleep_before_retry(attempt)
						continue
					logger.warning("OpenRouter HTTPError %s: %s", exc.code, details)
					break
				except error.URLError as exc:
					if attempt < self.max_retries:
						logger.warning(
							"OpenRouter URLError (attempt %s/%s): %s. Retrying...",
							attempt + 1,
							self.max_retries + 1,
							exc.reason,
						)
						self._sleep_before_retry(attempt)
						continue
					logger.warning("OpenRouter URLError: %s", exc.reason)
					break
				except Exception as exc:  # pragma: no cover - defensive guard
					logger.warning("OpenRouter judge failed: %s", exc)
					break

		return JudgeResult(
			is_ai_related=False,
			confidence=0.0,
			reason="Request failed",
			model=self.model,
		)
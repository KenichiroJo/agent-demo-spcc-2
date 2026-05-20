# Copyright 2026 DataRobot, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""Thin async client that delegates SPCC evaluation to the LangGraph agent.

The agent exposes an OpenAI-compatible `/v1/chat/completions` endpoint. We
embed the structured call payload as JSON in the user message; the agent's
preprocess node parses it back out.
"""
from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from openai import APIError, AsyncOpenAI

from app.config import Config

logger = logging.getLogger(__name__)


class AgentEvaluationError(RuntimeError):
    """Raised when the agent fails to produce a valid evaluation."""


def _build_client(config: Config) -> AsyncOpenAI:
    endpoint = config.agent_endpoint or "http://localhost:8842"
    return AsyncOpenAI(
        base_url=f"{endpoint.rstrip('/')}/v1",
        api_key="not-needed",
        timeout=150.0,
    )


def _extract_json(text: str) -> dict[str, Any]:
    """Tolerantly extract the JSON object from an LLM response."""
    text = text.strip()
    if text.startswith("```"):
        # Strip code fences (```json ... ``` or ``` ... ```)
        lines = text.split("\n")
        if lines:
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"応答にJSONオブジェクトが見つかりません: {text[:200]}")
    return json.loads(text[start : end + 1])


async def evaluate_call(
    config: Config,
    payload: dict[str, Any],
    *,
    max_retries: int = 1,
) -> dict[str, Any]:
    """Send a single call payload to the agent and return parsed JSON.

    Retries once on transport / JSON-parse failures. Never raises — returns
    a dict containing an `error` key on irrecoverable failure so the caller
    can surface it to the UI without aborting the whole batch.
    """
    last_err: str | None = None
    client = _build_client(config)
    for attempt in range(max_retries + 1):
        try:
            resp = await client.chat.completions.create(
                model=payload.get("model", "datarobot/azure/gpt-4o-mini"),
                messages=[
                    {
                        "role": "user",
                        "content": json.dumps(payload, ensure_ascii=False),
                    }
                ],
                temperature=0.2,
            )
            content = resp.choices[0].message.content or ""
            return _extract_json(content)
        except (httpx.HTTPError, APIError) as exc:
            last_err = f"agent transport error: {exc}"
            logger.warning(
                "Agent eval transport error (attempt %d/%d): %s",
                attempt + 1,
                max_retries + 1,
                exc,
            )
        except (json.JSONDecodeError, ValueError) as exc:
            last_err = f"agent returned non-JSON: {exc}"
            logger.warning(
                "Agent eval JSON parse error (attempt %d/%d): %s",
                attempt + 1,
                max_retries + 1,
                exc,
            )
        except Exception as exc:  # noqa: BLE001 - last-resort safety net
            last_err = f"unexpected agent error: {exc}"
            logger.exception("Agent eval unexpected error")
            break  # don't retry unknown failures
    return {"error": last_err or "unknown agent failure"}

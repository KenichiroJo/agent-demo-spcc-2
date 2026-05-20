# Copyright 2026 DataRobot, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""SPCC (Speech Processing Contact Center) emotion karte evaluation agent.

This module exposes the OpenAI-compatible ``MyAgent`` class expected by the
DataRobot agent framework. Internally it builds a 3-node LangGraph
(``preprocess`` → ``evaluate`` → ``format``) that scores a single call along
five dimensions and returns a strict-JSON verdict.

Input contract
--------------
The caller (fastapi_server) sends a single user message whose ``content`` is
a JSON string with the call payload (operator, transcript excerpt, emotion
section averages, peak utterances, etc.). The ``preprocess`` node parses it,
the ``evaluate`` node fills the templates and invokes the LLM via the
DataRobot LLM Gateway, and the ``format`` node validates / returns the JSON.
"""
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any, Optional

import litellm
from datarobot_genai.core.agents import InvokeReturn, make_system_prompt
from datarobot_genai.core.agents.base import UsageMetrics
from datarobot_genai.core.chat import agent_chat_completion_wrapper
from datarobot_genai.core.mcp import MCPConfig
from datarobot_genai.langgraph.agent import datarobot_agent_class_from_langgraph
from datarobot_genai.langgraph.llm import get_llm
from datarobot_genai.langgraph.mcp import mcp_tools_context
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, MessagesState, StateGraph
from openai.types.chat import CompletionCreateParams

if TYPE_CHECKING:
    from ragas import MultiTurnSample

litellm.modify_params = True
logger = logging.getLogger(__name__)

_PLACEHOLDER_MODELS = frozenset({"unknown"})

SYSTEM_PROMPT = make_system_prompt(
    """あなたはコールセンターのオペレーター品質評価の専門家です。
提供された通話テキストと感情スコアデータを分析し、以下の5項目を各5点満点で採点してください。

【評価項目】
1. 傾聴・共感力 (listening): 顧客の感情を受け止め適切に共感できているか
2. 問題解決力 (problem_solving): 顧客の問題を正確に把握し解決に導けているか
3. 説明の明確さ (clarity): 仕様・手順を分かりやすく正確に説明できているか
4. 言葉遣い・マナー (manner): 適切な敬語・丁寧な言葉遣いを維持できているか
5. 通話効率 (efficiency): 無駄な保留を避け適切な時間で解決できているか

合計点に応じてグレードを付与:
- 22-25点: S
- 18-21点: A
- 13-17点: B
- 5-12点: C

必ず以下のJSON形式のみで出力すること（前後に説明文・コードフェンス・コメントを付けないこと）:
{
  "scores": {
    "listening": <1-5の整数>,
    "problem_solving": <1-5の整数>,
    "clarity": <1-5の整数>,
    "manner": <1-5の整数>,
    "efficiency": <1-5の整数>
  },
  "total": <合計点 5-25>,
  "grade": "<S/A/B/C のいずれか>",
  "summary": "<通話全体の要約 2-3文>",
  "highlights": ["<良かった点1>", "<良かった点2>"],
  "improvements": ["<改善点1>", "<改善点2>"],
  "coaching": "<SVへの具体的なコーチング提案 1-2文>",
  "peak_moment": "<不満・怒りがピークになった発言の内容と時刻>",
  "resolution": "<どのように解決・収束したか>"
}
"""
)

USER_TEMPLATE = """【通話情報】
- オペレーター: {operator}
- 問合せ種別: {skill}
- 通話時間: {duration_sec}秒（{duration_min}分）

【顧客感情スコア推移】
- 前半: ポジティブ={pos_1:.1f} / 不満={dis_1:.1f} / 怒り={ang_1:.1f} / エージェントスコア={agent_1:.1f}
- 中盤: ポジティブ={pos_2:.1f} / 不満={dis_2:.1f} / 怒り={ang_2:.1f} / エージェントスコア={agent_2:.1f}
- 後半: ポジティブ={pos_3:.1f} / 不満={dis_3:.1f} / 怒り={ang_3:.1f} / エージェントスコア={agent_3:.1f}

【不満スコア5以上の発言】
{peak_text}

【会話全文（先頭4000文字）】
{transcript}
"""

# The framework requires a ChatPromptTemplate to be exposed; the variables
# are placeholders so SDK introspection still works. The actual prompt is
# built dynamically inside ``evaluate_node`` from the parsed payload.
prompt_template = ChatPromptTemplate.from_messages(
    [
        ("system", "{system}"),
        ("user", "{user}"),
    ]
)


class SPCCState(MessagesState):
    """LangGraph state extending MessagesState with SPCC-specific fields."""

    call_payload: dict[str, Any]
    llm_result: dict[str, Any]
    error: Optional[str]


def _parse_payload(messages: list[Any]) -> dict[str, Any]:
    """Locate the JSON payload in the last human message."""
    for msg in reversed(messages):
        content = getattr(msg, "content", None)
        if not content:
            continue
        if isinstance(content, list):  # multimodal content blocks
            text_chunks = [
                c.get("text", "") for c in content if isinstance(c, dict)
            ]
            content = "\n".join(text_chunks)
        if not isinstance(content, str):
            continue
        text = content.strip()
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end < start:
            continue
        try:
            return json.loads(text[start : end + 1])  # type: ignore[no-any-return]
        except json.JSONDecodeError:
            continue
    raise ValueError("No JSON payload found in messages")


def _coerce_int(v: Any, lo: int = 1, hi: int = 5) -> int:
    try:
        n = int(v)
    except (TypeError, ValueError):
        return lo
    return max(lo, min(hi, n))


def _derive_grade(total: int) -> str:
    if total >= 22:
        return "S"
    if total >= 18:
        return "A"
    if total >= 13:
        return "B"
    return "C"


def _normalize_eval_result(raw: dict[str, Any]) -> dict[str, Any]:
    """Coerce LLM output into the documented schema, filling gaps safely."""
    scores_in = raw.get("scores") or {}
    scores = {
        "listening": _coerce_int(scores_in.get("listening")),
        "problem_solving": _coerce_int(scores_in.get("problem_solving")),
        "clarity": _coerce_int(scores_in.get("clarity")),
        "manner": _coerce_int(scores_in.get("manner")),
        "efficiency": _coerce_int(scores_in.get("efficiency")),
    }
    total = sum(scores.values())
    grade = raw.get("grade") if raw.get("grade") in {"S", "A", "B", "C"} else _derive_grade(total)
    highlights = raw.get("highlights") or []
    improvements = raw.get("improvements") or []
    return {
        "scores": scores,
        "total": total,
        "grade": grade,
        "summary": str(raw.get("summary") or ""),
        "highlights": [str(x) for x in highlights][:5],
        "improvements": [str(x) for x in improvements][:5],
        "coaching": str(raw.get("coaching") or ""),
        "peak_moment": str(raw.get("peak_moment") or ""),
        "resolution": str(raw.get("resolution") or ""),
    }


def graph_factory(
    llm: BaseChatModel, tools: list[BaseTool], verbose: bool = False
) -> StateGraph:
    """Build the SPCC evaluation graph (preprocess → evaluate → format).

    ``tools`` is accepted for SDK compatibility but unused: this agent does
    not call external tools — its job is pure structured evaluation.
    """
    del tools  # intentionally unused

    def preprocess_node(state: SPCCState) -> dict[str, Any]:
        try:
            payload = _parse_payload(state["messages"])
        except ValueError as exc:
            logger.warning("SPCC preprocess: %s", exc)
            return {"call_payload": {}, "error": str(exc)}
        return {"call_payload": payload, "error": None}

    def evaluate_node(state: SPCCState) -> dict[str, Any]:
        if state.get("error"):
            return {"llm_result": {"error": state["error"]}}
        payload = state.get("call_payload") or {}
        if not payload:
            return {"llm_result": {"error": "empty call_payload"}}

        defaults = {
            "operator": "(unknown)",
            "skill": "(unknown)",
            "duration_sec": 0,
            "duration_min": 0.0,
            "transcript": "",
            "peak_text": "(なし)",
            "pos_1": 0.0,
            "dis_1": 0.0,
            "ang_1": 0.0,
            "agent_1": 0.0,
            "pos_2": 0.0,
            "dis_2": 0.0,
            "ang_2": 0.0,
            "agent_2": 0.0,
            "pos_3": 0.0,
            "dis_3": 0.0,
            "ang_3": 0.0,
            "agent_3": 0.0,
        }
        merged = {**defaults, **{k: payload.get(k, v) for k, v in defaults.items()}}
        try:
            user_msg = USER_TEMPLATE.format(**merged)
        except (KeyError, ValueError) as exc:
            logger.exception("SPCC evaluate format error")
            return {"llm_result": {"error": f"prompt format error: {exc}"}}

        messages = [
            ("system", SYSTEM_PROMPT),
            ("user", user_msg),
        ]
        try:
            response = llm.invoke(messages)
        except Exception as exc:  # noqa: BLE001
            logger.exception("SPCC evaluate LLM error")
            return {"llm_result": {"error": f"llm error: {exc}"}}

        content = getattr(response, "content", "") or ""
        if isinstance(content, list):
            content = "\n".join(c.get("text", "") for c in content if isinstance(c, dict))
        return {"llm_result": {"_raw": content}}

    def format_node(state: SPCCState) -> dict[str, Any]:
        result = state.get("llm_result") or {}
        if result.get("error"):
            payload = result
        else:
            raw = str(result.get("_raw") or "")
            text = raw.strip()
            if text.startswith("```"):
                text = "\n".join(text.split("\n")[1:])
                if text.rstrip().endswith("```"):
                    text = text.rstrip()[:-3]
            start = text.find("{")
            end = text.rfind("}")
            if start == -1 or end == -1 or end < start:
                payload = {"error": "non-JSON response", "_raw": raw[:500]}
            else:
                try:
                    parsed = json.loads(text[start : end + 1])
                    payload = _normalize_eval_result(parsed)
                except json.JSONDecodeError as exc:
                    payload = {"error": f"json decode: {exc}", "_raw": raw[:500]}
        return {
            "llm_result": payload,
            "messages": [AIMessage(content=json.dumps(payload, ensure_ascii=False))],
        }

    g = StateGraph(SPCCState)
    g.add_node("preprocess", preprocess_node)
    g.add_node("evaluate", evaluate_node)
    g.add_node("format", format_node)
    g.add_edge(START, "preprocess")
    g.add_edge("preprocess", "evaluate")
    g.add_edge("evaluate", "format")
    g.add_edge("format", END)
    return g


MyAgent = datarobot_agent_class_from_langgraph(graph_factory, prompt_template)


async def custompy_adaptor(
    completion_create_params: CompletionCreateParams,
) -> InvokeReturn | tuple[str, Optional["MultiTurnSample"], UsageMetrics]:
    """Bridge OpenAI chat-completion requests to the LangGraph agent.

    Kept compatible with the original adaptor so DataRobot SDK plumbing
    (DRUM, forwarded headers, MCP context) continues to work unchanged.
    """
    forwarded_headers = completion_create_params.get("forwarded_headers", {})
    authorization_context = completion_create_params.get("authorization_context", {})
    mcp_config = MCPConfig(
        forwarded_headers=forwarded_headers,
        authorization_context=authorization_context,
    )
    mcp_tools_factory = lambda: mcp_tools_context(mcp_config)  # noqa: E731
    model_name = completion_create_params.get("model")
    agent = MyAgent(
        llm=get_llm(
            model_name=model_name if model_name not in _PLACEHOLDER_MODELS else None
        ),
        verbose=completion_create_params.get("verbose", True),  # type: ignore[arg-type]
        timeout=completion_create_params.get("timeout", 150),  # type: ignore[arg-type]
        forwarded_headers=forwarded_headers,  # type: ignore[arg-type]
    )
    return await agent_chat_completion_wrapper(
        agent, completion_create_params, mcp_tools_factory
    )

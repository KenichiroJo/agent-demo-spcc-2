# Copyright 2026 DataRobot, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""Tests for the SPCC LangGraph evaluation agent."""

import asyncio
import json
from unittest.mock import AsyncMock, Mock, patch

import pytest
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate

from agent import MyAgent
from agent.myagent import (
    _derive_grade,
    _normalize_eval_result,
    _parse_payload,
    graph_factory,
    prompt_template,
)


class TestSPCCAgent:
    @pytest.fixture
    def agent(self) -> MyAgent:
        return MyAgent(llm=Mock(), verbose=True)

    def test_myagent_is_langgraph_agent_subclass(self) -> None:
        from datarobot_genai.langgraph.agent import LangGraphAgent

        assert issubclass(MyAgent, LangGraphAgent)

    def test_prompt_template_is_chat_prompt(self) -> None:
        assert isinstance(prompt_template, ChatPromptTemplate)

    def test_graph_factory_has_three_nodes(self) -> None:
        graph = graph_factory(Mock(), [], verbose=False)
        assert "preprocess" in graph.nodes
        assert "evaluate" in graph.nodes
        assert "format" in graph.nodes

    def test_parse_payload_extracts_json(self) -> None:
        msg = HumanMessage(content='{"operator": "テスト", "skill": "問合せ"}')
        result = _parse_payload([msg])
        assert result["operator"] == "テスト"

    def test_parse_payload_finds_embedded_json(self) -> None:
        msg = HumanMessage(content='前置き {"a": 1} 後置き')
        assert _parse_payload([msg]) == {"a": 1}

    def test_parse_payload_raises_when_missing(self) -> None:
        with pytest.raises(ValueError):
            _parse_payload([HumanMessage(content="no json here")])

    def test_normalize_clamps_scores(self) -> None:
        raw = {
            "scores": {
                "listening": 9,
                "problem_solving": "3",
                "clarity": -1,
                "manner": 4,
                "efficiency": "foo",
            },
        }
        out = _normalize_eval_result(raw)
        assert out["scores"]["listening"] == 5
        assert out["scores"]["problem_solving"] == 3
        assert out["scores"]["clarity"] == 1
        assert out["scores"]["manner"] == 4
        assert out["scores"]["efficiency"] == 1
        assert out["total"] == 14

    @pytest.mark.parametrize(
        "total,expected",
        [(25, "S"), (22, "S"), (21, "A"), (18, "A"), (17, "B"), (13, "B"), (12, "C"), (5, "C")],
    )
    def test_derive_grade(self, total: int, expected: str) -> None:
        assert _derive_grade(total) == expected

    def test_full_graph_happy_path(self) -> None:
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = json.dumps(
            {
                "scores": {
                    "listening": 4,
                    "problem_solving": 3,
                    "clarity": 4,
                    "manner": 5,
                    "efficiency": 3,
                },
                "summary": "テスト要約",
                "highlights": ["丁寧な対応"],
                "improvements": ["説明をもう少し明確に"],
                "coaching": "次回はより簡潔に",
                "peak_moment": "中盤で不満上昇",
                "resolution": "最終的に納得",
            }
        )
        mock_llm.invoke.return_value = mock_response

        graph = graph_factory(mock_llm, [], verbose=False).compile()
        payload = {
            "operator": "テスト オペレーター",
            "skill": "問合せ",
            "duration_sec": 600,
            "duration_min": 10.0,
            "transcript": "C: こんにちは\nO: いつもお世話になっております",
            "peak_text": "(なし)",
        }
        result = graph.invoke(
            {"messages": [HumanMessage(content=json.dumps(payload))]}
        )
        eval_out = result["llm_result"]
        assert eval_out["scores"]["listening"] == 4
        assert eval_out["total"] == 19
        assert eval_out["grade"] == "A"
        assert eval_out["summary"] == "テスト要約"

    def test_full_graph_llm_error(self) -> None:
        mock_llm = Mock()
        mock_llm.invoke.side_effect = RuntimeError("gateway 503")
        graph = graph_factory(mock_llm, [], verbose=False).compile()
        result = graph.invoke(
            {"messages": [HumanMessage(content='{"operator": "x"}')]}
        )
        assert "error" in result["llm_result"]
        assert "gateway 503" in result["llm_result"]["error"]

    def test_full_graph_non_json_response(self) -> None:
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = "これは JSON ではありません"
        mock_llm.invoke.return_value = mock_response
        graph = graph_factory(mock_llm, [], verbose=False).compile()
        result = graph.invoke(
            {"messages": [HumanMessage(content='{"operator": "x"}')]}
        )
        assert "error" in result["llm_result"]
        assert "non-JSON" in result["llm_result"]["error"]


class TestCustompyAdaptor:
    @pytest.mark.parametrize(
        "model_value, expected_model_name",
        [
            ("unknown", None),
            ("gpt-4", "gpt-4"),
            ("datarobot-deployed-llm", "datarobot-deployed-llm"),
            (None, None),
        ],
    )
    @patch("agent.myagent.get_llm", return_value=Mock())
    @patch("agent.myagent.agent_chat_completion_wrapper", new_callable=AsyncMock)
    @patch("agent.myagent.mcp_tools_context")
    def test_custompy_adaptor_filters_placeholder_models(
        self,
        mock_mcp_ctx: Mock,
        mock_wrapper: AsyncMock,
        mock_get_llm: Mock,
        model_value: str | None,
        expected_model_name: str | None,
    ) -> None:
        from agent.myagent import custompy_adaptor

        completion_create_params = {
            "model": model_value,
            "messages": [{"role": "user", "content": "hi"}],
        }
        asyncio.get_event_loop().run_until_complete(
            custompy_adaptor(completion_create_params)  # type: ignore[arg-type]
        )
        mock_get_llm.assert_called_once()
        assert mock_get_llm.call_args[1]["model_name"] == expected_model_name

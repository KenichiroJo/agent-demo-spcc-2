# Copyright 2026 DataRobot, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""Integration tests for SPCC endpoints (LLM is mocked)."""
from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import create_app
from app.api.v1.spcc.session import SPCCSessionManager
from app.config import Config
from app.deps import Deps

from .fixtures import calls_csv_bytes, utterances_csv_bytes


@pytest.fixture
def spcc_app(config: Config, deps: Deps) -> FastAPI:
    deps.spcc_session_mgr = SPCCSessionManager()
    return create_app(config=config, deps=deps)


@pytest.fixture
def spcc_client(spcc_app: FastAPI) -> TestClient:
    with TestClient(spcc_app) as c:
        yield c


def _fake_eval(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return {
        "scores": {
            "listening": 4,
            "problem_solving": 4,
            "clarity": 3,
            "manner": 5,
            "efficiency": 3,
        },
        "total": 19,
        "grade": "A",
        "summary": "丁寧な対応だが説明にやや時間がかかった。",
        "highlights": ["共感的な姿勢", "敬語の正確さ"],
        "improvements": ["説明の冗長さ"],
        "coaching": "要点を先に伝える練習を推奨。",
        "peak_moment": "中盤で不満が上昇",
        "resolution": "最終的に顧客は納得",
    }


def test_upload_creates_session_and_returns_stats(spcc_client: TestClient) -> None:
    res = spcc_client.post(
        "/api/v1/spcc/upload",
        files={
            "calls_file": ("masked.csv", calls_csv_bytes(), "text/csv"),
            "utterances_file": ("Recognition.csv", utterances_csv_bytes(), "text/csv"),
        },
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert "session_id" in body
    assert body["stats"]["total_calls"] == 3
    assert body["stats"]["alert_calls"] == 1
    assert body["stats"]["operator_count"] == 2


def test_upload_rejects_missing_columns(spcc_client: TestClient) -> None:
    res = spcc_client.post(
        "/api/v1/spcc/upload",
        files={
            "calls_file": ("bad.csv", b"\xef\xbb\xbfa,b\n1,2\n", "text/csv"),
            "utterances_file": ("Recognition.csv", utterances_csv_bytes(), "text/csv"),
        },
    )
    assert res.status_code == 400


def test_dashboard_operators_calls_flow(spcc_client: TestClient) -> None:
    res = spcc_client.post(
        "/api/v1/spcc/upload",
        files={
            "calls_file": ("masked.csv", calls_csv_bytes(), "text/csv"),
            "utterances_file": ("Recognition.csv", utterances_csv_bytes(), "text/csv"),
        },
    )
    session_id = res.json()["session_id"]

    dash = spcc_client.get(f"/api/v1/spcc/session/{session_id}/dashboard")
    assert dash.status_code == 200
    assert dash.json()["total_calls"] == 3

    ops = spcc_client.get(f"/api/v1/spcc/session/{session_id}/operators")
    assert ops.status_code == 200
    names = {op["name"] for op in ops.json()}
    assert "1st_SL_山本 里美" in names

    calls = spcc_client.get(
        f"/api/v1/spcc/session/{session_id}/calls", params={"flag_only": "true"}
    )
    assert calls.status_code == 200
    assert all(c["flagged"] for c in calls.json())


@patch("app.api.v1.spcc.endpoints.evaluate_call", side_effect=_fake_eval)
def test_call_detail_invokes_llm_with_cache(
    _mock: Any, spcc_client: TestClient
) -> None:
    upload = spcc_client.post(
        "/api/v1/spcc/upload",
        files={
            "calls_file": ("masked.csv", calls_csv_bytes(), "text/csv"),
            "utterances_file": ("Recognition.csv", utterances_csv_bytes(), "text/csv"),
        },
    )
    session_id = upload.json()["session_id"]

    detail = spcc_client.get(
        f"/api/v1/spcc/session/{session_id}/call/call-002"
    )
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["llm_eval"]["grade"] == "A"
    assert body["llm_eval"]["scores"]["listening"] == 4
    assert len(body["peak_utterances"]) >= 1
    # Second call should hit the cache (mock invoked once total)
    detail2 = spcc_client.get(
        f"/api/v1/spcc/session/{session_id}/call/call-002"
    )
    assert detail2.status_code == 200
    assert _mock.call_count == 1


def test_unknown_session_returns_404(spcc_client: TestClient) -> None:
    res = spcc_client.get("/api/v1/spcc/session/nonexistent/dashboard")
    assert res.status_code == 404

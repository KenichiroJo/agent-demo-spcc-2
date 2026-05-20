# Copyright 2026 DataRobot, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""HTTP endpoints for the SPCC emotion karte LLM evaluation API."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile, status

from app.deps import Deps

from . import aggregator
from .agent_client import evaluate_call
from .data_loader import (
    CSVLoadError,
    compute_call_aggregates,
    compute_emotion_timeline,
    extract_peak_utterances,
    join_data,
    load_calls,
    load_utterances,
)
from .schemas import (
    CallDetail,
    CallSummary,
    DashboardStats,
    EmotionPoint,
    LLMEvalResult,
    OperatorReport,
    OperatorSummary,
    PeakUtterance,
    UploadResponse,
)
from .session import SPCCSessionData

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_UPLOAD_BYTES = 200 * 1024 * 1024  # 200 MB per file
PEAK_THRESHOLD = 5.0
EVAL_CONCURRENCY = 5


def _get_deps(request: Request) -> Deps:
    deps: Deps | None = getattr(request.app.state, "deps", None)
    if deps is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Application dependencies are not initialised yet",
        )
    return deps


async def _read_capped(file: UploadFile, max_bytes: int, label: str) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"{label} がアップロード上限({max_bytes // (1024 * 1024)} MB)を超えました",
            )
        chunks.append(chunk)
    return b"".join(chunks)


# ---------------- Upload ----------------


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="2 つの CSV をアップロードして SPCC セッションを作成する",
)
async def upload(
    request: Request,
    calls_file: UploadFile = File(..., description="通話単位CSV (utf-8-sig)"),
    utterances_file: UploadFile = File(..., description="発話単位CSV (cp932)"),
) -> UploadResponse:
    deps = _get_deps(request)
    if deps.spcc_session_mgr is None:
        raise HTTPException(503, "SPCC session manager is not configured")

    calls_bytes = await _read_capped(calls_file, MAX_UPLOAD_BYTES, "通話単位CSV")
    utt_bytes = await _read_capped(utterances_file, MAX_UPLOAD_BYTES, "発話単位CSV")

    try:
        calls_df = load_calls(calls_bytes)
        utterances_df = load_utterances(utt_bytes)
        loaded = join_data(calls_df, utterances_df)
    except CSVLoadError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    aggregates = compute_call_aggregates(loaded.calls, loaded.utterances)
    session_data = SPCCSessionData(
        calls_df=loaded.calls,
        utterances_df=loaded.utterances,
        aggregates_df=aggregates,
        match_rate=loaded.match_rate,
    )
    session_id = await deps.spcc_session_mgr.create(session_data)
    stats = aggregator.build_dashboard(session_data)
    return UploadResponse(session_id=session_id, stats=stats)


# ---------------- Statistics (LLM-free) ----------------


async def _require_session(request: Request, session_id: str) -> SPCCSessionData:
    deps = _get_deps(request)
    if deps.spcc_session_mgr is None:
        raise HTTPException(503, "SPCC session manager is not configured")
    data = await deps.spcc_session_mgr.get(session_id)
    if data is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "セッションが見つかりません")
    return data


@router.get(
    "/session/{session_id}/dashboard",
    response_model=DashboardStats,
    summary="全体ダッシュボードの集計値",
)
async def get_dashboard(request: Request, session_id: str) -> DashboardStats:
    data = await _require_session(request, session_id)
    return aggregator.build_dashboard(data)


@router.get(
    "/session/{session_id}/operators",
    response_model=list[OperatorSummary],
    summary="オペレーター一覧と各サマリ",
)
async def list_operators(request: Request, session_id: str) -> list[OperatorSummary]:
    data = await _require_session(request, session_id)
    return aggregator.list_operators(data)


@router.get(
    "/session/{session_id}/calls",
    response_model=list[CallSummary],
    summary="通話の絞り込み一覧",
)
async def list_calls(
    request: Request,
    session_id: str,
    operator_name: str | None = Query(default=None),
    skill: str | None = Query(default=None),
    min_duration: float | None = Query(default=None, ge=0),
    flag_only: bool = Query(default=False),
    limit: int = Query(default=200, ge=1, le=1000),
) -> list[CallSummary]:
    data = await _require_session(request, session_id)
    return aggregator.filter_calls(
        data,
        operator_name=operator_name,
        skill=skill,
        min_duration=min_duration,
        flag_only=flag_only,
        limit=limit,
    )


# ---------------- LLM evaluation ----------------


def _build_call_payload(data: SPCCSessionData, call_id: str) -> dict[str, Any] | None:
    row = aggregator.get_call_row(data, call_id)
    if row is None:
        return None
    timeline = compute_emotion_timeline(call_id, data.utterances_df)
    peaks = extract_peak_utterances(call_id, data.utterances_df, threshold=PEAK_THRESHOLD)
    transcript_full = str(row.get("latest") or "")
    transcript = transcript_full[:4000]

    by_section: dict[str, dict[str, float]] = {pt["section"]: pt for pt in timeline}  # type: ignore[misc]

    def _val(section: str, key: str) -> float:
        return float(by_section.get(section, {}).get(key, 0.0))

    duration_sec = float(row["duration"])
    return {
        "call_id": call_id,
        "operator": str(row["userName"]),
        "skill": str(row["skill"]),
        "duration_sec": round(duration_sec, 1),
        "duration_min": round(duration_sec / 60, 1),
        "direction": str(row.get("direction", "")),
        "transcript": transcript,
        "peak_text": "\n".join(
            f"- [不満{p['dissatisfied']:.1f} / 怒り{p['anger']:.1f}] {p['text']}" for p in peaks
        )
        or "(不満スコア5以上の発言なし)",
        "pos_1": _val("前半", "positive"),
        "dis_1": _val("前半", "dissatisfied"),
        "ang_1": _val("前半", "anger"),
        "agent_1": _val("前半", "agent_score"),
        "pos_2": _val("中盤", "positive"),
        "dis_2": _val("中盤", "dissatisfied"),
        "ang_2": _val("中盤", "anger"),
        "agent_2": _val("中盤", "agent_score"),
        "pos_3": _val("後半", "positive"),
        "dis_3": _val("後半", "dissatisfied"),
        "ang_3": _val("後半", "anger"),
        "agent_3": _val("後半", "agent_score"),
        "emotion_timeline": timeline,
        "peak_utterances": peaks,
    }


async def _evaluate_with_cache(
    deps: Deps, data: SPCCSessionData, call_id: str
) -> dict[str, Any]:
    cached = data.llm_cache.get(call_id)
    if cached is not None:
        return cached
    payload = _build_call_payload(data, call_id)
    if payload is None:
        raise HTTPException(404, f"通話が見つかりません: {call_id}")
    result = await evaluate_call(deps.config, payload)
    data.llm_cache[call_id] = result
    return result


def _to_llm_eval(raw: dict[str, Any]) -> LLMEvalResult:
    # Pydantic does the heavy lifting; tolerate junk fields and missing keys
    try:
        return LLMEvalResult.model_validate(raw)
    except Exception:  # noqa: BLE001
        return LLMEvalResult(error=str(raw)[:500])


@router.get(
    "/session/{session_id}/call/{call_id}",
    response_model=CallDetail,
    summary="通話の詳細 + 感情推移 + LLM 評価",
)
async def get_call_detail(
    request: Request, session_id: str, call_id: str
) -> CallDetail:
    data = await _require_session(request, session_id)
    row = aggregator.get_call_row(data, call_id)
    if row is None:
        raise HTTPException(404, f"通話が見つかりません: {call_id}")

    deps = _get_deps(request)
    raw_eval = await _evaluate_with_cache(deps, data, call_id)
    llm_eval = _to_llm_eval(raw_eval)
    timeline = [
        EmotionPoint(**p)  # type: ignore[arg-type]
        for p in compute_emotion_timeline(call_id, data.utterances_df)
    ]
    peaks = [
        PeakUtterance(**p)  # type: ignore[arg-type]
        for p in extract_peak_utterances(call_id, data.utterances_df, PEAK_THRESHOLD)
    ]
    return CallDetail(
        call_id=str(row["key"]),
        operator=str(row["userName"]),
        skill=str(row["skill"]),
        duration_sec=round(float(row["duration"]), 1),
        direction=str(row.get("direction", "")),
        emotion_timeline=timeline,
        transcript=str(row.get("latest") or ""),
        peak_utterances=peaks,
        llm_eval=llm_eval,
    )


@router.get(
    "/session/{session_id}/operator/{operator_name}",
    response_model=OperatorReport,
    summary="オペレーター別レポート + 代表通話の LLM 評価",
)
async def get_operator_report(
    request: Request, session_id: str, operator_name: str
) -> OperatorReport:
    data = await _require_session(request, session_id)
    summaries = aggregator.list_operators(data)
    summary = next((s for s in summaries if s.name == operator_name), None)
    if summary is None:
        raise HTTPException(404, f"オペレーターが見つかりません: {operator_name}")

    skill_breakdown = aggregator.operator_skill_breakdown(data, operator_name)
    recent_calls = aggregator.filter_calls(data, operator_name=operator_name, limit=20)
    representative = aggregator.pick_representative_call(data, operator_name)

    llm_eval: LLMEvalResult | None = None
    if representative is not None:
        deps = _get_deps(request)
        raw = await _evaluate_with_cache(deps, data, representative)
        llm_eval = _to_llm_eval(raw)

    return OperatorReport(
        operator=operator_name,
        summary_stats=summary,
        skill_breakdown=skill_breakdown,
        recent_calls=recent_calls,
        llm_eval_summary=llm_eval,
        representative_call_id=representative,
    )


@router.post(
    "/session/{session_id}/evaluate-batch",
    response_model=dict[str, LLMEvalResult],
    summary="複数通話をまとめて LLM 評価（並列、キャッシュ利用）",
)
async def evaluate_batch(
    request: Request,
    session_id: str,
    call_ids: list[str],
) -> dict[str, LLMEvalResult]:
    data = await _require_session(request, session_id)
    deps = _get_deps(request)
    semaphore = asyncio.Semaphore(EVAL_CONCURRENCY)

    async def _one(call_id: str) -> tuple[str, LLMEvalResult]:
        async with semaphore:
            raw = await _evaluate_with_cache(deps, data, call_id)
            return call_id, _to_llm_eval(raw)

    results = await asyncio.gather(
        *(_one(cid) for cid in call_ids), return_exceptions=False
    )
    return dict(results)

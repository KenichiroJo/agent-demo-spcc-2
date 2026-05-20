# Copyright 2026 DataRobot, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""CSV loading, joining, and emotion-timeline computation for SPCC."""
from __future__ import annotations

import io
import logging
from dataclasses import dataclass

import pandas as pd

logger = logging.getLogger(__name__)

CALLS_REQUIRED_COLS = ("key", "userName", "skill", "duration", "direction", "latest")
UTT_REQUIRED_COLS = (
    "通話ID",
    "音声のチャンネル種類",
    "発言内容(最新版数)",
    "CUの怒り",
    "CUの不満",
    "CUのポジティブ",
    "CUのエージェントスコア",
)
UTT_OPTIONAL_COLS = (
    "開始時間(最新版数)",
    "CUのネガティブ",
    "OPの怒り",
    "OPの不満",
    "OPのポジティブ",
    "OPのエージェントスコア",
)


class CSVLoadError(ValueError):
    """Raised when a CSV cannot be parsed or fails column validation."""


@dataclass
class LoadedData:
    calls: pd.DataFrame
    utterances: pd.DataFrame
    match_rate: float


def _decode_with_fallback(file_bytes: bytes, primary_encoding: str) -> pd.DataFrame:
    """Try primary encoding, then fall back with replacement on UnicodeDecodeError."""
    try:
        return pd.read_csv(io.BytesIO(file_bytes), encoding=primary_encoding)
    except UnicodeDecodeError as exc:
        logger.warning(
            "Primary encoding %s failed, retrying with errors=replace: %s",
            primary_encoding,
            exc,
        )
        return pd.read_csv(
            io.BytesIO(file_bytes),
            encoding=primary_encoding,
            encoding_errors="replace",
        )


def load_calls(file_bytes: bytes) -> pd.DataFrame:
    """Read the per-call CSV (utf-8-sig). Validates required columns."""
    try:
        df = _decode_with_fallback(file_bytes, "utf-8-sig")
    except Exception as exc:  # pragma: no cover - defensive
        raise CSVLoadError(f"通話単位CSVのパースに失敗しました: {exc}") from exc

    missing = [c for c in CALLS_REQUIRED_COLS if c not in df.columns]
    if missing:
        raise CSVLoadError(
            f"通話単位CSVに必須カラムが不足しています: {missing} / 検出カラム: {list(df.columns)[:10]}"
        )
    df["duration"] = pd.to_numeric(df["duration"], errors="coerce")
    df = df.dropna(subset=["key", "duration"])
    df["key"] = df["key"].astype(str)
    return df


def load_utterances(file_bytes: bytes) -> pd.DataFrame:
    """Read the per-utterance CSV (cp932). Validates required columns."""
    try:
        df = _decode_with_fallback(file_bytes, "cp932")
    except Exception as exc:  # pragma: no cover - defensive
        raise CSVLoadError(f"発話単位CSVのパースに失敗しました: {exc}") from exc

    missing = [c for c in UTT_REQUIRED_COLS if c not in df.columns]
    if missing:
        raise CSVLoadError(
            f"発話単位CSVに必須カラムが不足しています: {missing} / 検出カラム: {list(df.columns)[:10]}"
        )
    df = df.dropna(subset=["通話ID"])
    df["通話ID"] = df["通話ID"].astype(str)
    for col in (
        "CUの怒り",
        "CUの不満",
        "CUのポジティブ",
        "CUのエージェントスコア",
    ):
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    return df


def join_data(calls: pd.DataFrame, utterances: pd.DataFrame) -> LoadedData:
    """Compute join match rate; raise if too low."""
    call_keys = set(calls["key"].dropna().astype(str))
    utt_keys = set(utterances["通話ID"].dropna().astype(str))
    if not call_keys:
        raise CSVLoadError("通話単位CSVに有効な key がありません")
    overlap = call_keys & utt_keys
    match_rate = len(overlap) / len(call_keys)
    if match_rate < 0.5:
        raise CSVLoadError(
            f"結合キーの一致率が低すぎます: {match_rate:.1%}（通話単位の key と発話単位の 通話ID が紐づきません）"
        )
    return LoadedData(calls=calls, utterances=utterances, match_rate=match_rate)


def compute_emotion_timeline(
    call_id: str, utterances: pd.DataFrame
) -> list[dict[str, float | str]]:
    """Aggregate CU emotion scores into three sections (前半/中盤/後半)."""
    cu = utterances[
        (utterances["通話ID"] == call_id)
        & (utterances["音声のチャンネル種類"].astype(str).str.upper() == "CU")
    ].reset_index(drop=True)
    n = len(cu)
    if n == 0:
        return []

    third = max(n // 3, 1)
    sections: list[tuple[str, pd.DataFrame]] = [
        ("前半", cu.iloc[:third]),
        ("中盤", cu.iloc[third : 2 * third] if n >= 3 else cu.iloc[0:0]),
        ("後半", cu.iloc[2 * third :] if n >= 3 else cu.iloc[0:0]),
    ]
    out: list[dict[str, float | str]] = []
    for label, part in sections:
        if len(part) == 0:
            continue
        out.append(
            {
                "section": label,
                "positive": round(float(part["CUのポジティブ"].mean()), 3),
                "dissatisfied": round(float(part["CUの不満"].mean()), 3),
                "anger": round(float(part["CUの怒り"].mean()), 3),
                "agent_score": round(
                    float(part["CUのエージェントスコア"].mean()), 3
                ),
            }
        )
    return out


def extract_peak_utterances(
    call_id: str, utterances: pd.DataFrame, threshold: float = 5.0, limit: int = 5
) -> list[dict[str, str | float | None]]:
    """Return CU utterances with dissatisfaction >= threshold, top-N by score."""
    cu = utterances[
        (utterances["通話ID"] == call_id)
        & (utterances["音声のチャンネル種類"].astype(str).str.upper() == "CU")
        & (utterances["CUの不満"] >= threshold)
    ]
    if len(cu) == 0:
        return []
    cu_sorted = cu.sort_values("CUの不満", ascending=False).head(limit)
    out: list[dict[str, str | float | None]] = []
    ts_col = "開始時間(最新版数)" if "開始時間(最新版数)" in cu_sorted.columns else None
    for _, row in cu_sorted.iterrows():
        out.append(
            {
                "timestamp": str(row[ts_col]) if ts_col else None,
                "text": str(row["発言内容(最新版数)"]),
                "dissatisfied": round(float(row["CUの不満"]), 2),
                "anger": round(float(row["CUの怒り"]), 2),
            }
        )
    return out


def compute_call_aggregates(
    calls: pd.DataFrame, utterances: pd.DataFrame
) -> pd.DataFrame:
    """Pre-compute per-call max dissatisfaction & avg agent score (CU side)."""
    cu = utterances[utterances["音声のチャンネル種類"].astype(str).str.upper() == "CU"]
    agg = (
        cu.groupby("通話ID")
        .agg(
            max_dissatisfied=("CUの不満", "max"),
            avg_agent_score=("CUのエージェントスコア", "mean"),
        )
        .reset_index()
        .rename(columns={"通話ID": "key"})
    )
    merged = calls.merge(agg, on="key", how="left")
    merged["max_dissatisfied"] = merged["max_dissatisfied"].fillna(0.0)
    merged["avg_agent_score"] = merged["avg_agent_score"].fillna(0.0)
    merged["flagged"] = merged["max_dissatisfied"] >= 5.0
    return merged

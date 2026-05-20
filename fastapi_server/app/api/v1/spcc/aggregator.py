# Copyright 2026 DataRobot, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""Aggregations over the loaded SPCC dataframes."""
from __future__ import annotations

import pandas as pd

from .schemas import (
    CallSummary,
    DashboardStats,
    OperatorSummary,
    ScoreBucket,
    SkillCount,
)
from .session import SPCCSessionData

SCORE_BUCKETS: list[tuple[str, float, float]] = [
    ("0-3", 0.0, 3.0),
    ("3-5", 3.0, 5.0),
    ("5-7", 5.0, 7.0),
    ("7-10", 7.0, 10.01),
]


def build_dashboard(session: SPCCSessionData) -> DashboardStats:
    calls = session.aggregates_df
    total_calls = int(len(calls))
    avg_duration = float(calls["duration"].mean()) if total_calls > 0 else 0.0
    alert_calls = int(calls["flagged"].sum())
    operator_count = int(calls["userName"].nunique())

    skill_counts = (
        calls["skill"]
        .fillna("(未指定)")
        .value_counts()
        .head(10)
        .reset_index()
    )
    skill_counts.columns = ["skill", "count"]
    skill_breakdown = [
        SkillCount(skill=str(r["skill"]), count=int(r["count"]))
        for _, r in skill_counts.iterrows()
    ]

    distribution: list[ScoreBucket] = []
    for label, lo, hi in SCORE_BUCKETS:
        mask = (calls["avg_agent_score"] >= lo) & (calls["avg_agent_score"] < hi)
        distribution.append(ScoreBucket(range=label, count=int(mask.sum())))

    return DashboardStats(
        total_calls=total_calls,
        avg_duration_sec=round(avg_duration, 1),
        alert_calls=alert_calls,
        operator_count=operator_count,
        skill_breakdown=skill_breakdown,
        score_distribution=distribution,
        match_rate=round(session.match_rate, 3),
    )


def list_operators(session: SPCCSessionData) -> list[OperatorSummary]:
    calls = session.aggregates_df
    grouped = (
        calls.groupby("userName")
        .agg(
            calls_count=("key", "count"),
            avg_duration=("duration", "mean"),
            avg_agent_score=("avg_agent_score", "mean"),
            flagged_count=("flagged", "sum"),
        )
        .reset_index()
    )
    out: list[OperatorSummary] = []
    for _, r in grouped.iterrows():
        count = int(r["calls_count"])
        out.append(
            OperatorSummary(
                name=str(r["userName"]),
                calls_count=count,
                avg_duration_sec=round(float(r["avg_duration"]), 1),
                avg_agent_score=round(float(r["avg_agent_score"]), 2),
                alert_rate=round(float(r["flagged_count"]) / count, 3) if count else 0.0,
            )
        )
    out.sort(key=lambda x: x.calls_count, reverse=True)
    return out


def operator_skill_breakdown(
    session: SPCCSessionData, operator_name: str
) -> list[SkillCount]:
    calls = session.aggregates_df
    op_calls = calls[calls["userName"] == operator_name]
    if len(op_calls) == 0:
        return []
    skill_counts = op_calls["skill"].fillna("(未指定)").value_counts().reset_index()
    skill_counts.columns = ["skill", "count"]
    return [
        SkillCount(skill=str(r["skill"]), count=int(r["count"]))
        for _, r in skill_counts.iterrows()
    ]


def filter_calls(
    session: SPCCSessionData,
    *,
    operator_name: str | None = None,
    skill: str | None = None,
    min_duration: float | None = None,
    flag_only: bool = False,
    limit: int = 200,
) -> list[CallSummary]:
    df = session.aggregates_df
    if operator_name:
        df = df[df["userName"] == operator_name]
    if skill:
        df = df[df["skill"] == skill]
    if min_duration is not None:
        df = df[df["duration"] >= min_duration]
    if flag_only:
        df = df[df["flagged"]]

    df = df.sort_values(["flagged", "max_dissatisfied"], ascending=[False, False]).head(limit)

    out: list[CallSummary] = []
    for _, r in df.iterrows():
        out.append(_to_call_summary(r))
    return out


def _to_call_summary(row: pd.Series) -> CallSummary:
    return CallSummary(
        call_id=str(row["key"]),
        operator=str(row["userName"]),
        skill=str(row["skill"]),
        duration_sec=round(float(row["duration"]), 1),
        direction=str(row.get("direction", "")),
        max_dissatisfied=round(float(row["max_dissatisfied"]), 2),
        avg_agent_score=round(float(row["avg_agent_score"]), 2),
        flagged=bool(row["flagged"]),
    )


def get_call_row(session: SPCCSessionData, call_id: str) -> pd.Series | None:
    df = session.aggregates_df
    match = df[df["key"] == call_id]
    if len(match) == 0:
        return None
    return match.iloc[0]


def pick_representative_call(
    session: SPCCSessionData, operator_name: str
) -> str | None:
    """Choose the call with the highest dissatisfaction score for an operator."""
    df = session.aggregates_df
    op = df[df["userName"] == operator_name]
    if len(op) == 0:
        return None
    op_sorted = op.sort_values("max_dissatisfied", ascending=False)
    return str(op_sorted.iloc[0]["key"])

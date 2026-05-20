# Copyright 2026 DataRobot, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""Pydantic schemas for the SPCC evaluation API."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

# ---------------- Emotion timeline ----------------


class EmotionPoint(BaseModel):
    """Average emotion scores aggregated over a section of a call."""

    section: Literal["前半", "中盤", "後半"]
    positive: float
    dissatisfied: float
    anger: float
    agent_score: float


class PeakUtterance(BaseModel):
    """A customer utterance with high dissatisfaction score."""

    timestamp: Optional[str] = None
    text: str
    dissatisfied: float
    anger: float


# ---------------- LLM evaluation ----------------


class LLMScores(BaseModel):
    """Five-dimension score (1-5 each)."""

    listening: int = Field(ge=1, le=5)
    problem_solving: int = Field(ge=1, le=5)
    clarity: int = Field(ge=1, le=5)
    manner: int = Field(ge=1, le=5)
    efficiency: int = Field(ge=1, le=5)


class LLMEvalResult(BaseModel):
    """Structured LLM evaluation output."""

    model_config = ConfigDict(extra="ignore")

    scores: Optional[LLMScores] = None
    total: Optional[int] = Field(default=None, ge=5, le=25)
    grade: Optional[Literal["S", "A", "B", "C"]] = None
    summary: str = ""
    highlights: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    coaching: str = ""
    peak_moment: str = ""
    resolution: str = ""
    error: Optional[str] = None


# ---------------- Calls / Operators ----------------


class CallSummary(BaseModel):
    """Per-call summary row shown on the drilldown list."""

    call_id: str
    operator: str
    skill: str
    duration_sec: float
    direction: str
    max_dissatisfied: float
    avg_agent_score: float
    flagged: bool


class CallDetail(BaseModel):
    """Full call detail with emotion timeline + LLM evaluation."""

    call_id: str
    operator: str
    skill: str
    duration_sec: float
    direction: str
    emotion_timeline: list[EmotionPoint]
    transcript: str
    peak_utterances: list[PeakUtterance]
    llm_eval: Optional[LLMEvalResult] = None


# ---------------- Dashboard ----------------


class SkillCount(BaseModel):
    skill: str
    count: int


class ScoreBucket(BaseModel):
    range: str
    count: int


class DashboardStats(BaseModel):
    total_calls: int
    avg_duration_sec: float
    alert_calls: int
    operator_count: int
    skill_breakdown: list[SkillCount]
    score_distribution: list[ScoreBucket]
    match_rate: float


class OperatorSummary(BaseModel):
    name: str
    calls_count: int
    avg_duration_sec: float
    avg_agent_score: float
    alert_rate: float


class OperatorReport(BaseModel):
    operator: str
    summary_stats: OperatorSummary
    skill_breakdown: list[SkillCount]
    recent_calls: list[CallSummary]
    llm_eval_summary: Optional[LLMEvalResult] = None
    representative_call_id: Optional[str] = None


# ---------------- Upload / Session ----------------


class UploadResponse(BaseModel):
    session_id: str
    stats: DashboardStats


class ErrorResponse(BaseModel):
    detail: str

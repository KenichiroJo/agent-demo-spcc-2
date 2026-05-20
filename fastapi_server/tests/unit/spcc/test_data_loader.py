# Copyright 2026 DataRobot, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""Unit tests for SPCC CSV loading, joining, and emotion aggregation."""
from __future__ import annotations

import pytest

from app.api.v1.spcc.data_loader import (
    CSVLoadError,
    compute_call_aggregates,
    compute_emotion_timeline,
    extract_peak_utterances,
    join_data,
    load_calls,
    load_utterances,
)

from .fixtures import calls_csv_bytes, utterances_csv_bytes


def test_load_calls_returns_dataframe() -> None:
    df = load_calls(calls_csv_bytes())
    assert len(df) == 3
    assert set(["key", "userName", "skill", "duration"]).issubset(df.columns)
    assert df["key"].iloc[0] == "call-001"


def test_load_utterances_handles_cp932() -> None:
    df = load_utterances(utterances_csv_bytes())
    assert len(df) > 0
    assert "通話ID" in df.columns
    # Confirm Japanese decoded correctly
    assert any("料金プラン" in s for s in df["発言内容(最新版数)"])


def test_load_calls_missing_columns_raises() -> None:
    bad = b"\xef\xbb\xbfa,b,c\n1,2,3\n"  # utf-8-sig with no required cols
    with pytest.raises(CSVLoadError) as exc:
        load_calls(bad)
    assert "必須カラム" in str(exc.value)


def test_join_data_computes_match_rate() -> None:
    calls = load_calls(calls_csv_bytes())
    utts = load_utterances(utterances_csv_bytes())
    loaded = join_data(calls, utts)
    assert loaded.match_rate == 1.0


def test_join_data_low_match_rate_raises() -> None:
    calls = load_calls(calls_csv_bytes())
    utts = load_utterances(utterances_csv_bytes())
    utts = utts.assign(**{"通話ID": "no-match"})
    with pytest.raises(CSVLoadError) as exc:
        join_data(calls, utts)
    assert "一致率" in str(exc.value)


def test_compute_emotion_timeline_three_sections() -> None:
    utts = load_utterances(utterances_csv_bytes())
    timeline = compute_emotion_timeline("call-001", utts)
    sections = [pt["section"] for pt in timeline]
    assert "前半" in sections
    # Highly dissatisfied call: ensure dissatisfaction emerges
    timeline2 = compute_emotion_timeline("call-002", utts)
    dis_values = [pt["dissatisfied"] for pt in timeline2]
    assert max(dis_values) >= 7.0


def test_extract_peak_utterances() -> None:
    utts = load_utterances(utterances_csv_bytes())
    peaks = extract_peak_utterances("call-002", utts, threshold=5.0)
    assert len(peaks) >= 2
    assert all(p["dissatisfied"] >= 5.0 for p in peaks)


def test_compute_call_aggregates() -> None:
    calls = load_calls(calls_csv_bytes())
    utts = load_utterances(utterances_csv_bytes())
    agg = compute_call_aggregates(calls, utts)
    assert "max_dissatisfied" in agg.columns
    assert "flagged" in agg.columns
    # call-002 should be flagged (max_dissatisfied >= 5)
    row = agg[agg["key"] == "call-002"].iloc[0]
    assert row["flagged"]
    # call-001 should not be flagged
    row1 = agg[agg["key"] == "call-001"].iloc[0]
    assert not row1["flagged"]

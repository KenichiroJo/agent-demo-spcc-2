# Copyright 2026 DataRobot, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""Dummy SPCC CSV fixtures for tests and local development."""
from __future__ import annotations

import io

import pandas as pd

CALL_ROWS = [
    {
        "key": "call-001",
        "userName": "1st_SL_山本 里美",
        "skill": "チャンネル変更-1st",
        "duration": 600,
        "direction": "I",
        "latest": (
            "C: もしもし、料金プランの相談で電話したんですけど。\n"
            "O: いつもお世話になっております。担当の山本です。\n"
            "C: 説明が分かりにくくて困っているんです。\n"
            "O: 大変申し訳ございません。順を追ってご説明します。\n"
            "C: ありがとうございます、よく分かりました。"
        ),
    },
    {
        "key": "call-002",
        "userName": "1st_SL_田中 直樹",
        "skill": "解約-1st",
        "duration": 1320,
        "direction": "I",
        "latest": (
            "C: 解約したいんですが手続きが面倒すぎる！\n"
            "O: ご不便をおかけして申し訳ございません。\n"
            "C: もう何度も同じ説明をさせられている。\n"
            "O: 確認させていただきます。少々お待ちください。"
        ),
    },
    {
        "key": "call-003",
        "userName": "1st_SL_山本 里美",
        "skill": "プラン変更",
        "duration": 360,
        "direction": "O",
        "latest": (
            "O: いつもお世話になっております、山本です。\n"
            "C: はい、こんにちは。\n"
            "O: 新プランのご案内でお電話しました。\n"
            "C: 検討してみます、ありがとう。"
        ),
    },
]

# Utterances: 通話ID, 音声のチャンネル種類, 発言内容(最新版数), 開始時間(最新版数),
# CU の怒り/不満/ポジティブ/ネガティブ/エージェントスコア, OP の同様
UTT_ROWS = [
    # call-001: low dissatisfaction, finally positive
    ("call-001", "CU", "もしもし、料金プランの相談で電話したんですけど。", "00:00:05", 1.0, 2.0, 3.0, 2.0, 6.0, 0, 0, 5, 0, 6),
    ("call-001", "OP", "いつもお世話になっております。担当の山本です。", "00:00:10", 0, 0, 0, 0, 0, 1.0, 1.0, 5.0, 1.0, 7.0),
    ("call-001", "CU", "説明が分かりにくくて困っているんです。", "00:01:20", 2.0, 4.0, 1.0, 5.0, 4.0, 0, 0, 0, 0, 0),
    ("call-001", "OP", "大変申し訳ございません。順を追ってご説明します。", "00:01:35", 0, 0, 0, 0, 0, 0.5, 1.0, 4.0, 1.0, 6.5),
    ("call-001", "CU", "ありがとうございます、よく分かりました。", "00:08:45", 0.5, 1.0, 7.0, 1.0, 8.0, 0, 0, 0, 0, 0),
    # call-002: high dissatisfaction throughout
    ("call-002", "CU", "解約したいんですが手続きが面倒すぎる！", "00:00:10", 5.0, 7.0, 0.5, 7.0, 2.0, 0, 0, 0, 0, 0),
    ("call-002", "OP", "ご不便をおかけして申し訳ございません。", "00:00:20", 0, 0, 0, 0, 0, 1.0, 2.0, 3.0, 2.0, 5.0),
    ("call-002", "CU", "もう何度も同じ説明をさせられている。", "00:05:00", 6.0, 8.0, 0.5, 8.0, 1.5, 0, 0, 0, 0, 0),
    ("call-002", "OP", "確認させていただきます。少々お待ちください。", "00:05:30", 0, 0, 0, 0, 0, 1.0, 2.0, 3.0, 2.0, 5.0),
    ("call-002", "CU", "早くしてください、時間がないんです。", "00:10:00", 5.5, 7.5, 0.5, 7.5, 1.8, 0, 0, 0, 0, 0),
    # call-003: short positive call
    ("call-003", "OP", "いつもお世話になっております、山本です。", "00:00:05", 0, 0, 0, 0, 0, 0.5, 0.5, 6.0, 0.5, 7.5),
    ("call-003", "CU", "はい、こんにちは。", "00:00:10", 0.5, 0.5, 5.0, 1.0, 7.0, 0, 0, 0, 0, 0),
    ("call-003", "OP", "新プランのご案内でお電話しました。", "00:00:30", 0, 0, 0, 0, 0, 0.5, 0.5, 6.0, 0.5, 7.5),
    ("call-003", "CU", "検討してみます、ありがとう。", "00:05:00", 0.5, 1.0, 6.5, 1.0, 7.5, 0, 0, 0, 0, 0),
]


def calls_csv_bytes() -> bytes:
    """Return the per-call CSV encoded as utf-8-sig."""
    df = pd.DataFrame(CALL_ROWS)
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8-sig")


def utterances_csv_bytes() -> bytes:
    """Return the per-utterance CSV encoded as cp932."""
    columns = [
        "通話ID",
        "音声のチャンネル種類",
        "発言内容(最新版数)",
        "開始時間(最新版数)",
        "CUの怒り",
        "CUの不満",
        "CUのポジティブ",
        "CUのネガティブ",
        "CUのエージェントスコア",
        "OPの怒り",
        "OPの不満",
        "OPのポジティブ",
        "OPのネガティブ",
        "OPのエージェントスコア",
    ]
    df = pd.DataFrame(UTT_ROWS, columns=columns)
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("cp932")

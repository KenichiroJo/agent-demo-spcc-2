# Copyright 2026 DataRobot, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""In-memory session storage for SPCC uploads.

Each upload creates a fresh session containing the parsed dataframes and an
LLM evaluation cache. Sessions auto-expire after `ttl_seconds`.
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class SPCCSessionData:
    calls_df: pd.DataFrame
    utterances_df: pd.DataFrame
    aggregates_df: pd.DataFrame  # calls joined with max_dissatisfied / avg_agent_score
    match_rate: float
    created_at: float = field(default_factory=time.time)
    llm_cache: dict[str, dict[str, Any]] = field(default_factory=dict)


class SPCCSessionManager:
    """Thread-safe in-memory store of SPCC sessions with TTL cleanup."""

    def __init__(self, ttl_seconds: int = 24 * 60 * 60) -> None:
        self.ttl_seconds = ttl_seconds
        self._sessions: dict[str, SPCCSessionData] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self) -> None:
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

    async def create(self, data: SPCCSessionData) -> str:
        session_id = uuid.uuid4().hex
        async with self._lock:
            self._sessions[session_id] = data
        logger.info("SPCC session created: %s (calls=%d)", session_id, len(data.calls_df))
        return session_id

    async def get(self, session_id: str) -> SPCCSessionData | None:
        async with self._lock:
            data = self._sessions.get(session_id)
        if data and (time.time() - data.created_at) > self.ttl_seconds:
            await self.delete(session_id)
            return None
        return data

    async def delete(self, session_id: str) -> None:
        async with self._lock:
            self._sessions.pop(session_id, None)

    async def _cleanup_loop(self) -> None:
        try:
            while True:
                await asyncio.sleep(60 * 30)  # every 30 min
                now = time.time()
                expired: list[str] = []
                async with self._lock:
                    for sid, data in self._sessions.items():
                        if (now - data.created_at) > self.ttl_seconds:
                            expired.append(sid)
                    for sid in expired:
                        self._sessions.pop(sid, None)
                if expired:
                    logger.info("SPCC session cleanup expired %d sessions", len(expired))
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001
            logger.exception("SPCC cleanup loop crashed; will not restart")

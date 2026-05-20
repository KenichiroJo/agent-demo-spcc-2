# Copyright 2026 DataRobot, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""SPCC (Speech Processing Contact Center) emotion karte LLM evaluation API."""
from fastapi import APIRouter

from .endpoints import router as endpoints_router

spcc_router = APIRouter(prefix="/spcc", tags=["spcc"])
spcc_router.include_router(endpoints_router)

__all__ = ["spcc_router"]

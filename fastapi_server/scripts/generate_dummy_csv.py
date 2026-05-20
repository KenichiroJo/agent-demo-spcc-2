#!/usr/bin/env python3
"""Generate small dummy CSV files for SPCC local development.

Usage:
    cd fastapi_server
    uv run python scripts/generate_dummy_csv.py [output_dir]

Writes:
    {output_dir}/masked_dummy.csv      (utf-8-sig)
    {output_dir}/Recognition_dummy.csv (cp932)
"""
from __future__ import annotations

import sys
from pathlib import Path

# Allow running this script without installing the package
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(REPO_ROOT))

from tests.unit.spcc.fixtures import calls_csv_bytes, utterances_csv_bytes


def main(argv: list[str]) -> int:
    out_dir = Path(argv[1]) if len(argv) > 1 else Path.cwd()
    out_dir.mkdir(parents=True, exist_ok=True)
    calls_path = out_dir / "masked_dummy.csv"
    utt_path = out_dir / "Recognition_dummy.csv"
    calls_path.write_bytes(calls_csv_bytes())
    utt_path.write_bytes(utterances_csv_bytes())
    print(f"Wrote {calls_path}")
    print(f"Wrote {utt_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

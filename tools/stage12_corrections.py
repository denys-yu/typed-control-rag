"""Recompute the two corrected pilot summary figures from the analysis table.

Reads `results/pilot_analysis.jsonl` only. It changes no pilot record and opens
no run log; it exists so the figures in
`results/pilot_summary_corrections_v1.1.md` can be reproduced in one command.

    python tools/stage12_corrections.py
"""

from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from typed_rag import hotpotqa
from typed_rag.config import load_config

ANALYSIS_FILENAME = "pilot_analysis.jsonl"


def compute(config) -> dict:
    rows = hotpotqa.read_jsonl(config.paths["results"] / ANALYSIS_FILENAME)
    completed = [r for r in rows if r["record_status"] == "completed"]

    retries = [r for r in completed if r.get("retried")]
    post_retry = collections.Counter(r["post_retry_reviewed_state"] for r in retries)

    cells: dict[tuple, list[dict]] = collections.defaultdict(list)
    for row in completed:
        cells[(row["question_id"], row["condition"], row["branch"])].append(row)
    complete_cells = [v for v in cells.values() if len(v) == 5]
    sizes = collections.Counter(len(v) for v in cells.values())

    return {
        "rows": len(rows),
        "completed": len(completed),
        "retries": len(retries),
        "post_retry_states": dict(sorted(post_retry.items())),
        "cells": len(cells),
        "cell_size_histogram": {str(k): v for k, v in sorted(sizes.items())},
        "complete_cells": len(complete_cells),
        "complete_cells_homogeneous_terminal_outcome": sum(
            1 for v in complete_cells if len({x["terminal_outcome"] for x in v}) == 1
        ),
        "complete_cells_homogeneous_support_label": sum(
            1 for v in complete_cells if len({x["answer_support"] for x in v}) == 1
        ),
    }


def main() -> int:
    result = compute(load_config())
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

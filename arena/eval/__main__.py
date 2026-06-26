from __future__ import annotations

import argparse
import json
from pathlib import Path

from arena.eval.runner import run_eval


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the MCP-Sentinel deterministic arena evaluation suite.")
    parser.add_argument("--out", type=Path, default=Path("runs") / "arena-eval")
    args = parser.parse_args()
    report = run_eval(args.out)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

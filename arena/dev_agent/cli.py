from __future__ import annotations

import argparse
import json
from pathlib import Path

from arena.dev_agent.agent import DevAgent
from arena.dev_agent.scenarios import SCENARIO_TASKS


def main() -> int:
    args = _parse_args()
    task = args.task or SCENARIO_TASKS[args.scenario]
    agent = DevAgent(force_offline=args.offline, artifacts_root=args.out, proxy_mode=args.proxy_mode)
    result = agent.run(task, scenario_id=args.scenario)
    print(json.dumps(result.to_summary(), ensure_ascii=False, indent=2))
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the local MCP-Sentinel TP-00 development-agent arena.")
    parser.add_argument("--scenario", choices=sorted(SCENARIO_TASKS), required=True)
    parser.add_argument("--task", help="Optional custom task text. The scenario still selects the deterministic route.")
    parser.add_argument("--offline", action="store_true", help="Force deterministic offline LLM planning mode.")
    parser.add_argument("--proxy-mode", choices=("observe", "enforce"), default="observe", help="Sentinel proxy mode.")
    parser.add_argument("--out", type=Path, default=Path("runs") / "arena-base", help="Arena output root.")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())

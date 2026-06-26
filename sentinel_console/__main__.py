from __future__ import annotations

import argparse
from pathlib import Path

from sentinel_console.generator import generate_console


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a static MCP-Sentinel review console.")
    parser.add_argument("--input", type=Path, required=True, help="Arena run or arena-eval output directory.")
    parser.add_argument("--out", type=Path, default=Path("runs") / "sentinel-console")
    args = parser.parse_args()
    output = generate_console(args.input, args.out)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

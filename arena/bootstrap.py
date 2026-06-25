"""Source-layout bootstrap for direct `python -m arena...` runs."""

from __future__ import annotations

import sys
from pathlib import Path


def setup_paths() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    for rel_path in (
        "auto_attack_system/src",
        "auto_defense_system/src",
        "auto_evaluation_system/src",
        "sdk/python/src",
    ):
        source_path = str(repo_root / rel_path)
        if source_path not in sys.path:
            sys.path.insert(0, source_path)

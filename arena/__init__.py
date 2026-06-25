"""Local MCP-Sentinel arena package."""

from arena.bootstrap import setup_paths

setup_paths()

from arena.dev_agent.agent import DevAgent
from arena.dev_agent.models import ArenaEvent, ArenaRunResult

__all__ = ["ArenaEvent", "ArenaRunResult", "DevAgent"]

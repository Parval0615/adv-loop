from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal


ArenaEventType = Literal["llm_inference", "tool_call", "resource_read", "sub_dispatch"]
ArenaActor = Literal["dev_agent", "file_mcp", "network_mcp", "worker_agent"]


@dataclass(frozen=True)
class ArenaEvent:
    event_id: str
    trace_id: str
    parent_id: str | None
    event_type: ArenaEventType
    actor: ArenaActor
    name: str
    arguments: dict[str, Any]
    result: Any
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ArenaRunResult:
    scenario_id: str
    final_answer: str
    events: list[ArenaEvent]
    artifacts_dir: Path
    llm_mode: str
    sentinel_decisions: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_summary(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "final_answer": self.final_answer,
            "artifacts_dir": str(self.artifacts_dir),
            "llm_mode": self.llm_mode,
            "event_count": len(self.events),
            "event_types": [event.event_type for event in self.events],
            "tool_calls": [
                event.name for event in self.events if event.event_type == "tool_call"
            ],
            "sentinel_decision_count": len(self.sentinel_decisions),
            "metadata": self.metadata,
        }

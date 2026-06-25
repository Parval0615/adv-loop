from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class SentinelContext:
    task: str
    scenario_id: str
    history: list[dict[str, Any]] = field(default_factory=list)
    normalizations: list[dict[str, Any]] = field(default_factory=list)
    resource_reads: list[dict[str, Any]] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    sub_dispatches: list[dict[str, Any]] = field(default_factory=list)

    def snapshot(self) -> dict[str, Any]:
        return deepcopy(asdict(self))

    def record_tool_call(
        self,
        *,
        name: str,
        arguments: dict[str, Any],
        result: Any,
        decision: dict[str, Any],
        executed: bool,
    ) -> None:
        self.tool_calls.append(
            {
                "name": name,
                "arguments": deepcopy(arguments),
                "result": deepcopy(result),
                "decision": deepcopy(decision),
                "executed": executed,
            }
        )

    def record_normalization(self, normalized_field: dict[str, Any]) -> None:
        self.normalizations.append(deepcopy(normalized_field))

    def record_resource_read(self, *, source: str, arguments: dict[str, Any], result: Any) -> None:
        self.resource_reads.append(
            {
                "source": source,
                "arguments": deepcopy(arguments),
                "result": deepcopy(result),
            }
        )

    def record_sub_dispatch(self, *, task: str, payload: dict[str, Any], result: Any) -> None:
        self.sub_dispatches.append(
            {
                "task": task,
                "payload_summary": _summarize_payload(payload),
                "result": deepcopy(result),
            }
        )


def _summarize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(value, str):
            summary[key] = {
                "type": "str",
                "length": len(value),
                "preview": value[:32],
            }
        else:
            summary[key] = {"type": type(value).__name__, "value": deepcopy(value)}
    return summary

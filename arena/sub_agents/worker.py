from __future__ import annotations

from typing import Any


class WorkerAgent:
    def __init__(self, name: str = "worker_agent") -> None:
        self.name = name
        self.received_tasks: list[dict[str, Any]] = []

    def dispatch(self, task: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        message = {"task": task, "payload": payload or {}}
        self.received_tasks.append(message)
        return {
            "worker": self.name,
            "accepted": True,
            "received_keys": sorted(message["payload"].keys()),
        }

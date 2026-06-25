from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from arena.dev_agent.models import ArenaActor, ArenaEvent, ArenaEventType


class EventRecorder:
    def __init__(self, trace_id: str | None = None) -> None:
        self.trace_id = trace_id or str(uuid4())
        self._counter = 0
        self.events: list[ArenaEvent] = []

    def add(
        self,
        *,
        event_type: ArenaEventType,
        actor: ArenaActor,
        name: str,
        arguments: dict[str, Any] | None = None,
        result: Any = None,
        parent_id: str | None = None,
    ) -> ArenaEvent:
        self._counter += 1
        event = ArenaEvent(
            event_id=f"evt-{self._counter:04d}",
            trace_id=self.trace_id,
            parent_id=parent_id,
            event_type=event_type,
            actor=actor,
            name=name,
            arguments=arguments or {},
            result=result,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self.events.append(event)
        return event

from __future__ import annotations

from auto_evaluation_system.events.models import StepEvent
from auto_evaluation_system.sandbox.session import SandboxSession


class AutoGenBackend:
    framework = "autogen"

    def run(self, session: SandboxSession) -> list[StepEvent]:
        raise NotImplementedError("AutoGen backend is a scaffold only.")

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from auto_evaluation_system.events.models import MemoryOpPayload
from auto_attack_system.injectors import InjectionEvent
from auto_attack_system.injectors.goal_perturbation import GoalPerturbationInjector
from auto_attack_system.injectors.tool_tampering import ToolTamperingProxy
from auto_evaluation_system.memory import InMemoryMemoryStore
from auto_evaluation_system.sandbox.config import ScenarioConfig
from auto_evaluation_system.sandbox.llm.vcr_client import VCRCachedLLMClient
from auto_evaluation_system.sandbox.tools.registry import ToolRegistry
from auto_evaluation_system.telemetry import TelemetryStepEmitter


@dataclass
class SandboxSession:
    config: ScenarioConfig
    session_id: str
    emitter: TelemetryStepEmitter
    tools: Any
    llm: VCRCachedLLMClient
    memory_store: InMemoryMemoryStore
    injection_events: list[InjectionEvent] = field(default_factory=list)
    pending_memory_ops: list[MemoryOpPayload] = field(default_factory=list)
    pending_step_injections: list[InjectionEvent] = field(default_factory=list)

    @property
    def memory_namespace(self) -> str:
        if self.config.memory:
            return self.config.memory.namespace
        return f"session-{self.session_id}"


class SandboxEnvironment:
    """Creates isolated sandbox sessions with no shared mutable state."""

    def create_session(self, config: ScenarioConfig) -> SandboxSession:
        active_config, goal_result = GoalPerturbationInjector().apply_config(config)
        emitter = TelemetryStepEmitter(max_steps=active_config.runner.max_steps)
        tools = ToolRegistry(mode=config.tools.mode)
        tools.register_defaults()
        if (
            active_config.injection.mode == "controlled"
            and active_config.injection.kind == "tool_tampering"
        ):
            tools = ToolTamperingProxy(tools, active_config)
        llm = VCRCachedLLMClient(config=active_config, session_id=str(uuid4()))
        session = SandboxSession(
            config=active_config,
            session_id=str(uuid4()),
            emitter=emitter,
            tools=tools,
            llm=llm,
            memory_store=InMemoryMemoryStore(),
        )
        if goal_result.applied:
            session.injection_events.extend(goal_result.events)
            session.pending_step_injections.extend(goal_result.events)
        return session

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from evasion_shield import NormalizedField, normalize_text
from injection_radar import injection_radar_stage
from intent_aligner import intent_aligner_stage
from policy_dsl import policy_dsl_stage
from sentinel_proxy.context import SentinelContext
from sentinel_proxy.models import DecisionValue, InterceptDecision, InterceptRequest
from trace_dag import trace_dag_stage

PipelineStage = Callable[[InterceptRequest, SentinelContext], InterceptDecision]


class SentinelPipeline:
    def __init__(self, stages: list[tuple[str, PipelineStage]] | None = None) -> None:
        self.stages = stages or default_stages()

    def evaluate(self, request: InterceptRequest, context: SentinelContext) -> InterceptDecision:
        stage_decisions: list[dict[str, Any]] = []
        selected = InterceptDecision("allow", "pipeline", "all sentinel stages allowed")
        first_ask: InterceptDecision | None = None
        first_block: InterceptDecision | None = None

        for stage_name, stage in self.stages:
            decision = stage(request, context)
            normalized = InterceptDecision(
                decision=decision.decision,
                stage=decision.stage or stage_name,
                reason=decision.reason,
                risk_level=decision.risk_level,
                metadata=decision.metadata,
            )
            stage_decisions.append(normalized.to_dict())

            if normalized.decision == "block" and first_block is None:
                first_block = normalized
            if normalized.decision == "ask" and first_ask is None:
                first_ask = normalized

        if first_block is not None:
            selected = first_block
        elif first_ask is not None:
            selected = first_ask

        return InterceptDecision(
            decision=selected.decision,
            stage=selected.stage,
            reason=selected.reason,
            risk_level=selected.risk_level,
            metadata={**selected.metadata, "stage_decisions": stage_decisions},
        )


class ToolNameDecisionStage:
    def __init__(
        self,
        decisions: dict[str, DecisionValue],
        *,
        stage_name: str = "test_stub",
        reason: str = "test stub decision",
    ) -> None:
        self.decisions = decisions
        self.stage_name = stage_name
        self.reason = reason

    def __call__(self, request: InterceptRequest, context: SentinelContext) -> InterceptDecision:
        decision = self.decisions.get(request.name, "allow")
        return InterceptDecision(
            decision=decision,
            stage=self.stage_name,
            reason=f"{self.reason}: {request.name}",
            risk_level="test" if decision != "allow" else "none",
        )


def default_stages() -> list[tuple[str, PipelineStage]]:
    return [
        ("normalizer", _normalizer_stage),
        ("injection_radar", injection_radar_stage),
        ("intent_aligner", intent_aligner_stage),
        ("policy_dsl", policy_dsl_stage),
        ("trace_dag", trace_dag_stage),
    ]


def _allow_stage(stage_name: str) -> PipelineStage:
    def stage(request: InterceptRequest, context: SentinelContext) -> InterceptDecision:
        return InterceptDecision(
            decision="allow",
            stage=stage_name,
            reason="TP-01 skeleton stage allows by default",
        )

    return stage


def _normalizer_stage(request: InterceptRequest, context: SentinelContext) -> InterceptDecision:
    normalized_fields: list[dict[str, Any]] = []
    for field_path, value in _iter_text_fields(request.arguments, "request.arguments"):
        normalized_fields.append(_record_normalized_field(context, "request", field_path, value))

    normalized_fields.append(_record_normalized_field(context, "context", "task", context.task))
    for index, item in enumerate(context.history[-3:]):
        content = item.get("content")
        if isinstance(content, str):
            normalized_fields.append(
                _record_normalized_field(context, "context.history", f"history[-3+{index}].content", content)
            )

    tagged = [field for field in normalized_fields if field["result"]["evasion_tags"]]
    return InterceptDecision(
        decision="allow",
        stage="normalizer",
        reason=f"normalized {len(normalized_fields)} text fields",
        metadata={
            "normalized_field_count": len(normalized_fields),
            "tagged_field_count": len(tagged),
            "tagged_fields": tagged,
        },
    )


def _record_normalized_field(
    context: SentinelContext,
    source: str,
    field_path: str,
    value: str,
) -> dict[str, Any]:
    normalized = NormalizedField(source=source, field_path=field_path, result=normalize_text(value)).to_dict()
    context.record_normalization(normalized)
    return normalized


def _iter_text_fields(value: Any, prefix: str):
    if isinstance(value, str):
        yield prefix, value
        return
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _iter_text_fields(child, f"{prefix}.{key}")
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            yield from _iter_text_fields(child, f"{prefix}[{index}]")

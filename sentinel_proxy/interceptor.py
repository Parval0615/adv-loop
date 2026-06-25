from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from typing import Any

from sentinel_proxy.context import SentinelContext
from sentinel_proxy.models import InterceptDecision, InterceptRequest, InterceptResult, ProxyMode
from sentinel_proxy.pipeline import SentinelPipeline


class SentinelInterceptor:
    def __init__(
        self,
        *,
        context: SentinelContext,
        mode: ProxyMode = "observe",
        pipeline: SentinelPipeline | None = None,
    ) -> None:
        if mode not in ("observe", "enforce"):
            raise ValueError(f"unknown sentinel proxy mode: {mode}")
        self.context = context
        self.mode = mode
        self.pipeline = pipeline or SentinelPipeline()
        self.decision_records: list[dict[str, Any]] = []

    def intercept(self, request: InterceptRequest, execute: Callable[[], Any]) -> InterceptResult:
        context_before = self.context.snapshot()
        decision = self.pipeline.evaluate(request, self.context)
        context_after = self.context.snapshot()

        executed = self.mode == "observe" or decision.decision == "allow"
        if executed:
            response = execute()
        elif decision.decision == "ask":
            response = {"requires_confirmation": True, "reason": decision.reason}
        else:
            response = {"blocked": True, "reason": decision.reason}

        result = InterceptResult(executed=executed, decision=decision, response=response)
        self._record_decision(request, context_before, context_after, result)
        return result

    def decision_summary(self, decision: InterceptDecision, *, executed: bool) -> dict[str, Any]:
        return {
            "decision": decision.decision,
            "stage": decision.stage,
            "reason": decision.reason,
            "risk_level": decision.risk_level,
            "executed": executed,
        }

    def _record_decision(
        self,
        request: InterceptRequest,
        context_before: dict[str, Any],
        context_after: dict[str, Any],
        result: InterceptResult,
    ) -> None:
        self.decision_records.append(
            {
                "mode": self.mode,
                "request": request.to_dict(),
                "context": deepcopy(context_after),
                "context_before": deepcopy(context_before),
                "decision": result.decision.to_dict(),
                "executed": result.executed,
                "response": deepcopy(result.response),
            }
        )

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from dataclasses import replace
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
        self._intercept_counter = 0

    def intercept(self, request: InterceptRequest, execute: Callable[[], Any]) -> InterceptResult:
        if request.intercept_id is None:
            self._intercept_counter += 1
            request = replace(request, intercept_id=f"int-{self._intercept_counter:04d}")
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

        result = InterceptResult(
            intercept_id=request.intercept_id or "",
            executed=executed,
            decision=decision,
            response=response,
        )
        self._record_decision(request, context_before, context_after, result)
        return result

    def decision_summary(
        self,
        decision: InterceptDecision,
        *,
        executed: bool,
        intercept_id: str | None = None,
    ) -> dict[str, Any]:
        return {
            "intercept_id": intercept_id,
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
                "intercept_id": result.intercept_id,
                "trace_id": self.context.trace_id,
                "mode": self.mode,
                "request": request.to_dict(),
                "context": deepcopy(context_after),
                "context_before": deepcopy(context_before),
                "decision": result.decision.to_dict(),
                "executed": result.executed,
                "response": deepcopy(result.response),
            }
        )

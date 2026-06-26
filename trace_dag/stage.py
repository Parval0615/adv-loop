from __future__ import annotations

from sentinel_proxy.context import SentinelContext
from sentinel_proxy.models import InterceptDecision, InterceptRequest


def trace_dag_stage(request: InterceptRequest, context: SentinelContext) -> InterceptDecision:
    trace_ref = {
        "trace_id": context.trace_id,
        "intercept_id": request.intercept_id,
        "request_name": request.name,
        "event_type": request.event_type,
        "actor": request.actor,
        "tool_call_index": len(context.tool_calls) + 1,
    }
    context.record_trace_ref(trace_ref)
    return InterceptDecision(
        decision="allow",
        stage="trace_dag",
        reason="recorded trace hook reference",
        metadata={"trace_ref": trace_ref},
    )

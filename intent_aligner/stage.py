from __future__ import annotations

from intent_aligner.aligner import evaluate_alignment
from sentinel_proxy.context import SentinelContext
from sentinel_proxy.models import InterceptDecision, InterceptRequest


def intent_aligner_stage(request: InterceptRequest, context: SentinelContext) -> InterceptDecision:
    verdict = evaluate_alignment(request, context)
    verdict_payload = verdict.to_dict()
    context.record_intent_verdict(verdict_payload)
    return InterceptDecision(
        decision="allow",
        stage="intent_aligner",
        reason="request is aligned with inferred intent" if verdict.aligned else verdict.rationale,
        risk_level="none" if verdict.aligned else "medium",
        metadata={"verdict": verdict_payload},
    )

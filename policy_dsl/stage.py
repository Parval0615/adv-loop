from __future__ import annotations

from policy_dsl.engine import PolicyEngine
from sentinel_proxy.context import SentinelContext
from sentinel_proxy.models import InterceptDecision, InterceptRequest


DEFAULT_ENGINE = PolicyEngine()


def policy_dsl_stage(request: InterceptRequest, context: SentinelContext) -> InterceptDecision:
    policy_decision = DEFAULT_ENGINE.evaluate(request, context)
    payload = policy_decision.to_dict()
    context.record_policy_decision(payload)
    return InterceptDecision(
        decision=policy_decision.decision,
        stage="policy_dsl",
        reason=policy_decision.reason,
        risk_level=policy_decision.risk_level,
        metadata={"policy_decision": payload},
    )

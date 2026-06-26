from __future__ import annotations

from injection_radar.radar import scan_request
from sentinel_proxy.context import SentinelContext
from sentinel_proxy.models import InterceptDecision, InterceptRequest


def injection_radar_stage(request: InterceptRequest, context: SentinelContext) -> InterceptDecision:
    findings = scan_request(request, context)
    for finding in findings:
        context.record_injection_finding(finding.to_dict())

    return InterceptDecision(
        decision="allow",
        stage="injection_radar",
        reason=f"recorded {len(findings)} injection finding(s)",
        risk_level="medium" if findings else "none",
        metadata={"finding_count": len(findings), "findings": [finding.to_dict() for finding in findings]},
    )

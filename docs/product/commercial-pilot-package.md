# Commercial Pilot Package

This package is the first private single-tenant delivery bundle for enterprise
agent security evaluation. It uses the local e-commerce customer service /
shopping guide agent as the first enterprise agent under test.

## Delivery Bundle

| Artifact | Path / command | Purpose |
|---|---|---|
| Python SDK | `sdk/python/src/agent_security_sdk/` | White-box adapter integration |
| Hosted API | `auto_evaluation_system.product_api.app.create_app` | Optional private API service |
| OpenAPI contract | `docs/api/openapi.yaml` | Enterprise API review and client generation |
| Demo command | `python -m auto_evaluation_system.product_api.demo` after editable install, or set `PYTHONPATH` from a source checkout | One-command local pilot run |
| Report JSON | `agent-security-report-v0.1.json` | Machine-readable security report |
| Dashboard | `agent-security-dashboard-v0.1.html` | Local interactive executive / engineer view |
| Retest comparison | `agent-security-comparison-v0.1.json` | Before / after remediation evidence |
| Readiness audit | `docs/product/product-readiness-audit.md` | Product audit and regression evidence |

## Pilot Script

1. Register the enterprise demo agent with `adapter_type="ecommerce_demo"`.
2. Select `ecommerce-security-v0.1`.
3. Run the full benchmark or a pilot preset:
   `customer_service`, `shopping_guide`, or `merchant_operations`.
4. Review the JSON report, Markdown report, and interactive dashboard.
5. Apply remediation in the agent, guard, policy, or business rule layer.
6. Run evaluation again and generate a retest comparison report.

## Acceptance Talk Track

- The product evaluates clean and controlled business flows, not only one-off
  prompt strings.
- The report ties each finding to business impact, scenario evidence, guard
  decisions, trajectory references, audit refs, and remediation guidance.
- The demo uses mock store data only: no real Taobao, no real payments, no real
  enterprise records, and no external attack targets.
- The current audited demo reaches `OVERALL_SCORE=100` on
  `ecommerce-security-v0.1`.

## Private Deployment Boundary

- Single tenant per deployment.
- Local artifact root defaults to `runs/product/`.
- All artifacts remain inside the private environment unless the enterprise
  exports them.
- FastAPI is optional; core evaluation and reports do not depend on a web
  server.
- Hosted API contract is stable enough for a pilot, but auth and SaaS account
  management are not implemented in this package.

## Market Parity Checklist

| Capability | Current state | Next market step |
|---|---|---|
| SDK integration | Python SDK MVP | Add JS/TS SDK and framework examples |
| Hosted API | Optional FastAPI adapter + OpenAPI | Add auth, API keys, and request quotas |
| Scenario library | 16 e-commerce clean/control pairs | Expand to 24+ controlled scenarios |
| Business simulator | Mock Taobao-like store | Add richer catalog, campaigns, reviews, logistics states |
| Report | JSON + Markdown | Add PDF export and signed report bundle |
| Dashboard | Local interactive HTML | Add private web console with login and history |
| Retest | Before / after comparison | Add remediation workflow and CI gate |
| Audit | Hash-chain events and audit refs | Add artifact signing and retention policy |

## Next Pilot Risks

- A real enterprise agent may expose only a black-box HTTP endpoint, reducing
  tool-call observability.
- Custom business tools require enterprise-provided tool specs and business
  rules before high-risk action evaluation can be accurate.
- Production data must be sanitized or mocked before evaluation.
- Any real-time guard deployment needs separate latency, availability, rollback,
  and legal approval gates.

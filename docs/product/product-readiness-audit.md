# Product Readiness Audit

Date: 2026-06-09

Scope: local e-commerce agent, SDK adapter, product API service, attack pack,
pilot presets, report generation, dashboard artifact, retest comparison,
business rules, guard wiring, and regression gates.

## Audit Result

The private single-tenant MVP is ready as a local enterprise pilot package. It
does not connect to real Taobao, real payment systems, real enterprise data, or
external attack targets.

## Verified Product Surface

- E-commerce agent entry:
  `auto_defense_system.ecommerce_agent.invoke_ecommerce_agent(...)`
- SDK adapter:
  `agent_security_sdk.EcommerceEnterpriseAdapter`
- Product service:
  `auto_evaluation_system.product_api.ProductEvaluationService`
- Optional Hosted API:
  `auto_evaluation_system.product_api.app.create_app`
- Demo:
  `python -m auto_evaluation_system.product_api.demo` after editable install, or
  `$env:PYTHONPATH="auto_evaluation_system/src;auto_defense_system/src;sdk/python/src"; python -m auto_evaluation_system.product_api.demo`
- Reports:
  `agent-security-report-v0.1`, local interactive `agent-security-dashboard-v0.1.html`,
  `agent-security-comparison-v0.1`

## Fixed During Audit

| Area | Finding | Fix |
|---|---|---|
| Structured tool output | `tool_calls.result` and some `tool_calls.arguments` could retain raw sensitive text while `answer` was masked. | Masked tool call arguments, results, blocked reasons, and refund reasons before returning or auditing. |
| SDK trajectory | SDK trajectory stored raw user message text. | `EcommerceEnterpriseAdapter` now records masked message text while still sending the original message to the agent. |
| PII evaluation | Product service counted user input PII as output leakage. | PII leakage check now inspects only agent output fields: answer, tool calls, business events, and audit events. |
| Artifact path safety | tenant, agent, and report ids were used in local artifact paths without explicit component validation. | Added safe path component validation before registration, report lookup, tenant storage, and comparison. |
| Audit evidence | Report artifacts had empty `audit_refs` even when audit events existed in trajectories. | Evaluation service now writes `audit-events.json` and links it from `artifacts.audit_refs`. |
| Recommendation goal drift | The e-commerce guide allowed commission-biased recommendation requests. | Added Goal Guard bridge for recommendation goal drift and audit logging. |

## Business Rule Audit

- Server-side order amount is recomputed from cart contents and current product
  prices.
- Stock is checked on cart add/update and decremented on order creation.
- Address ownership is checked before order creation.
- Order ownership is checked before status, payment, refund, and ticket actions.
- Payment is mock-only and must equal server-side order amount.
- Duplicate refund requests are blocked.
- Merchant price and stock tools require merchant/admin role and shop ownership.
- Unknown tools and role mismatches default to block.

## Attack and Evaluation Audit

- `ecommerce-security-v0.1` attack pack loads with 16 clean/control pairs.
- Pilot presets reference only existing scenario ids.
- Product evaluation generates trajectories, audit refs, JSON report, Markdown
  report, and static dashboard artifact.
- Retest comparison reports score delta, risk level change, finding buckets, and
  scenario deltas.
- The private demo currently completes with `OVERALL_SCORE=100` after audit
  fixes.

## Regression Results

- `python -m pytest auto_defense_system/tests/test_ecommerce_agent.py -q`:
  25 passed.
- `python -m pytest auto_defense_system/tests -q`: 72 passed, 2 warnings.
- `python -m pytest auto_evaluation_system/tests -q`: 114 passed, 1 skipped.
- `python -m pytest auto_evaluation_system/tests/product -q`: 18 passed,
  1 skipped.
- `python -m pytest -q`: 215 passed, 1 skipped, 2 warnings.
- `git diff --check`: passed; only Windows CRLF notices.

## Remaining Product Boundary

- FastAPI is optional and skipped when product dependencies are not installed.
- Dashboard is a local interactive HTML artifact, not a SaaS console.
- The e-commerce agent is deterministic and mock-only; it is not a real Taobao
  integration or real LLM shopping assistant.
- Multi-tenant SaaS isolation, billing, user management, and PDF export remain
  future product packages.

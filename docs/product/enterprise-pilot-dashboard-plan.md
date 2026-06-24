# Enterprise Pilot and Dashboard Plan

This plan turns the private e-commerce evaluation MVP into a pilot-ready
product package. It keeps the first deployment private and single-tenant, and
it does not connect to real Taobao, real payment systems, real enterprise data,
or external attack targets.

## Pilot Scope

The first pilot uses the existing local e-commerce agent as the enterprise
customer service and shopping guide agent.

| Pilot agent | Current adapter | Primary business flows | Demo data |
|---|---|---|---|
| Customer service agent | `EcommerceEnterpriseAdapter` | order status, logistics, refund, support ticket | buyer, another buyer, historical order, support ticket |
| Shopping guide agent | `EcommerceEnterpriseAdapter` | search, detail, recommendation, cart, checkout, coupon | product catalog, shop metadata, coupon fixture |
| Merchant operations agent | same adapter with merchant role | price update, stock update, ownership checks | merchant-owned shop and product |

The first pilot does not require a new external agent framework. The enterprise
integration surface is still exercised because the evaluation runner talks to
the agent only through the SDK adapter contract.

## Demo Data Boundary

- Use only `create_demo_store()` fixtures.
- Use mock buyer, merchant, admin, product, coupon, order, payment, refund, and
  support ticket records.
- Keep payment and refund state changes local and deterministic.
- Mask phone, address, and payment token-like values before report output.
- Store local artifacts under `runs/product/<tenant_id>/`.

## Evaluation Package

The pilot benchmark remains `ecommerce-security-v0.1`.

Required evidence for each scenario:

- clean trajectory
- controlled trajectory
- expected decision and actual decision
- guard, tool, business, and audit events when available
- business impact label
- remediation recommendation when a controlled attack succeeds or clean flow is
  blocked

## Local Interactive Dashboard v0.1

The first dashboard is a local HTML artifact generated beside the JSON and
Markdown report. It is dependency-free and supports local filtering without a
server.

Information architecture:

| View | Content |
|---|---|
| Overview | tenant, agent, benchmark, overall score, risk level |
| Metrics | attack success rate, false positive rate, scenario pass count |
| Findings | severity, scenario, title, business impact, recommendation |
| Scenario table | clean decision, expected decision, actual decision, pass/fail |
| Evidence | trajectory file references and report artifact paths |
| Business impact | failed impact labels grouped by affected business risk |

Explicitly out of scope for dashboard v0.1:

- login or user management
- SaaS multi-tenant console
- report editing
- real-time websocket status
- PDF export
- remediation workflow automation

## Pilot Delivery Checklist

- One command runs the private demo and writes JSON, Markdown, and HTML report
  artifacts.
- The report contains no raw phone numbers, addresses, or payment token values.
- The dashboard can be opened directly from disk without a server.
- Product docs explain SDK integration, optional Hosted API integration, local
  artifact storage, and no-real-data boundaries.
- Regression tests cover the e-commerce agent, product SDK, attack pack,
  service, report generator, demo, and dashboard artifact.

## Next Task Packages

| Package | Goal | Acceptance |
|---|---|---|
| `PROD12 - Read-only Dashboard Artifact` | Generate static HTML dashboard from `agent-security-report-v0.1` and include its path in report artifacts. | dashboard tests pass and private demo writes HTML |
| `PROD13 - Pilot Sample Expansion` | Add named customer service, shopping guide, and merchant operations pilot presets without new real integrations. | service can run selected pilot preset scenarios |
| `PROD14 - Retest Comparison Report` | Compare two completed reports for before/after remediation evidence. | comparison fixture shows score and finding delta |
| `PROD15 - Product Readiness Gate` | Re-run full product, defense, and repo regression and update handoff docs. | `pytest -q` and product doc scans pass |

## Implemented Preset IDs

- `customer_service`
- `shopping_guide`
- `merchant_operations`

These presets are stored in
`auto_evaluation_system/configs/scenarios/ecommerce/pilot-presets-v0.1.yaml`.

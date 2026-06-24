# Enterprise Integration MVP

This productization track turns the local e-commerce agent into a private,
single-tenant enterprise agent security evaluation MVP.

## Deployment Boundary

- Private single-tenant deployment.
- Local artifacts are written under `runs/product/`.
- No real Taobao integration.
- No real payment execution.
- No real external attack target.

## SDK Integration

The first SDK adapter wraps the local e-commerce customer guide agent:

```python
from agent_security_sdk import EcommerceEnterpriseAdapter

adapter = EcommerceEnterpriseAdapter()
turn = adapter.send_message("buyer_001", "搜索 耳机", {"role": "buyer"})
trajectory = adapter.export_trajectory()
```

## Hosted API

The FastAPI adapter is optional. Install product dependencies before serving:

```powershell
pip install -e ".[product]"
uvicorn auto_evaluation_system.product_api.app:create_app --factory
```

Retest comparison is available through `POST /v1/comparisons` with
`before_report_id` and `after_report_id`.

The static API contract is tracked in [`../api/openapi.yaml`](../api/openapi.yaml).

## Private Demo

After `pip install -e ".[dev]"`, run:

```powershell
python -m auto_evaluation_system.product_api.demo
```

From a source checkout without editable install, set the local source path:

```powershell
$env:PYTHONPATH="auto_evaluation_system/src;auto_defense_system/src;sdk/python/src"; python -m auto_evaluation_system.product_api.demo
```

The demo registers the e-commerce guide agent, runs `ecommerce-security-v0.1`,
and writes JSON, Markdown, and static HTML dashboard reports to
`runs/product/`.

The same demo helper can run a specific pilot preset:

```python
from auto_evaluation_system.product_api.demo import run_private_ecommerce_demo

run_private_ecommerce_demo(pilot_preset="customer_service")
```

## Pilot Presets

`EvaluationRequest.pilot_preset` selects a curated scenario subset:

| Preset | Business role | Coverage |
|---|---|---|
| `customer_service` | Customer service agent | order ownership, logistics, refund, support injection, PII masking |
| `shopping_guide` | Shopping guide agent | recommendation goal drift, checkout payment amount integrity, output masking |
| `merchant_operations` | Merchant operations agent | merchant price and stock authorization |

If `scenarios` is provided explicitly, it overrides the preset scenario list.

## Local Dashboard Artifact

The first dashboard is generated as
`agent-security-dashboard-v0.1.html` beside the report JSON. It is a local,
interactive artifact with no web server dependency. It supports local filtering
by severity, scenario status, and scenario/finding text, and it includes
trajectory and audit evidence references.

## Retest Comparison

After an enterprise fixes guard or tool policy issues, compare two completed
reports:

```python
from auto_evaluation_system.product_api import ProductEvaluationService

service = ProductEvaluationService()
comparison = service.compare_reports("eval_before", "eval_after")
```

This writes `agent-security-comparison-v0.1.json` and Markdown artifacts with
score delta, risk-level change, resolved findings, new findings, persisted
findings, and scenario deltas.

## Pilot Plan

The enterprise pilot and dashboard delivery boundary is tracked in
[`enterprise-pilot-dashboard-plan.md`](./enterprise-pilot-dashboard-plan.md).
The latest readiness audit is tracked in
[`product-readiness-audit.md`](./product-readiness-audit.md).
The commercial pilot bundle is tracked in
[`commercial-pilot-package.md`](./commercial-pilot-package.md).
The final handoff is tracked in [`final-handoff.md`](./final-handoff.md).

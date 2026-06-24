# Auto Defense System

Runtime defense package for the integrated AI security project.

This directory currently preserves the existing RAG / agent defense code and exposes
the Phase 4 entry points for guard and policy work. Legacy project notes remain in
`legacy_README.md`; new task packages should use this README and `PROGRESS.md` as
the current handoff source.

## Phase 4 Entry Points

| Area | Path | Current status |
|------|------|----------------|
| Input Guard / Firewall | `src/auto_defense_system/security/firewall/` | smoke-covered |
| Output Guard | `src/auto_defense_system/security/output/filter.py` | smoke-covered |
| Runtime Policy Engine | `src/auto_defense_system/security/policy/engine.py` | smoke-covered |
| Tool Integrity | `src/auto_defense_system/security/integrity.py` | existing candidate |
| Tool Guard | `src/auto_defense_system/security/tool_guard.py` | smoke-covered contract |
| Audit / Traceability | `src/auto_defense_system/security/audit.py` | smoke-covered |
| Memory Guard | `src/auto_defense_system/security/memory_guard.py` | smoke-covered contract |
| Goal Guard | `src/auto_defense_system/security/goal_guard.py` | smoke-covered contract |
| Agent wiring | `src/auto_defense_system/agent/` | existing integration surface |
| E-commerce Agent MVP | `src/auto_defense_system/ecommerce_agent/` | clean / refusal covered |

## Current Smoke Test

```powershell
python -m pytest auto_defense_system/tests -q
```

The current smoke suite covers:

- config import without real API keys
- Input Guard / Firewall baseline:
  - malicious prompt injection is blocked by `check_malicious_input(...)`
  - benign input is allowed by the local input guard
  - Layer 1 classifier blocks prompt injection without LLM calls
  - old fallback and context fallback block missed local keywords
  - benign fallback path is allowed with a mocked classifier and no API call
- Tool Guard policy baseline:
  - dangerous SQL is blocked
  - readonly SQL is allowed
  - dangerous file operation is blocked
  - external write request is blocked
  - sensitive email content is blocked
- Output Guard baseline:
  - sensitive values are detected with masked evidence
  - sensitive values are masked in output text
  - high-risk executable output is blocked
  - RAG descriptive SQL text is allowed while executable RAG payloads are blocked
- Audit / Traceability baseline:
  - audit entries are written and verified as a hash chain
  - JSON reader returns ordered audit entries and latest-entry slices
  - human-readable reader renders audit entries for CLI / web surfaces
  - tampered JSON audit entries are detected by integrity verification
- Memory Guard contract baseline:
  - clean memory evidence is allowed
  - memory poisoning evidence is blocked
  - attribution and reason are preserved in the decision
  - audit handoff payload writes into the audit hash chain
- Goal Guard contract baseline:
  - aligned goal evidence is allowed
  - goal drift evidence is blocked
  - attribution and reason are preserved in the decision
  - audit handoff payload writes into the audit hash chain
- Tool Guard contract baseline:
  - clean tool responses are allowed
  - tampered tool responses are blocked
  - TRS attribution blocks tool tampering evidence
  - audit handoff payload writes into the audit hash chain
- policy audit records both blocked and allowed Tool Guard decisions
- Tool Integrity baseline:
  - signed temporary tool verifies successfully
  - tampered temporary tool is rejected and audited
- Tool Integrity batch handoff:
  - all signed temporary tools report `all_valid=True`
  - mixed valid / tampered temporary tools report `all_valid=False`
- E-commerce Agent MVP:
  - demo fixtures, in-memory store, clean buyer / merchant flows, refusal flows, masking, guard decisions, and audit integrity

## E-commerce Agent MVP

The local Taobao-like agent is exposed from `auto_defense_system.ecommerce_agent`.
It is deterministic and mock-only: no real Taobao APIs, no real payment, and no
real LLM calls.

Public entry points:

- `create_demo_store()`
- `invoke_ecommerce_agent(user_id, role, message, store=None)`
- `EcommerceAgentResult`

Supported business flows:

- buyer: product search, product detail, cart add/update, coupon, order creation,
  mock payment, order/logistics status, refund request, support ticket
- merchant/admin: mock price and stock management

Validation:

```powershell
python -m pytest auto_defense_system/tests/test_ecommerce_agent.py -q
```

Enterprise integration:

- The first enterprise adapter wraps this agent through `agent_security_sdk.EcommerceEnterpriseAdapter`.
- Product evaluation is orchestrated by `auto_evaluation_system.product_api.ProductEvaluationService`.
- Product reports now include JSON, Markdown, and read-only HTML dashboard artifacts.

## Tool Guard Policy Baseline

T24 fixes the current `check_policy(...)` baseline as a deterministic, no-real-tool
handoff point. It only checks policy decisions; it does not invoke the agent graph,
execute tools, call real APIs, or change Phase 3 detector contracts.

## Tool Guard Policy Audit

T25 fixes `write_policy_audit(...)` as the audit handoff for Tool Guard policy
decisions. The smoke suite now confirms both blocked and allowed decisions are
written to the audit hash chain and pass `verify_audit_integrity()`.

## Tool Guard Integrity Baseline

T26 fixes the current `security.integrity` baseline for deterministic handoff.
The smoke suite signs a temporary tool with an in-memory Ed25519 keypair, verifies
it with `verify_and_load(...)`, then tampers with the file and confirms the
integrity failure is written to the audit hash chain.

## Tool Guard Integrity Batch

T27 fixes `batch_verify_tools(...)` as the multi-tool integrity handoff. The smoke
suite now covers both all-valid tools and a mixed valid / tampered tool set.

## Output Guard Baseline

T28 fixes the current `security.output.filter` baseline as a deterministic output
handoff point. The smoke suite covers `detect_sensitive_info(...)`,
`mask_sensitive_info(...)`, and `check_output_compliance(...)`; it does not invoke
the agent graph, call real APIs, or change detector contracts.

## Input Guard / Firewall Baseline

T29 fixes the current `security.firewall` baseline as a deterministic input
handoff point. The smoke suite covers `check_malicious_input(...)`, Layer 1
classifier blocking, `classify_with_old_fallback(...)`, and
`classify_with_context(...)` fallback behavior without invoking the real LLM
classifier or the agent graph.

## Audit Traceability Baseline

T30 fixes the current `security.audit` baseline as a deterministic traceability
handoff point. The smoke suite covers `write_audit_log(...)`,
`read_audit_log_json(...)`, `read_audit_log(...)`, and
`verify_audit_integrity(...)`, including direct tamper detection. It does not
rotate signing keys, invoke the agent graph, or change detector contracts.

## Memory Guard Contract Baseline

T31 fixes the current `security.memory_guard` contract as a deterministic
defense-side handoff point. The smoke suite covers `MemoryGuardInput`,
`MemoryGuardDecision`, and `evaluate_memory_guard(...)` for clean allow,
poisoning block, attribution preservation, and audit hash-chain handoff. It does
not write or clean the memory store, invoke the agent graph, or change detector
contracts.

## Goal Guard Contract Baseline

T32 fixes the current `security.goal_guard` contract as a deterministic
defense-side handoff point. The smoke suite covers `GoalGuardInput`,
`GoalGuardDecision`, and `evaluate_goal_guard(...)` for aligned allow, goal drift
block, attribution preservation, and audit hash-chain handoff. It does not
rewrite agent goals, invoke the agent graph, or change detector contracts.

## Tool Guard Contract Baseline

T36 adds `security.tool_guard` as the deterministic runtime handoff for tool
tampering evidence. The smoke suite covers `ToolGuardInput`,
`ToolGuardDecision`, and `evaluate_tool_guard(...)` for clean allow, tampered
response block, TRS attribution block, and audit hash-chain handoff. It does not
invoke real tools, call real APIs, or integrate with the production agent graph.

## Phase 4 Defense Completion

T33 fixes Phase 4 v0.1 as a deterministic handoff, not a full production defense
deployment. The current smoke suite is the acceptance surface for Input Guard /
Firewall, Tool Guard policy, Tool Guard audit, Tool Guard contract, Tool
Integrity, Output Guard, Audit / Traceability, Memory Guard contract, and Goal
Guard contract.

Still out of scope: real agent graph integration, real LLM/API calls, detector
schema changes, trajectory schema changes, and real defense ablation experiments.

## T23 Boundary

T23 is only the Phase 4 Defense Entry Gate. It documents the existing defense
surfaces and how they can connect to the completed Phase 3 detector v0.1 handoff.
It does not implement new Memory Guard, Goal Guard, Tool Guard, detector schema,
or real API experiments.

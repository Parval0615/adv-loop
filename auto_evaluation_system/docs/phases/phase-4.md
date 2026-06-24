# Phase 4 · Defense & Guard Ablation

**Week 20–22** · runtime guard、policy engine 和防御消融入口

Phase 4 在 Phase 1–3 的 sandbox / telemetry / injectors / detector handoff 基础上，
完成 defense-side guard / policy / audit / integrity 的 deterministic v0.1 handoff。
T33 是收口验收：确认可重放、可测试、可交接，不代表已经完成真实 agent
defense ablation 或线上防御集成。

## 交付物 → 代码映射

| ROADMAP 交付物 | 仓库位置 | T33 状态 |
|----------------|----------|----------|
| Runtime Policy Engine | `auto_defense_system/src/auto_defense_system/security/policy/engine.py` | smoke-covered policy baseline and audit handoff |
| Tool Guard / Integrity | `auto_defense_system/src/auto_defense_system/security/integrity.py` | smoke-covered signing, verification, tamper rejection, and batch summary |
| Input Guard / Firewall | `auto_defense_system/src/auto_defense_system/security/firewall/` | smoke-covered local guard / fallback contract |
| Output Guard | `auto_defense_system/src/auto_defense_system/security/output/filter.py` | smoke-covered detect / mask / compliance baseline |
| Audit / Traceability | `auto_defense_system/src/auto_defense_system/security/audit.py` | smoke-covered JSON reader, text reader, hash-chain verify, and tamper detection |
| Memory Guard contract | `auto_defense_system/src/auto_defense_system/security/memory_guard.py` | smoke-covered decision contract |
| Goal Guard contract | `auto_defense_system/src/auto_defense_system/security/goal_guard.py` | smoke-covered decision contract |
| Defense handoff index | `auto_defense_system/README.md` | T33 completion handoff doc |

## Phase 3 Handoff

Phase 3 detector v0.1 is complete enough for Phase 4 entry planning:

- MIS / GDM / TRS baseline APIs are exported and tested.
- Each metric has one acceptance evaluation helper.
- Each metric has one paired report status helper and one replayable status fixture.
- Large-scale calibration, Dashboard v1, real API experiments, and guard ablations are not part of the T23 entry gate.

## T33 Completion Checklist

| Entry | Status | Acceptance |
|-------|--------|------------|
| Defense smoke | done | `python -m pytest auto_defense_system/tests -q` passes |
| Input Guard / Firewall | done | malicious prompt block, benign allow, Layer 1 block, old fallback, and context fallback covered |
| Tool Guard policy | done | dangerous SQL, readonly SQL, file operation, external POST, and sensitive email allow / block covered |
| Tool Guard policy audit | done | blocked and allowed decisions write to audit hash chain |
| Tool Integrity | done | signed tool verification, tamper rejection, and batch verification covered |
| Output Guard | done | sensitive detection, masking, high-risk block, RAG descriptive allow, and executable RAG block covered |
| Audit / Traceability | done | write, JSON read, text read, hash-chain verify, and tamper detection covered |
| Memory Guard contract | done | clean allow, poisoning block, attribution / reason, and audit handoff covered |
| Goal Guard contract | done | aligned allow, drift block, attribution / reason, and audit handoff covered |

## 当前阶段不做

- 不新增 guard 功能或重构 guard 实现。
- 不修改 Phase 3 detector API、paired report schema 或 trajectory schema。
- 不重构 `auto_defense_system` legacy code。
- 不跑需要真实 API key 的实验。
- 不跑真实 defense ablation 或线上 agent 集成。

## 下一步

下一任务包应进入 Research Output 入口：先把 Phase 1–4 的 foundation、attack
space、detector 和 defense handoff 映射到 MemoryFlow / GoalDrift / AgentRiskBench
产出计划，再决定是否执行 benchmark packaging、paper skeleton 或 dashboard work。

详见根路线图的 [Phase Flow](../../../ROADMAP.md#phase-flow)。

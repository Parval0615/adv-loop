# Phase 2 · Risk Injector & Goal Formalization

**Week 7-12 · 已完成 v0.1**

Phase 2 在 Phase 1 的 sandbox / telemetry / memory / runner 基础上完成三类受控注入与 Goal Drift 形式化定义。

## 交付物

| ROADMAP 交付物 | 仓库位置 | 状态 |
|----------------|----------|------|
| Goal Drift 定义文档 | `auto_evaluation_system/docs/specs/goal-drift/` | 已完成 v0.1 |
| GDM 结构校验器 | `auto_attack_system/src/auto_attack_system/injectors/goal_perturbation/` | 已完成 v0.1 |
| Memory Poisoning Injector | `auto_attack_system/src/auto_attack_system/injectors/memory_poisoning/` | 已完成 v0.1 |
| Tool Tamper Proxy | `auto_attack_system/src/auto_attack_system/injectors/tool_tampering/` | 已完成 v0.1 |
| Goal Perturbation Injector | `auto_attack_system/src/auto_attack_system/injectors/goal_perturbation/` | 已完成 v0.1 |
| 受控实验样例 | `auto_evaluation_system/configs/scenarios/` | clean / controlled 均已提供 |
| 标注样例 | `auto_evaluation_system/datasets/annotated/phase2/` | 已提供小型 fixture |

## 完成门禁

- Goal Drift v0.1 review 已通过，见 `docs/specs/goal-drift/review.md`。
- 三类 injector 均有 deterministic config、seed、label 和 trajectory metadata。
- 新增 scenario 均可通过 replay 无 API key 跑通。
- trajectory 仍使用 `schema_version="1.0"`，不修改 `schemas/trajectory-v1.schema.json`。
- `auto_evaluation_system.detection.goal_drift` 未实现 detector。

## 下一步

进入 Phase 3 · Task 1 Trajectory Risk Modeling。优先基于 Phase 1-2 的 labeled trajectories 做规则 / 统计 baseline，再推进 GDM / MIS / TRS detector。详见根路线图的 [Phase Flow](../../../ROADMAP.md#phase-flow)。

# Goal Drift 形式化定义 v0.1

**Phase 2 · Task 1 · 已完成 v0.1**

本规格给出 Goal Drift Metric (GDM) 的可实现边界，但本阶段只提供结构校验器，不实现 Phase 3 detector。

## Goal Representation

目标表示由 `auto_attack_system.injectors.goal_perturbation.GoalRepresentation` 校验，最小字段为：

- `primary_intent`：原始任务的主意图。
- `constraints`：执行时必须遵守的约束。
- `success_criteria`：判断任务完成的标准，至少 1 条。
- `forbidden_actions`：明确禁止的行为。
- `acceptable_alternatives`：允许的等价替代方案。

## GDM 输入与输出

Phase 3 实现 GDM 时，输入应固定为：

- 原始 `GoalRepresentation`
- prefix 或 full trajectory
- step / turn / task 粒度的 `GoalDriftProbe`
- clean baseline 与 controlled trajectory 的对照标签

输出应固定为：

- `drift_score`：0.0-1.0 的漂移强度。
- `drift_onset_step`：首次越过阈值的 step index，可为空。
- `attribution`：可追溯到具体 trajectory step 的证据。
- `decision`：`aligned` / `drifted` / `ambiguous`。

## Probe 协议

`GoalDriftProbe` 的最小字段：

- `probe_id`
- `target`：`step` / `turn` / `task`
- `question`
- `expected_alignment`：`aligned` / `drifted` / `ambiguous`

Probe 不写入 agent context window，只用于离线标注、review 和 Phase 3 detector 验证。

## Clean vs Controlled 对照

每个 controlled goal drift 实验必须有对应 clean scenario，并共享：

- `seed`
- backend framework
- 原始任务目标
- mock tool set

Controlled trajectory 必须在 `metadata.injections` 中记录 `kind="goal_perturbation"`、`strategy`、`intensity`、`label` 和 deterministic `injection_id`。

## 失败边界

False positive 风险：

- 普通工具失败导致最终答案错误，但 agent 仍追求原始目标。
- clean trajectory 中出现合理替代方案。
- 输出措辞变化但约束和主意图未变化。

False negative 风险：

- 轻微目标漂移只影响中间步骤，最终输出被后续步骤修正。
- drift 发生在隐式工具选择或记忆召回中。
- perturbation 改变了优先级但未触发显式 forbidden action。

## 校验入口

```python
from auto_attack_system.injectors.goal_perturbation import (
    GoalDriftProbe,
    GoalRepresentation,
    validate_goal_drift_spec,
)
```

该入口只校验定义结构完整性，不计算 GDM 分数，不属于 `auto_evaluation_system.detection`。

## Review

W8 review 记录见 [review.md](./review.md)。结论：v0.1 定义具备可计算性与可验证性，允许 Phase 3 在此基础上实现 detector。

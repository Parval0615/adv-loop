# Trajectory Risk Score (TRS) Spec Entry

**Phase 3 · draft entry** · 轨迹级运行时风险评分。

本规格只定义 TRS 的可实现边界，不实现 detector。

## 输入

- 完整 trajectory 或 prefix trajectory。
- step-level telemetry，包括 model messages、tool calls、memory ops、state deltas 和 policy events。
- clean / controlled pair labels，以及 MIS / GDM 等子指标输出。
- scenario config 中的 task goal、seed、backend 和 mock tool set。

## 输出

- `trajectory_risk_score`：0.0-1.0 的整体风险评分。
- `step_scores`：每个 step 的局部风险评分。
- `risk_decision`：`low` / `medium` / `high` / `ambiguous`。
- `attribution`：导致风险升高的 step、event、tool call 或 memory evidence。

## 证据

- clean / controlled trajectory 的差异。
- goal drift、memory poisoning、tool tampering 和 policy violation 的阶段性信号。
- 风险是否在最终输出前出现 early warning。
- 风险证据是否能追溯到 schema v1 中已有字段。

## 失败边界

- 最终答案错误不必然代表 trajectory risk 高。
- 单个异常 step 如果被后续步骤修正，应保留 attribution，但不必直接判高风险。
- TRS 不替代 MIS / GDM；它聚合多类风险信号并报告可解释证据。
- 当前 spec 不新增 schema 字段，不定义模型训练方案。

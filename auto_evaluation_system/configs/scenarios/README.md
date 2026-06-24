# 实验场景配置

Phase 1 Experiment Runner 读取此目录下的 YAML/JSON 场景描述。

## 约定

- 每个文件描述一个可独立运行的实验场景
- 必须包含 `seed` 以支持 deterministic replay
- 必须包含 `experiment_id`，与 Trajectory Schema 关联
- 注入实验使用 `injection_mode: controlled`；纯观测使用 `observational`

## 示例

见 [example-baseline.yaml](./example-baseline.yaml)。

## Scenario Manifest

`manifest.yaml` 记录 clean / controlled scenario 配对，用于连接 `AttackSpec`、Phase 2 replay scenarios 和后续 AgentRiskBench 打包。

Manifest 约定：

- `schema_version` 固定为 `attack-scenarios-v0.1`
- 每条 `records[]` 必须包含 `pair_id`、`attack_spec_id`、`risk_type`、`clean_scenario`、`controlled_scenario`、`seed`、`framework` 和 `controlled_label`
- clean scenario 的 `injection.mode` 必须为 `none`
- controlled scenario 的 `injection.mode` 必须为 `controlled`
- paired scenarios 必须共享 seed、framework、goal 和 mock tool mode

AttackSpec 字段说明见 [`auto_attack_system/docs/attack-spec.md`](../../../auto_attack_system/docs/attack-spec.md)。

## 命名

```
{phase}-{category}-{name}.yaml

示例:
  p1-sandbox-langgraph-isolation.yaml
  p2-inject-memory-poison-light.yaml
  p3-detect-goal-drift-probe.yaml
```

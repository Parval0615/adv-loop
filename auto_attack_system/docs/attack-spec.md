# AttackSpec

`AttackSpec` 是受控攻击的最小描述结构，用于把 attack system 的攻击定义、evaluation system 的 clean / controlled scenario 配对和后续 benchmark 打包连接起来。

当前 T1 只定义结构和 manifest，不实现 mutation engine。

## AttackSpec 字段

| 字段 | 说明 |
|---|---|
| `attack_id` | deterministic id，建议使用 `{experiment_id}:{risk_type}:{strategy}:{intensity}` |
| `risk_type` | `memory_poisoning` / `tool_tampering` / `goal_perturbation` |
| `strategy` | 具体受控注入策略，例如 `semantic_substitution` |
| `intensity` | `light` / `medium` / `heavy` |
| `target` | 攻击目标，例如 `short_term`、`get_weather`、`system_prompt` |
| `label` | controlled trajectory 的 ground-truth 标签 |
| `goal` | 原始任务目标 |
| `success_criteria` | 后续评估或 detector 验收要检查的标准 |
| `metadata` | split、paper tag、notes 等非必需补充信息 |

## Scenario Manifest 字段

`auto_evaluation_system/configs/scenarios/manifest.yaml` 记录 scenario-level 配对，不替代 `datasets/annotated/phase2/manifest.json` 的 trajectory dataset manifest。

| 字段 | 说明 |
|---|---|
| `pair_id` | clean / controlled scenario pair id |
| `attack_spec_id` | 对应 `AttackSpec.attack_id` |
| `risk_type` | 与 controlled scenario 的 `injection.kind` 一致 |
| `clean_scenario` | repo-relative clean scenario path |
| `controlled_scenario` | repo-relative controlled scenario path |
| `seed` | paired replay seed |
| `framework` | paired backend framework |
| `controlled_label` | 与 controlled scenario 的 `injection.label` 一致 |

## 边界

- 不改变 `ScenarioConfig`、`InjectionConfig`、`InjectionEvent` 或 `trajectory-v1.schema.json`。
- 不生成新 payload，不做 mutation，不实现 detector。
- Manifest 只声明现有 Phase 2 clean / controlled scenarios 的配对关系。

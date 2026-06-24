# Detector Contract and Acceptance Fixtures

**T2 · v0.1 contract** · MIS / GDM / TRS detector 的共同输入输出契约与验收 fixture 入口。

本规格只定义契约和验收数据入口，不实现 detector，不修改 `schemas/trajectory-v1.schema.json`。

## DetectorInput

`DetectorInput` 固定 detector 的最小输入：

- `metric`：`MIS` / `GDM` / `TRS`。
- `scenario_pair_id`：来自 `configs/scenarios/manifest.yaml`。
- `clean_trajectory_path`：clean trajectory，可为空，允许早期 fixture 只有 controlled trajectory。
- `controlled_trajectory_path`：controlled trajectory。
- `attack_spec_id`：对应 `AttackSpec.attack_id`。
- `metadata`：阈值、split、review notes 等附加信息。

## DetectorOutput

`DetectorOutput` 固定 detector 的最小输出：

- `metric`：与输入 metric 一致。
- `score`：0.0-1.0。
- `decision`：`clean` / `poisoned` / `aligned` / `drifted` / `low` / `medium` / `high` / `ambiguous`。
- `attribution`：至少一条可追溯证据，包含 `evidence_type`、可选 `step_index`、`field_path` 和 `summary`。
- `failure_notes`：false positive / false negative 或普通 task failure 边界说明。

## Acceptance Fixtures

`auto_evaluation_system/datasets/acceptance/detectors/manifest.yaml` 是 T2 的验收入口。每条记录连接：

- T1 scenario manifest pair。
- controlled trajectory fixture。
- 目标 metric。
- expected decision。
- expected evidence path。

当前 fixture 只用于验收未来 detector 是否消费正确输入、输出可解释证据；不声明阈值、不声明模型训练方案。

## Public API

```python
from auto_evaluation_system.detection.contracts import (
    AcceptanceFixtureManifest,
    DetectorInput,
    DetectorOutput,
    load_acceptance_fixture_manifest,
)
```

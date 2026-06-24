# Paired Evaluation Protocol

**T3 · v0.1 protocol** · clean / controlled paired evaluation 协议和报告骨架。

本规格只定义报告骨架，不实现 detector，不跑大规模实验，不调用真实 API。

## 输入

报告骨架由两类 manifest 生成：

- T1 `auto_evaluation_system/configs/scenarios/manifest.yaml`
- T2 `auto_evaluation_system/datasets/acceptance/detectors/manifest.yaml`

## Report Skeleton

每条 report record 必须包含：

- `pair_id`
- `risk_type`
- `metric`
- `attack_spec_id`
- `expected_decision`
- `evidence_summary`
- `failure_notes`
- `test_status`
- clean / controlled scenario path
- controlled trajectory path

初始 `test_status` 固定为 `not_run`，表示 detector 尚未执行。

## Golden Report Fixture

T4 固定一份 golden report fixture：

```text
auto_evaluation_system/datasets/acceptance/reports/paired-evaluation-report-v0.1.json
```

该 fixture 必须与 `build_paired_evaluation_report_skeleton()` 基于 T2 acceptance manifest 生成的内容一致。它只作为交接和测试基线，不代表 detector 已运行。

## Public API

```python
from auto_evaluation_system.runner import build_paired_evaluation_report_skeleton
```

该入口只把现有 manifest 转换为报告骨架，不计算 MIS / GDM / TRS 分数。

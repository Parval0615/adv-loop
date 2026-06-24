# Runtime Risk Specs

本目录记录 Phase 3 检测指标的规格入口。当前只固定输入、输出、证据和失败边界，不实现 detector，不修改 `schemas/trajectory-v1.schema.json`。

## 指标入口

| 指标 | 规格 | 状态 |
|---|---|---|
| MIS（Memory Integrity Score） | [memory-integrity/](./memory-integrity/) | T0 spec entry |
| GDM（Goal Drift Metric） | [goal-drift/](./goal-drift/) | v0.1 reviewed |
| TRS（Trajectory Risk Score） | [trajectory-risk/](./trajectory-risk/) | T0 spec entry |
| Detector Contract | [detector-contract/](./detector-contract/) | T2 contract entry |
| Paired Evaluation | [paired-evaluation/](./paired-evaluation/) | T3 protocol entry |

## 共通边界

- 输入来自 clean / controlled trajectory、scenario config、metadata labels 和可追溯证据。
- 输出必须包含 score、decision、attribution 和 failure notes。
- 当前阶段只写规格，不实现 `auto_evaluation_system.detection` detector。

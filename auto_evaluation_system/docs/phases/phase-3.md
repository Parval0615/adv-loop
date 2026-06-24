# Phase 3 · Detection & Trajectory Modeling

**Week 13–19** · 检测算法与轨迹风险建模

**v0.1 completion gate passed in T22.** 当前收口范围是 MIS / GDM / TRS
baseline detector 小闭环、acceptance evaluation helper、paired report status
helper 和可重放 status fixtures；不包括大规模阈值校准、Dashboard v1 或真实
API 实验。

## 交付物 → 代码映射

| ROADMAP 交付物 | 仓库位置 |
|----------------|----------|
| Trajectory Risk Model (TRS) | `auto_evaluation_system/src/auto_evaluation_system/detection/trajectory_risk/` |
| Goal Drift Detector (GDM) | `auto_evaluation_system/src/auto_evaluation_system/detection/goal_drift/` |
| Memory Integrity Score (MIS) | `auto_evaluation_system/src/auto_evaluation_system/detection/memory_integrity/` |
| Risk Dashboard v1 | `auto_evaluation_system/src/auto_evaluation_system/dashboard/` |
| Annotated Dataset v1 | `auto_evaluation_system/datasets/annotated/` |

## 前置条件

Phase 1–2 数据质量达标；Goal Drift 定义已通过 review。

## v0.1 Completion Checklist

| 交付物 | 状态 | 验收入口 |
|--------|------|----------|
| Detector Contract | done | `auto_evaluation_system.detection.contracts` |
| TRS baseline loop | done | `run_trs_baseline` + `run_trs_acceptance_evaluation` + TRS status fixture |
| GDM baseline loop | done | `run_gdm_baseline` + `run_gdm_acceptance_evaluation` + GDM status fixture |
| MIS baseline loop | done | `run_mis_baseline` + `run_mis_acceptance_evaluation` + MIS status fixture |
| Paired report status fixtures | done | `datasets/acceptance/reports/paired-evaluation-*-status-v0.1.json` |
| Large-scale calibration / Dashboard | deferred | 后续任务包单独规划，不属于 T22 收口范围 |

## 周度里程碑

- W13–14：TRS 建模
- W15–16：Goal Drift 检测器
- W17：Memory Poisoning 检测
- W18：分析引擎 / Dashboard
- W19：评估 + 基准测试

详见根路线图的 [Phase Flow](../../../ROADMAP.md#phase-flow)。

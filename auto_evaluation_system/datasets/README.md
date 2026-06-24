# Datasets

带标注的轨迹数据集与研究基线数据。

## 目录

| 路径 | 阶段 | 说明 |
|------|------|------|
| `annotated/` | Phase 2–3 | 带风险标注的 trajectory（GDM/TRS/MIS ground truth） |
| `acceptance/` | Phase 3 | detector contract acceptance fixtures |
| `raw/` | — | 原始实验输出（**不提交 Git**，见 .gitignore） |

## Acceptance

- `acceptance/detectors/manifest.yaml`：MIS / GDM / TRS detector contract acceptance fixture manifest。
- `acceptance/reports/paired-evaluation-report-v0.1.json`：paired evaluation golden report skeleton，初始 `test_status="not_run"`。

## 数据原则

- 所有数据集必须能追溯到 `experiment_id` + `seed` + 场景配置
- Annotated 数据集 Phase 3 结束后考虑公开
- 大文件放 `raw/`，仓库只保留 schema 说明与采样

## 命名

```
annotated/{phase}-{risk_type}-{version}/
  manifest.json
  trajectories/
```

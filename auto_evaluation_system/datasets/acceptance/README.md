# Acceptance Fixtures

本目录保存 Phase 3 前置验收 fixture。它们用于验证契约、manifest 和报告骨架是否能稳定交接，不运行 detector，不调用真实 API。

## Index

| 路径 | 说明 |
|---|---|
| `detectors/manifest.yaml` | MIS / GDM / TRS detector contract acceptance fixture manifest |
| `reports/paired-evaluation-report-v0.1.json` | paired evaluation golden report skeleton |
| `reports/paired-evaluation-trs-status-v0.1.json` | T13 TRS status report fixture: TRS passed, MIS / GDM not_run |
| `reports/paired-evaluation-gdm-status-v0.1.json` | T17 GDM status report fixture: GDM passed, MIS / TRS not_run |
| `reports/paired-evaluation-mis-status-v0.1.json` | T21 MIS status report fixture: MIS passed, GDM / TRS not_run |

T22 confirms these five acceptance entries as the Phase 3 v0.1 handoff set:
the golden report stays `not_run`, while each metric-specific status fixture is
replayable and scoped to one detector loop.

## 边界

- 只保存小型、可审查、可复现 fixture。
- 不保存大规模实验输出；大规模运行结果应放入未提交的 `raw/` 或 `runs/`。
- 不声明 detector 阈值或模型训练方案。

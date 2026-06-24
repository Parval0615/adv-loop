# AGENTS.md

## 概述

**Agent Runtime Security Lab** — Agent 运行时安全研究基础设施。

- **远程仓库：** https://github.com/Parval0615/Agent-Runtime-Security-Lab
- **路线图：** [ROADMAP.md](./ROADMAP.md)
- **架构：** [docs/architecture/README.md](./docs/architecture/README.md)

## 当前阶段

**Phase 3 · Detection & Trajectory Modeling（Week 13–19）**

Phase 1 已完成：`arl.sandbox` → `arl.telemetry` → `arl.memory` → `arl.runner`

Phase 2 已完成：GDM spec / review checklist → memory poisoning injector → tool tampering proxy → goal perturbation injector

当前优先：Phase 3 · Task 1 Trajectory Risk Modeling。未明确要求前，不要实现 `arl.detection.goal_drift` 的 detector 逻辑。

## 目录与阶段映射

| 路径 | 阶段 | 说明 |
|------|------|------|
| `src/arl/sandbox/` | 1 | 多框架隔离执行、可重放 |
| `src/arl/telemetry/` | 1 | Out-of-band 轨迹采集 |
| `src/arl/memory/` | 1 | 向量 + 关系双轨存储 |
| `src/arl/runner/` | 1 | 实验调度，读 `configs/scenarios/` |
| `src/arl/injectors/` | 2 | 风险注入（memory / tool / goal） |
| `src/arl/detection/` | 3 | GDM / TRS / MIS 检测 |
| `src/arl/dashboard/` | 3 | 风险可视化 |
| `schemas/` | 1 | Trajectory Schema v1 |
| `docs/specs/goal-drift/` | 2 | GDM 形式化（W8 门禁） |
| `benchmark/` | 4 | AgentRiskBench |
| `research/` | 4 | 论文与博客 |

## 开发约定

- 与用户交流使用**简体中文**
- 代码注释与文档可用中文或英文，保持模块内一致
- **最小改动**：只改当前阶段相关模块
- **可重放性优先**：任何实验代码必须支持 seed + 配置重跑
- **观测解耦**：Telemetry 不得写入 Agent context window
- 未经明确要求，不要 commit 或 push

## 常用命令

| 操作 | 命令 |
|------|------|
| 安装（editable） | `pip install -e ".[all]"` |
| 运行 sandbox smoke | `pytest tests/sandbox -q` |
| 录制 LLM cassette | `$env:VCR_RECORD='1'; pytest tests/sandbox/test_replay_direct_api.py` |
| 运行测试 | `pytest` |
| Lint | `ruff check src tests` |
| 查看状态 | `git status` |

## 门禁与风险

- **W8 Goal Drift review** 通过前，不得实现 `arl.detection.goal_drift`
- Phase 3 检测有效性依赖 Phase 1–2 数据质量，不可跳过工程底座
- 不要提交 `.env`、API key、`datasets/raw/` 大文件

## Agent 行为准则

1. 动手前读目标模块的 README 和对应 Phase 文档
2. 新实验场景放 `configs/scenarios/`，遵循命名约定
3. 轨迹数据必须符合 `schemas/trajectory-v1.schema.json`
4. 声称完成前运行 pytest / ruff（如有相关测试）
5. 遵循 ROADMAP 和 PAPER 阶段顺序，不越级实现，记录完成进度

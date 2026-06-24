# Agent Runtime Security Lab

Agent 运行时安全研究基础设施 — 从零构建可观测、可重放、可注入、可检测的实验平台。

**远程仓库：** https://github.com/Parval0615/Agent-Runtime-Security-Lab

## 研究路线

四阶段 · 约 24 周 · 详见 [ROADMAP.md](./ROADMAP.md)

| 阶段 | 名称 | 当前代码位置 |
|------|------|-------------|
| **Phase 1** | Sandbox & Telemetry Foundation | `src/arl/{sandbox,telemetry,memory,runner}/` |
| **Phase 2** | Risk Injector & Goal Formalization | `src/arl/injectors/` · `docs/specs/goal-drift/` |
| **Phase 3** | Detection & Trajectory Modeling | `src/arl/{detection,dashboard}/` |
| **Phase 4** | Research Output & Publication | `benchmark/` · `research/` · `infra/` |

## 仓库结构

```
Agent-Runtime-Security-Lab/
├── ROADMAP.md                 # 完整研究路线图
├── src/arl/                   # 核心 Python 包（按阶段组织）
│   ├── sandbox/               # Phase 1 · 执行层
│   ├── telemetry/             # Phase 1 · 观测层（out-of-band）
│   ├── memory/                # Phase 1 · 存储层
│   ├── runner/                # Phase 1 · 实验编排
│   ├── injectors/             # Phase 2 · 风险注入
│   ├── detection/             # Phase 3 · 检测与建模
│   └── dashboard/             # Phase 3 · 可视化
├── schemas/                   # Trajectory Schema v1 等
├── configs/scenarios/         # 实验场景 YAML 配置
├── docs/
│   ├── architecture/          # 系统架构与设计原则
│   ├── phases/                # 各阶段任务摘要
│   └── specs/goal-drift/      # Goal Drift 形式化（Phase 2 门禁）
├── datasets/                  # 标注数据集
├── benchmark/                 # AgentRiskBench（Phase 4）
├── research/                  # 论文与博客
├── infra/docker/              # 一键部署
└── tests/                     # 测试（镜像 src/arl 结构）
```

## 快速开始

```powershell
# 克隆
git clone https://github.com/Parval0615/Agent-Runtime-Security-Lab.git
cd Agent-Runtime-Security-Lab

# Python 环境
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## 核心设计原则

1. **可重放性** — 每次实验附带 seed + 配置，一键重跑
2. **注入与涌现分离** — 受控注入 vs 自然观测，两种模式并存
3. **轨迹为一等公民** — 完整 trajectory 是核心数据结构
4. **工程先于研究** — Phase 1–2 工程底座，Phase 3 算法研究
5. **观测与执行解耦** — Telemetry 不影响 Agent 决策

## 文档

- [系统架构](./docs/architecture/README.md)
- [Phase 1 摘要](./docs/phases/phase-1.md)
- [Goal Drift 规格（待编写）](./docs/specs/goal-drift/README.md)
- [Agent 协作约定](./AGENTS.md)
- [贡献指南](./CONTRIBUTING.md)

## License

Apache 2.0（Phase 4 开源发布目标）

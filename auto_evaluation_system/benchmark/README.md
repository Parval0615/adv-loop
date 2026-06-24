# AgentRiskBench

**Phase 4 · Week 22** · 标准化 Agent 运行时风险评测套件

AgentRiskBench 是基于 paired clean / controlled trajectories 的运行时风险 benchmark，服务 MemoryFlow、GoalDrift、Tool / MCP Security 和 Trajectory Risk Modeling。

## 目标

- ≥ 200 个标准化风险注入场景
- 覆盖 Goal Drift、Trajectory Risk、Memory Poisoning、Tool Security 四大维度
- Docker 一键部署的可复现实验环境
- 公开 Leaderboard 机制

## 结构（规划）

```
auto_evaluation_system/benchmark/
├── scenarios/          # 从 configs/scenarios/ 精选并扩展
├── evaluators/         # 统一评测脚本
├── leaderboard/        # 排行榜数据与展示
└── docker-compose.yaml # 一键部署（链接 infra/docker/）
```

## 当前状态

Phase 1–4 的 foundation、attack space、detector v0.1 和 deterministic defense
handoff 已完成收口。T34 只把 AgentRiskBench 映射到 Research Output 入口；
benchmark alpha packaging、leaderboard 和 dashboard 仍由后续任务包单独执行。

## 依赖

- `auto_evaluation_system/src/auto_evaluation_system/runner/` — 实验执行
- `auto_attack_system/src/auto_attack_system/injectors/` — 风险场景
- `auto_evaluation_system/src/auto_evaluation_system/detection/` — MIS / GDM / TRS 评测指标
- `auto_defense_system/src/auto_defense_system/security/` — 防御策略与 guard 对照

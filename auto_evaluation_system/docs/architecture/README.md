# 系统架构

Agent Runtime Security Lab 采用**分层解耦**架构：执行层、观测层、存储层、注入层、检测层各自独立，通过标准化 Trajectory 数据流连接。

## 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    Experiment Runner (Phase 1)               │
│              configs/scenarios/*.yaml → 调度队列              │
└──────────────────────────┬──────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
   ┌──────────┐     ┌──────────┐     ┌──────────┐
   │ Sandbox  │     │ Telemetry│     │  Memory  │
   │ (执行层) │     │ (观测层) │     │ (存储层) │
   └────┬─────┘     └────┬─────┘     └────┬─────┘
        │                │                │
        │    out-of-band │                │
        │    side-channel│                │
        └────────────────┼────────────────┘
                         ▼
              schemas/trajectory-v1
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
   ┌──────────┐   ┌──────────┐   ┌──────────┐
   │ Injectors│   │ Detection│   │Dashboard │
   │ (Phase 2)│   │ (Phase 3)│   │ (Phase 3)│
   └──────────┘   └──────────┘   └──────────┘
                         │
                         ▼
              benchmark/ · datasets/ · research/
                    (Phase 4 产出)
```

## 五层职责

| 层 | 包路径 | 阶段 | 核心职责 |
|----|--------|------|----------|
| 执行层 | `auto_evaluation_system.sandbox` | 1 | 多框架 Agent 隔离运行、可重放 |
| 观测层 | `auto_evaluation_system.telemetry` | 1 | 轨迹采集，与执行层物理隔离 |
| 存储层 | `auto_evaluation_system.memory` | 1 | 向量 + 关系双轨 memory |
| 注入层 | `auto_attack_system.injectors.*` | 2 | 受控风险注入 |
| 检测层 | `auto_evaluation_system.detection.*` | 3 | GDM / TRS / MIS 计算 |
| 展示层 | `auto_evaluation_system.dashboard` | 3 | 风险可视化 |

## 数据流

1. **Runner** 读取场景配置，初始化 Sandbox + Memory namespace
2. **Sandbox** 执行 Agent 任务；**Telemetry** 通过 hook 旁路采集，不写入 Agent context
3. 轨迹按 **Trajectory Schema v1** 序列化，存入实验结果目录
4. **Phase 2**：Injectors 在 memory / tool / prompt 层注入风险，生成 annotated baseline
5. **Phase 3**：Detection 消费 annotated trajectory，输出 TRS/GDM/MIS
6. **Phase 4**：Benchmark 打包 ≥200 场景，Research 产出论文与博客

## 设计原则（摘自 ROADMAP）

1. **可重放性** — 每次实验必须附带 seed + 配置，能一键重跑
2. **注入与涌现分离** — 基础设施同时支持受控注入与自然观测两种模式
3. **轨迹为一等公民** — 完整 trajectory 是核心数据结构，非仅 I/O 日志
4. **工程先于研究** — Phase 1–2 偏工程，Phase 3 才开始算法研究
5. **观测与执行解耦** — Telemetry 不得影响 Agent 决策

## 相关文档

- [ROADMAP.md](../../ROADMAP.md) — 完整 24 周路线图
- [docs/phases/](../phases/) — 各阶段任务摘要
- [docs/specs/goal-drift/](../specs/goal-drift/) — Goal Drift 形式化（Phase 2 门禁）

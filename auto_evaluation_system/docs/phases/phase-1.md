# Phase 1 · Sandbox & Telemetry Foundation

**Week 1–6** · 搭建可观测、可重放的实验基础设施

## 交付物 → 代码映射

| ROADMAP 交付物 | 仓库位置 |
|----------------|----------|
| Sandbox SDK | `auto_evaluation_system/src/auto_evaluation_system/sandbox/` |
| Telemetry Schema v1 | `auto_evaluation_system/schemas/trajectory-v1.schema.json` + `auto_evaluation_system/src/auto_evaluation_system/telemetry/` |
| Memory Store | `auto_evaluation_system/src/auto_evaluation_system/memory/` |
| Experiment Runner | `auto_evaluation_system/src/auto_evaluation_system/runner/` + `auto_evaluation_system/configs/scenarios/` |
| Architecture Doc | `auto_evaluation_system/docs/architecture/` |

## 最高优先级

**可重放性（deterministic replay）** — Phase 1 最重要的单一目标。

## 周度里程碑

- W1–2：框架集成 + 沙箱隔离
- W3–4：Telemetry 管道
- W5：Memory 双轨存储
- W6：实验编排 + 集成测试

详见根路线图的 [Phase Flow](../../../ROADMAP.md#phase-flow)。

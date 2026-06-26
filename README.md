# MCP-Sentinel / AdvLoop

本仓库当前主线是 **MCP-Sentinel「关哨」**：面向在线 LLM Agent 的提示注入与工具滥用防护网关。它以现有 AdvLoop 攻击、防御、评测内核为复用底座，规划升级为一个拦截在 `LLM Agent ↔ 工具 / MCP server / 子 Agent` 之间的 MCP-in-the-middle 安全代理。

当前阶段不是生产级网关成品，而是从 AdvLoop 赛事一基线演进到赛事二作品的研发仓库。完整任务拆解见 [`ROADMAP.md`](./ROADMAP.md)。

## 当前定位

MCP-Sentinel 的目标是把 Agent 工具调用链路中的安全风险串成一个闭环：

```text
工具调用 / 资源读取 / 子 Agent 派发
-> MCP-Sentinel 统一拦截
-> 多源注入识别
-> 意图 - 计划 - 工具语义对齐研判
-> 语义策略 DSL 三态裁决：放行 / 询问 / 阻断
-> 跨 MCP 与子 Agent 的 trace DAG 溯源
```

## Roadmap 摘要

| 任务包 | 目标 |
|---|---|
| TP-00 | 搭建具备工具调用、文件系统、网络访问、子 Agent 派发能力的在线研发助手靶场 |
| TP-01 | 实现 MCP-in-the-middle 代理骨架和统一拦截流水线 |
| TP-02 | 建立抗绕过归一化前置层 |
| TP-03 | 覆盖直接、间接、记忆三类注入识别 |
| TP-04 | 实现用户意图、Agent 计划、工具调用的语义偏离研判 |
| TP-05 | 升级语义策略 DSL，支持放行 / 询问 / 阻断三态决策 |
| TP-06 | 构建跨 MCP 与子 Agent 的攻击路径 DAG 溯源 |
| TP-07 | 串联检测、研判、阻断、溯源闭环 |
| TP-08 | 建立攻防靶场用例集和量化评估 |
| TP-09 | 提供安全研判与复盘可视化控制台 |

## 现有可复用基线

仓库已经包含 AdvLoop 赛事一的可复现资产，这些模块是赛事二网关的基础：

| 目录 | 作用 |
|---|---|
| `auto_attack_system` | payload、注入器、攻击规划、失败反思和攻击战役 |
| `auto_defense_system` | 工具策略、输入/输出防护、审计链、完整性校验、本地电商 Agent |
| `auto_evaluation_system` | sandbox、detector、closed-loop runner、证据包生成 |
| `sdk/python` | 本地观测与适配 SDK |
| `docs/competition` | AdvLoop 赛事一固定报告、复现说明和证据包 |
| `docs/product` | 本地私有单租户试点包说明 |

## 已验证能力

既有 AdvLoop 基线支持离线确定性复现：

- 多智能体闭环、攻击反思、防御自动加固、收敛曲线、雷达图、消融实验和数据卡都有单命令入口。
- 固定证据显示：初始 ASR 44%，7 轮加固后降至 0%；攻击反思使覆盖从 2/7 提升到 7/7；精准加固误伤率 0%。
- 所有攻击只作用于本地合成靶场，不连接真实淘宝、真实支付、真实企业数据或真实外部攻击目标。

## 快速开始

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pytest -q
```

## 既有基线命令

```powershell
python run.py --closed-loop-demo
python run.py --attack-campaign --offline
python run.py --defense-regression --offline
python run.py --evidence-pack --offline
```

## TP-00 靶场入口

```powershell
python -m arena.dev_agent.cli --scenario clean-readme --offline --out runs/arena-base
```

研发助手靶场说明见 [`arena/README.md`](./arena/README.md)。

固定证据副本见 [`docs/competition/evidence-pack`](./docs/competition/evidence-pack/README.md)。

## 当前实现状态

| 范围 | 状态 |
|---|---|
| TP-00 ~ TP-02 | 已完成本地靶场、代理骨架和归一化前置层。 |
| TP-03 ~ TP-09 | 已落地 deterministic local v1：多源注入识别、意图偏离、策略 DSL、trace DAG、评测集和静态复盘控制台。 |
| 生产网关能力 | 未完成；当前实现不接真实 MCP server、真实私钥、真实外网或真实远端仓库。 |

## 边界

- 当前 `ROADMAP.md` 描述的是赛事二 MCP-Sentinel 的目标形态；本仓库已提供本地 deterministic v1，但仍不是生产级 MCP 网关。
- `arena.eval` 和 `sentinel_console` 面向本地 fixture 复现与复盘，评测指标不代表真实线上流量表现。
- 本仓库不接真实淘宝、真实支付、真实企业数据或真实外部攻击目标。
- `docs/product/` 中的 enterprise pilot 指本地私有单租户试点包，不代表 SaaS、多租户或生产集成已完成。

# 赛事一 8 分钟演示脚本：电商领域自治任务智能体

## 演示目标

在 8 分钟内证明系统具备以下能力：任务解析、步骤规划、环境感知、动态重规划、目标达成判定，以及可追踪的 trace artifact。安全能力作为可靠性保障说明，不作为主叙事。

推荐优先使用离线确定性链路，保证现场可复现：

```bash
python run.py --agent-demo --offline
```

如果现场网络和 API key 可用，再补充在线模型轨迹：

```bash
export LLM_API_BASE="https://dashscope.aliyuncs.com/compatible-mode/v1"
export LLM_API_KEY="sk-your-api-key"
export LLM_MODEL="qwen-plus"
python run.py --agent-demo
```

PowerShell 环境变量写法：

```powershell
$env:LLM_API_BASE="https://dashscope.aliyuncs.com/compatible-mode/v1"
$env:LLM_API_KEY="sk-your-api-key"
$env:LLM_MODEL="qwen-plus"
python run.py --agent-demo
```

## 0:00 - 0:40 开场

各位老师好，我们的项目是“大模型驱动的电商领域自治任务智能体”。

一句话概括：系统接收自然语言购物任务后，不是走固定关键词脚本，而是解析目标、生成计划、调用真实电商工具、读取环境反馈，并在失败时动态重规划，最后给出目标是否达成和可审计轨迹。

## 0:40 - 1:40 场景与架构

当前环境是本地合成电商系统，包含商品搜索、详情、购物车、订单、支付模拟、退款、客服工单和商家运营工具。

主链路是：

```text
用户任务 -> 任务解析 -> 计划生成 -> ReAct 执行 -> 工具观察 -> 重规划 -> 目标判定 -> trace artifacts
```

需要强调两点：

1. 工具调用复用真实业务函数，不复制业务逻辑。
2. trace 会落盘为 `trace_graph.md`、`trace_timeline.jsonl`、`trace_integrity.json`，便于答辩现场追溯。

## 1:40 - 3:00 现场运行离线 demo

执行：

```bash
python run.py --agent-demo --offline
```

本轮验证输出摘要：

```text
SCENARIO=basic-search
GOAL_ACHIEVED=True
STEPS=1
REPLANS=0
TRACE=1:product_search:ok

SCENARIO=replan-stock-recovery
GOAL_ACHIEVED=True
STEPS=2
PLANS=2
REPLANS=1
TRACE=1:cart_add_item:blocked:replan > 2:cart_add_item:ok
```

讲解重点：

`basic-search` 展示基础任务解析和工具执行；`replan-stock-recovery` 展示第一次加购因库存不足被阻断，系统读取 observation 后触发重规划，选择有货商品加入购物车并达成目标。

## 3:00 - 4:20 展示 trace artifacts

打开本轮离线 demo 的产物目录：

```text
runs/agent-demo-<run-id>/replan-stock-recovery/
```

说明三个文件：

| 文件 | 现场说明 |
|---|---|
| `trace_graph.md` | Mermaid 图展示 task、decision、tool call 之间的关系 |
| `trace_timeline.jsonl` | 展示第一步 block、第二步 allow，以及对应工具调用 |
| `trace_integrity.json` | 展示 trace id、entry count、root hash 和链式 hash |

可引用的轨迹说明：

```text
第一步：cart_add_item -> blocked，原因是库存不足，触发 replan
第二步：cart_add_item -> ok，加入云朵记忆枕 x1
最终状态：当前购物车 1 件商品
```

## 4:20 - 5:20 在线 / 离线双线策略

说明复现策略：

| 路线 | 作用 |
|---|---|
| 在线路线 | 配置 Qwen 兼容 API，生成真实模型轨迹，适合正式展示模型能力 |
| 离线路线 | 使用 `--offline` 确定性 fallback，适合 CI、答辩兜底和现场网络不稳定时复现 |

两条路线共用同一套 CLI、任务编排器、业务工具和 trace artifact。区别只在 LLM 客户端是否使用真实 API。

现场口径：赛事默认链路 = v2 / run.py。`run.py --agent-demo`、`run.py --agent-task` 和 `invoke_ecommerce_agent_v2()` 是自治智能体展示入口；`invoke_ecommerce_agent()` 是 legacy 兼容入口，保留给旧单步电商用例。

## 5:20 - 6:20 任务评测指标

说明系统不只看单次 demo，也提供任务评测口径：

| 指标 | 定义 |
|---|---|
| 任务达成率 | `achieved_tasks / total_tasks` |
| 平均步数 | `total_steps / total_tasks` |
| 重规划触发率 | `replan_triggered_tasks / total_tasks` |
| 重规划成功率 | `replan_successful_tasks / replan_triggered_tasks` |
| 无效工具调用率 | `invalid_tool_calls / total_tool_calls` |

判定方式是保守组合：`TaskRunResult.goal_achieved`、真实 store 状态推断、可选 LLM judge。任何明确反证都会使任务不计为达成。

离线批量任务评测已可用：`python run.py --task-eval --offline` 运行默认 3 条任务集，输出 `task_achievement_rate`、`average_steps`、`replan_trigger_rate` 等指标并落盘 `task_evaluation_report.json`。本轮离线默认任务集 `task_achievement_rate=1.000000`。

## 6:20 - 7:10 可靠性与安全保障

安全能力作为可靠性保障：

1. 输入防火墙在电商 v2 入口前阻断明显目标漂移。
2. 工具目录按角色过滤，买家不可见商家改价和改库存工具。
3. blocked observation 不会中断进程，而是进入重规划判断。
4. trace integrity 让每次决策可复盘。

表述重点：项目主语是自治任务智能体，安全模块保证智能体在复杂任务中不越权、不漂移、可追踪。

## 7:10 - 7:50 边界与待补

需要主动说明：

1. 当前使用本地合成电商 store，不连接真实淘宝、真实支付或真实用户数据。
2. Qwen 在线真实轨迹需要现场 API key、模型可用性和网络条件，本轮报告中标为待补。
3. 单任务 CLI `python run.py --agent-task "找800元内降噪耳机比价后下单" --offline` 退出码为 0，`GOAL_ACHIEVED=True`，轨迹为 `product_search > cart_add_item > create_order`。
4. 本轮未修改 `.env.example`，Qwen 兼容模式示例只写入报告和脚本。

## 7:50 - 8:00 收尾

总结一句话：

本项目展示的是一个可运行、可复现、可审计的电商任务自治智能体。它能从自然语言任务出发，完成计划、执行、观察、重规划和目标判定，并用 trace artifacts 给出证据。

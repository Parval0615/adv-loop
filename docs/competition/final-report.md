# 大模型驱动的电商领域自治任务智能体

## 1. 项目定位

本项目面向赛事一的“生成式大语言模型与智能体”方向，目标不是展示固定脚本式购物流程，而是实现一个可以解析自然语言任务、生成计划、调用真实电商工具、读取环境反馈、动态重规划并判定目标是否达成的自治任务智能体。

当前主场景是本地合成电商环境，覆盖商品搜索、商品详情、购物车、订单、支付模拟、退款、客服工单和商家运营工具。系统不连接真实淘宝、真实支付、真实用户数据或真实外部商户；所有业务状态来自仓库内的本地 store 和工具函数。

## 2. 主线能力

```text
用户任务
  -> 任务解析：抽取 goal、subgoals、constraints、entities
  -> 步骤规划：基于角色可见工具目录生成 PlanStep
  -> 环境交互：ReAct 执行器选择工具、生成参数、调用真实业务函数
  -> 环境感知：把工具结果、blocked、缺货、预算不足、异常等写入 Observation
  -> 动态重规划：失败或阻断时生成 revision+1 的替代计划
  -> 目标达成判定：结合 TaskRunResult、真实 store 状态和可选 LLM judge
  -> trace artifacts：导出可审计的图、时间线和完整性哈希
```

这条链路对应赛事评分语言中的任务解析、任务规划、环境感知、自主决策、动态重规划和目标达成验证。

## 3. 系统组成

| 模块 | 职责 | 关键产物 |
|---|---|---|
| `task_agent/planner.py` | 解析自然语言任务并生成计划 | `TaskSpec`、`Plan`、`PlanStep` |
| `task_agent/executor.py` | 执行 ReAct 循环并调用真实电商工具 | `TaskStep`、`Observation` |
| `task_agent/replanner.py` | 根据 blocked、缺货、预算、支付失败等反馈触发重规划 | `Plan.revision`、replan reason |
| `task_agent/agent.py` | 编排 parse、plan、execute、replan、summary、verify | `TaskRunResult` |
| `task_agent/trace_adapter.py` | 把任务轨迹转换为 trace DAG artifacts | `trace_graph.md`、`trace_timeline.jsonl`、`trace_integrity.json` |
| `auto_evaluation_system/task_eval.py` | 批量计算任务达成与自治能力指标 | `TaskEvaluationReport` |

工具目录复用 `auto_defense_system.ecommerce_agent.tools` 的真实业务函数；买家角色不可见 `merchant_*` 工具，未知工具和参数错误会被转成 blocked observation，而不是抛出未捕获异常。

## 4. 配置与 Qwen 兼容模式

配置读取语义保持不变：`SharedLLMClient` 默认通过 `LLMConfig.from_project()` 读取项目配置；防御侧事实来源 `auto_defense_system/src/auto_defense_system/config.py` 已读取以下环境变量：

| 变量 | 当前语义 |
|---|---|
| `LLM_API_BASE` | OpenAI-compatible endpoint，默认 `https://api-inference.modelscope.cn/v1` |
| `LLM_API_KEY` | API key，未配置时为空 |
| `LLM_MODEL` | 模型名，默认 `Qwen/Qwen3.5-35B-A3B` |

Qwen 兼容模式可直接通过 shell 环境变量注入，不需要改变代码读取逻辑。

macOS / Linux 示例：

```bash
export LLM_API_BASE="https://dashscope.aliyuncs.com/compatible-mode/v1"
export LLM_API_KEY="sk-your-api-key"
export LLM_MODEL="qwen-plus"
python run.py --agent-demo
```

PowerShell 示例：

```powershell
$env:LLM_API_BASE="https://dashscope.aliyuncs.com/compatible-mode/v1"
$env:LLM_API_KEY="sk-your-api-key"
$env:LLM_MODEL="qwen-plus"
python run.py --agent-demo
```

本轮只补充文档说明，未修改 `.env.example` 或任何代码文件。

## 5. 在线 / 离线双线复现策略

| 路线 | 用途 | 命令形态 | 证据价值 |
|---|---|---|---|
| 在线路线 | 生成真实模型轨迹，体现 Qwen 兼容 API 下的任务解析、计划和决策 | 配置 `LLM_API_*` 后运行 `python run.py --agent-demo` 或 `python run.py --agent-task "..."` | 用于正式展示真实模型行为；输出会受模型版本、网络和账号额度影响 |
| 离线路线 | CI、答辩兜底和现场 API 不稳定时复现 | `python run.py --agent-demo --offline` | 使用确定性 fallback，稳定生成 trace artifacts，验证编排、工具调用、重规划和目标判定链路 |

两条路线共用同一 CLI、同一任务编排器和同一 trace 导出器。区别只在 LLM 客户端是否强制使用 deterministic fallback；业务工具和 trace artifact 格式不变。

入口策略：赛事默认链路 = v2 / run.py。`run.py --agent-demo`、`run.py --agent-task` 和 `invoke_ecommerce_agent_v2()` 使用 TaskAgent 主链路；`invoke_ecommerce_agent()` 暂保留 legacy 关键词路由，用于已有单步电商 API 和旧测试兼容，legacy `_route_message()` 不作为赛事默认链路。

## 6. CLI 与 Trace Artifacts

核心命令：

```bash
python run.py --agent-demo --offline
python run.py --agent-task "找800元内降噪耳机比价后下单" --offline
```

`--agent-demo --offline` 会运行两个演示场景：

| 场景 | 任务 | 本轮验证结果 |
|---|---|---|
| `basic-search` | `搜索降噪耳机` | `LLM_MODE=deterministic-offline`，`GOAL_ACHIEVED=True`，`STEPS=1`，`REPLANS=0` |
| `replan-stock-recovery` | `把有货商品加入购物车` | `LLM_MODE=scripted-demo-offline`，`GOAL_ACHIEVED=True`，`STEPS=2`，`PLANS=2`，`REPLANS=1` |

本轮离线 demo 实际生成的证据目录：

```text
runs/agent-demo-<run-id>/basic-search/
runs/agent-demo-<run-id>/replan-stock-recovery/
```

每个场景输出以下 artifact：

| 文件 | 内容 |
|---|---|
| `trace_graph.md` | Mermaid 图，展示 task、decision、tool call 之间的关系 |
| `trace_timeline.jsonl` | 决策和工具调用的逐行时间线 |
| `trace_integrity.json` | trace id、entry count、root hash 和链式 hash |

`replan-stock-recovery` 的关键轨迹摘要：

```text
TRACE=1:cart_add_item:blocked:replan > 2:cart_add_item:ok
FINAL_ANSWER=... 重规划 1 次。成功工具：cart_add_item。失败或拦截：库存不足，不能加入购物车。最新结果：已加入购物车：云朵记忆枕 x1。真实状态：当前购物车 1 件商品。
```

这条证据说明系统不是静态脚本：第一次加购因库存不足被环境阻断，随后触发重规划并选择有货商品完成目标。

## 7. 任务评测指标定义

任务评测模块输出 `TaskEvaluationReport`，其中指标定义如下：

| 指标 | 定义 |
|---|---|
| `task_achievement_rate` | `achieved_tasks / total_tasks` |
| `average_steps` | `total_steps / total_tasks` |
| `replan_trigger_rate` | `replan_triggered_tasks / total_tasks` |
| `replan_success_rate` | `replan_successful_tasks / replan_triggered_tasks` |
| `invalid_tool_call_rate` | `invalid_tool_calls / total_tool_calls` |

单条任务是否达成会综合三类信号：`TaskRunResult.goal_achieved`、真实 store 状态推断、可选 LLM judge。评测逻辑偏保守：如果结果声称达成但 store 证据或 judge 明确否定，则该任务不计为达成。

本轮已运行离线默认批量任务评测集：

```bash
python run.py --task-eval --offline
```

产物路径形如 `runs/task-eval-<run-id>/task_evaluation_report.json`，报告 schema 为 `task-evaluation-report-v0.1`。离线指标如下，均来自最新一次真实运行：

| 指标 | 数值 |
|---|---:|
| `total_tasks` | 3 |
| `achieved_tasks` | 3 |
| `task_achievement_rate` | 1.000000 |
| `average_steps` | 1.000000 |
| `replan_trigger_rate` | 0.000000 |
| `replan_success_rate` | 0.000000 |
| `invalid_tool_call_rate` | 0.000000 |
| `total_tool_calls` | 3 |
| `invalid_tool_calls` | 0 |

默认任务集包含 `搜索降噪耳机`、`搜索智能手表`、`联系平台招商客服说明订单问题`。本轮未运行 Qwen 在线批量评测，因此不填写在线模型成功率或在线轨迹指标。

## 8. 安全作为可靠性保障

安全能力不作为本报告主线，但它是自治任务智能体可靠执行的保障：

1. 输入防火墙继续位于电商 v2 入口前，阻断明显目标漂移和高风险请求。
2. 工具目录按角色过滤，买家任务无法直接调用商家改价、改库存等工具。
3. 业务失败、策略阻断和工具异常会进入 observation，并可触发重规划。
4. trace integrity 为任务执行过程提供可审计证据，便于复盘每次决策来源。

因此，项目主语是“电商领域自治任务智能体”；安全模块的定位是防止智能体在复杂任务中越权、漂移或不可追踪。

## 9. 已验证命令

本轮已在项目根目录运行：

```bash
python run.py --agent-demo --offline
```

结果：退出码 0；`basic-search` 与 `replan-stock-recovery` 均 `GOAL_ACHIEVED=True`；重规划场景 `REPLANS=1`；trace artifacts 已落盘到 `runs/agent-demo-<run-id>/`。

同时运行了单任务 CLI：

```bash
python run.py --agent-task "找800元内降噪耳机比价后下单" --offline
```

结果：退出码 0；`GOAL_ACHIEVED=True`；`STEPS=3`；`REPLANS=0`；轨迹为 `product_search > cart_add_item > create_order`；trace artifacts 已落盘。搜索词清洗后直接命中商品 `p1001`，加购后创建订单 `o0002`（金额 599.00 元，状态 pending_payment），无需重规划即达成目标。

同时运行了批量任务评测 CLI：

```bash
python run.py --task-eval --offline
```

结果：退出码 0；`total_tasks=3`，`achieved_tasks=3`，`task_achievement_rate=1.000000`，`average_steps=1.000000`，`replan_success_rate=0.000000`，`invalid_tool_call_rate=0.000000`；报告已落盘到 `runs/task-eval-<run-id>/task_evaluation_report.json`。

## 10. 待补数据与边界

| 项目 | 状态 |
|---|---|
| Qwen 在线真实轨迹 | 待补。需要有效 `LLM_API_KEY`、可访问的兼容 endpoint 和现场网络。 |
| 批量任务评测汇总 | 离线默认任务集已补：`task_achievement_rate=1.000000`，报告见 `runs/task-eval-<run-id>/task_evaluation_report.json`。Qwen 在线批量评测仍待补，需要有效 API key、可访问 endpoint 和现场网络。 |
| 生产电商接入 | 不在本项目范围。当前只使用本地合成 store。 |
| `.env.example` 更新 | 本轮未修改，配置示例已写入报告和演示脚本。 |

## 11. 答辩复现建议

首选展示离线稳定链路：

```bash
python run.py --agent-demo --offline
```

如果现场 API 可用，再展示在线链路：

```bash
export LLM_API_BASE="https://dashscope.aliyuncs.com/compatible-mode/v1"
export LLM_API_KEY="sk-your-api-key"
export LLM_MODEL="qwen-plus"
python run.py --agent-demo
```

评委追问可打开 `runs/<run-id>/<scenario>/trace_graph.md`、`trace_timeline.jsonl` 和 `trace_integrity.json`，说明每一步计划、工具调用、环境阻断、重规划和最终状态证据。

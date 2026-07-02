# 竞赛资料入口

本目录保存 AdvLoop「智驭」赛事一资料。当前提交主线已统一为 **大模型驱动的电商领域自治任务智能体**：系统接收自然语言购物任务后，完成任务解析、计划生成、真实电商工具调用、环境感知、动态重规划和目标达成判定。

安全攻防能力仍保留为可靠性保障和历史证据，不再作为本目录的主叙事。

## 当前主线

| 能力 | 当前落点 | 证据 |
|---|---|---|
| 任务解析与计划生成 | `task_agent/planner.py`、`TaskSpec`、`Plan` | [`final-report.md`](./final-report.md) |
| ReAct 执行与真实工具调用 | `task_agent/executor.py`、`tool_registry.py` | [`comp1-agent-demo-script.md`](./comp1-agent-demo-script.md) |
| 环境感知与动态重规划 | blocked、缺货、预算不足等 observation 触发 `replan()` | `runs/agent-demo-<run-id>/replan-stock-recovery/` |
| 目标达成与批量评测 | `auto_evaluation_system/task_eval.py` | `runs/task-eval-<run-id>/task_evaluation_report.json` |
| 证据可追溯 | `trace_graph.md`、`trace_timeline.jsonl`、`trace_integrity.json` | `task_agent/trace_adapter.py` |

## 已验证结果

| 结论 | 当前结果 | 证据 |
|---|---:|---|
| 离线 demo 可复现 | `basic-search` 与 `replan-stock-recovery` 均 `GOAL_ACHIEVED=True` | [`final-report.md`](./final-report.md) |
| 重规划链路有效 | `replan-stock-recovery` 首步 blocked，随后 `REPLANS=1` 并达成目标 | [`comp1-agent-demo-script.md`](./comp1-agent-demo-script.md) |
| 单任务 CLI 达成目标 | `GOAL_ACHIEVED=True`，轨迹为 `product_search > cart_add_item > create_order` | [`reproducibility.md`](./reproducibility.md) |
| 批量任务评测可运行 | `total_tasks=3`，`achieved_tasks=3`，`task_achievement_rate=1.000000` | [`final-report.md`](./final-report.md) |
| 历史安全证据保留 | ASR 44% -> 0%，7 轮收敛 | [`evidence-pack/`](./evidence-pack/) |

## 目录导览

| 文件 | 用途 |
|---|---|
| [`final-report.md`](./final-report.md) | 赛事一正式项目报告，主线为电商自治任务智能体 |
| [`comp1-agent-demo-script.md`](./comp1-agent-demo-script.md) | 8 分钟现场演示脚本，覆盖重规划场景 |
| [`reproducibility.md`](./reproducibility.md) | 环境、安装、离线复现和验证命令 |
| [`submission-checklist.md`](./submission-checklist.md) | 提交前检查清单 |
| [`evidence-pack/`](./evidence-pack/) | 历史安全攻防证据副本，作为可靠性补充 |
| [`defense-script-8min.md`](./defense-script-8min.md) | 历史安全攻防讲稿，非当前主演示脚本 |

## 推荐运行顺序

```bash
python run.py --agent-demo --offline
python run.py --agent-task "找800元内降噪耳机比价后下单" --offline
python run.py --task-eval --offline
python -m pytest -q task_agent/tests trace_dag/tests auto_attack_system/tests auto_defense_system/tests auto_evaluation_system/tests
```

## 边界声明

- 当前主线使用本地合成电商 store，不连接真实淘宝、真实支付、真实用户数据或真实外部商户。
- 在线 Qwen 轨迹需要有效 `LLM_API_KEY`、兼容 endpoint 和现场网络；无 API key 时使用 `--offline` 可确定性复现核心链路。
- `invoke_ecommerce_agent_v2()`、`run.py --agent-demo` 和 `run.py --agent-task` 是赛事展示入口；旧 `invoke_ecommerce_agent()` 仅作为 legacy 兼容入口。
- 历史安全攻防材料可作为可靠性补充，不应替代电商自治任务智能体主线。

# AdvLoop 赛事一复现说明

本文件用于复现“大模型驱动的电商领域自治任务智能体”主线。核心链路不依赖真实外部服务；无 API key 或现场网络不稳定时，使用 `--offline` 可确定性复现任务解析、规划、工具调用、重规划、目标判定和 trace artifacts。

## 环境要求

- Python 3.10+
- macOS、Linux、Windows PowerShell 或兼容 shell
- 从项目根目录运行命令
- 当前主线只连接本地合成电商 store，不接真实淘宝、真实支付或真实用户数据

## 安装

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

PowerShell 激活方式：

```powershell
.\.venv\Scripts\Activate.ps1
```

## 电商自治任务智能体主链路复现

```bash
python run.py --agent-demo --offline
python run.py --agent-task "找800元内降噪耳机比价后下单" --offline
python run.py --task-eval --offline
```

预期摘要：

- `--agent-demo --offline`：运行 `basic-search` 和 `replan-stock-recovery` 两个场景；后者首步因库存不足 blocked，随后触发 `REPLANS=1` 并达成目标。
- `--agent-task ... --offline`：单任务输出 `GOAL_ACHIEVED=True`，轨迹为 `product_search > cart_add_item > create_order`。
- `--task-eval --offline`：默认 3 条任务集输出 `task_achievement_rate=1.000000`、`average_steps=1.000000`、`invalid_tool_call_rate=0.000000`。

## 在线 Qwen 兼容模式

如果现场 API 可用，可运行在线模型链路：

```bash
export LLM_API_BASE="https://dashscope.aliyuncs.com/compatible-mode/v1"
export LLM_API_KEY="sk-your-api-key"
export LLM_MODEL="qwen-plus"
python run.py --agent-demo
```

在线结果会受模型版本、网络和账号额度影响；报告中未补在线批量指标时，不应把离线指标冒充在线指标。

## 回归验证

```bash
python -m pytest -q task_agent/tests trace_dag/tests auto_attack_system/tests auto_defense_system/tests auto_evaluation_system/tests
python -m compileall -q auto_attack_system auto_defense_system auto_evaluation_system sdk task_agent trace_dag
```

全量 pytest 收集阶段已处理 `langchain_openai` 缺失导致的导入阻塞；离线/CI 环境应能完成本规格相关测试验证。

## 运行产物位置

| 目录 | 来源命令 | 内容 |
|---|---|---|
| `runs/agent-demo-<run-id>/basic-search/` | `python run.py --agent-demo --offline` | 基础搜索场景 trace artifacts |
| `runs/agent-demo-<run-id>/replan-stock-recovery/` | `python run.py --agent-demo --offline` | 库存阻断后重规划场景 trace artifacts |
| `runs/task-agent-<run-id>/` | `python run.py --agent-task "..." --offline` | 单任务计划、执行和 trace artifacts |
| `runs/task-eval-<run-id>/task_evaluation_report.json` | `python run.py --task-eval --offline` | 批量任务评测报告 |

历史安全攻防证据副本仍位于 [`evidence-pack/`](./evidence-pack/)，可作为可靠性补充材料。

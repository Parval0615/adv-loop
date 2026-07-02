# MCP-Sentinel 复现说明

本文用于复现 MCP-Sentinel 的多智能体安全自治闭环。默认命令使用本地合成数据，不访问真实交易系统、企业数据或外部攻击目标。

## 环境

- Python 3.10+
- Windows PowerShell、macOS 或 Linux shell
- 从仓库根目录运行

## 安装

```powershell
git clone https://github.com/Parval0615/mcp-sentinel.git
cd mcp-sentinel
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## 离线确定性复现

```powershell
python run.py --attack-campaign --offline
python run.py --defense-regression --offline
python run.py --evidence-pack --offline
python run.py --closed-loop-demo
python run.py --agent-demo --offline
python run.py --agent-task "找800元内降噪耳机比价后下单" --offline
python run.py --task-eval --offline
```

预期行为：

- Attack Agent 扩展到七类攻击面，并输出反思与升级记录。
- Defense Agent 将基线攻击成功率降至目标范围，同时精准策略不阻断良性请求。
- Evidence Pack 生成 JSON、Markdown、收敛曲线、雷达图和消融结果。
- Closed Loop Demo 对受控风险完成检测、阻断和审计完整性验证。
- Task Agent 展示自然语言解析、业务工具执行和失败后的重规划。

具体数字以每次命令输出和生成 JSON 为准，不使用手工维护的历史结果代替当前运行。

## 在线大模型模式

```powershell
$env:LLM_API_BASE="https://dashscope.aliyuncs.com/compatible-mode/v1"
$env:LLM_API_KEY="sk-your-api-key"
$env:LLM_MODEL="qwen-plus"
python run.py --attack-campaign
python run.py --defense-regression
python run.py --agent-task "评估目标 Agent 的工具调用风险并给出执行计划"
```

在线结果受模型版本、API 和网络影响。正式证据应记录模型名、运行时间、实际模式和是否发生 fallback；不得把离线确定性输出标为在线模型结果。

## 回归验证

```powershell
python -m pytest -q
python -m compileall -q auto_attack_system auto_defense_system auto_evaluation_system sdk task_agent trace_dag arena evasion_shield injection_radar intent_aligner policy_dsl sentinel_console sentinel_proxy
git diff --check
```

## 产物目录

| 目录 | 内容 |
|---|---|
| `attack-runs/` | 攻击战役、覆盖和反思日志 |
| `defense-runs/` | 加固决策和良性回归 |
| `evidence-runs/` | 曲线、雷达图、消融和数据卡 |
| `runs/` | 闭环、任务 Agent、trace 和评测结果 |
| `docs/competition/evidence-pack/` | 用于提交和答辩的固定证据副本 |

这些运行目录均被 Git 忽略；只有经过验证并同步到固定证据包的产物进入提交。

## 边界

- `--offline` 证明工程闭环可复现，不证明真实大模型质量。
- 电商支付、退款、网络访问和 Git 推送均为本地模拟。
- 当前控制台是静态本地复盘页面。
- 禁止将真实密钥、真实用户数据或外部攻击目标加入复现配置。

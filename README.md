# MCP-Sentinel

MCP-Sentinel 是一个面向 LLM Agent 运行安全的大模型驱动多智能体自治系统。它把复杂安全目标转化为可执行计划，由 Attack Agent 探索风险、Defense Agent 根据损伤反馈选择加固动作、Evaluation Agent 量化效果并驱动下一轮决策，形成可复现、可审计的闭环。

项目面向“生成式大语言模型与智能体”赛题：以智能体运行安全为代表性实际问题，展示任务理解、步骤规划、环境感知、自主决策、工具执行、失败反思和动态重规划。电商 RAG Agent 与本地 MCP 工具链是验证环境，不代表接入真实交易、支付、企业数据或外部攻击目标。

## 自治闭环

```text
用户安全目标 / 业务任务
        ↓
任务解析与计划生成
        ↓
Attack Agent ──攻击结果与失败反馈──┐
        ↓                           │
Evaluation Agent ──风险与损伤报告──┤
        ↓                           │
Defense Agent ──加固动作与策略更新──┘
        ↓
重新评测，直至风险收敛或达到停止条件
        ↓
trace DAG、审计链、指标与证据包
```

在线模式通过 OpenAI-compatible API 调用 Qwen 等模型完成结构化解析、计划、动作选择和反思；离线模式使用确定性 fallback，保证 CI 和答辩现场可以稳定复现工程闭环。离线结果只证明编排、环境反馈和评测链路，不冒充在线模型能力。

## 代码结构

| 模块 | 职责 |
|---|---|
| `task_agent` | 自然语言任务解析、计划、ReAct 执行、观察、重规划与目标判定 |
| `auto_attack_system` | 攻击动作生成、攻击面探索、失败反思与策略升级 |
| `auto_defense_system` | 防御动作选择、策略执行、权限控制、输入输出防护与审计 |
| `auto_evaluation_system` | 沙箱运行、风险检测、闭环评测、消融实验和证据生成 |
| `sentinel_proxy` | 工具、资源与子 Agent 调用的统一拦截流水线 |
| `injection_radar` / `intent_aligner` | 注入识别与用户意图—计划—工具语义对齐 |
| `policy_dsl` | 放行、询问、阻断三态策略决策 |
| `trace_dag` | 跨工具、MCP 与子 Agent 的执行链路溯源 |
| `arena` | 文件、网络、命令、模拟 Git 和子 Agent 场景的本地靶场 |

## 快速开始

```powershell
git clone https://github.com/Parval0615/mcp-sentinel.git
cd mcp-sentinel
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
python -m pytest -q
```

## 核心演示

```powershell
# 多智能体攻击—评测—防御闭环
python run.py --closed-loop-demo

# Attack Agent 探索与反思
python run.py --attack-campaign --offline

# Defense Agent 自主加固与良性回归
python run.py --defense-regression --offline

# 收敛曲线、雷达图、消融和数据卡
python run.py --evidence-pack --offline

# 自然语言任务解析、工具执行和重规划
python run.py --agent-demo --offline
```

正式在线轨迹可通过 `.env` 中的 `LLM_API_BASE`、`LLM_API_KEY` 和 `LLM_MODEL` 配置。详细复现步骤见 [`docs/competition/reproducibility.md`](docs/competition/reproducibility.md)。

## 当前边界

- 当前验证环境是本地合成电商与研发助手靶场，不连接真实淘宝、真实支付、真实企业数据或真实外部攻击目标。
- MCP 拦截、控制台和评测面向本地 fixture；当前指标不代表生产流量表现。
- 在线模型效果依赖模型版本、API 可用性和网络；固定证据包以离线确定性复现为基准。
- 产品试点材料描述本地私有部署能力，不代表 SaaS、多租户或生产集成已经完成。

赛题对应关系、演示讲稿和固定证据入口见 [`docs/competition/README.md`](docs/competition/README.md)。

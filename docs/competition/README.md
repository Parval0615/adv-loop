# MCP-Sentinel 竞赛资料

本目录保存 MCP-Sentinel 面向“生成式大语言模型与智能体”赛题的正式材料。项目主线是大模型驱动的多智能体安全自治系统：解析安全目标、规划攻防步骤、感知执行环境、根据结果自主决策，并通过自动评测形成可追溯闭环。

## 赛题能力映射

| 能力 | 代码落点 | 主要证据 |
|---|---|---|
| 自然语言任务解析与计划 | `task_agent/planner.py` | [`final-report.md`](final-report.md) |
| Attack Agent 攻击规划与失败反思 | `auto_attack_system/attack_agent.py` | 固定证据包、攻击战役输出 |
| Defense Agent 自主加固 | `auto_defense_system/defense_agent.py` | 防御回归和消融实验 |
| Evaluation Agent 环境反馈 | `auto_evaluation_system` | 收敛曲线、雷达图和数据卡 |
| 工具与 MCP 场景决策 | `sentinel_proxy`、`policy_dsl`、`arena` | allow / ask / block 轨迹 |
| 跨链路审计与溯源 | `trace_dag`、审计哈希链 | trace、timeline、integrity artifacts |

## 文档入口

| 文件 | 用途 |
|---|---|
| [`final-report.md`](final-report.md) | 正式项目报告与能力边界 |
| [`comp1-agent-demo-script.md`](comp1-agent-demo-script.md) | 八分钟主演示脚本 |
| [`reproducibility.md`](reproducibility.md) | 安装、离线复现和在线配置 |
| [`submission-checklist.md`](submission-checklist.md) | 提交前验证与打包清单 |
| [`evidence-pack/`](evidence-pack/) | 当前代码生成的固定证据副本 |

## 推荐演示顺序

```powershell
python run.py --attack-campaign --offline
python run.py --defense-regression --offline
python run.py --evidence-pack --offline
python run.py --closed-loop-demo
python run.py --agent-demo --offline
```

离线结果证明系统编排、工具执行、环境反馈、决策闭环和证据生成可复现；真实大模型能力应使用有效 Qwen 兼容 API 生成在线轨迹，并明确记录实际运行模式和 fallback 状态。

## 安全边界

- 所有攻击仅针对本地合成靶场。
- 不连接真实淘宝、真实支付、真实用户数据、真实企业系统或真实外部攻击目标。
- 固定指标是本地确定性基准，不代表生产流量效果。

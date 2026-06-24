# 竞赛资料入口

本目录保存 **AdvLoop「智驭」赛事一基线** 的正式报告、讲稿、固定证据包和复现说明。仓库当前主线已经切换到 **MCP-Sentinel「关哨」赛事二规划**，请先阅读根目录 [`README.md`](../../README.md) 和 [`ROADMAP.md`](../../ROADMAP.md) 了解当前方向。

## 当前主线

MCP-Sentinel 面向在线 LLM Agent 的提示注入与工具滥用防护，目标形态是 MCP-in-the-middle 中间代理，覆盖：

| 能力 | Roadmap 对应 |
|---|---|
| 多源注入识别 | TP-02、TP-03、TP-08 |
| 意图 - 计划 - 工具语义对齐研判 | TP-04 |
| 语义策略 DSL 与三态决策 | TP-05 |
| 跨 MCP / 子 Agent 溯源 DAG | TP-06、TP-09 |
| 检测 → 研判 → 阻断 → 溯源闭环 | TP-07 |

## 既有 AdvLoop 基线

AdvLoop / 智驭是一个面向 LLM 安全任务的**多智能体自治闭环系统**：Attack Agent 解析任务并规划攻击，Evaluation Agent 感知环境并量化风险，Defense Agent 自主选择加固动作，并在本地电商 RAG 场景中验证收敛。

多数 Agent 项目展示的是“用 Agent 完成一个业务任务”。AdvLoop 展示的是“让多个 Agent 自己完成安全任务闭环”：系统自动发现风险、量化损伤、选择加固动作，并用同一攻击集回归验证决策效果。

## 固定结果

| 结论 | 当前结果 | 证据 |
|---|---:|---|
| 自治闭环可收敛 | ASR 44% -> 0%，7 轮收敛 | [`evidence-pack/convergence_curve.png`](./evidence-pack/convergence_curve.png) |
| 攻击反思有效 | 无 reflection 覆盖 2/7，完整系统覆盖 7/7 | [`evidence-pack/ablation_table.md`](./evidence-pack/ablation_table.md) |
| 防御决策不可或缺 | 去掉 Defense 后 ASR 保持 44% | [`evidence-pack/ablation.json`](./evidence-pack/ablation.json) |
| 自主加固不伤正常请求 | 精准加固误伤率 0% | [`../product/product-readiness-audit.md`](../product/product-readiness-audit.md) |
| 工程可回归 | 215 passed, 1 skipped, 2 warnings | [`reproducibility.md`](./reproducibility.md) |

## 目录导览

| 文件 | 用途 |
|---|---|
| [`final-report.md`](./final-report.md) | AdvLoop 赛事一正式项目报告 |
| [`defense-script-8min.md`](./defense-script-8min.md) | AdvLoop 8 分钟中文讲解稿 |
| [`reproducibility.md`](./reproducibility.md) | 环境、安装、离线复现和验证命令 |
| [`submission-checklist.md`](./submission-checklist.md) | AdvLoop 提交前检查清单 |
| [`evidence-pack/`](./evidence-pack/) | AdvLoop 固化后的最终证据副本 |

## 推荐运行顺序

```powershell
python run.py --closed-loop-demo
python run.py --attack-campaign --offline
python run.py --defense-regression --offline
python run.py --evidence-pack --offline
python -m pytest -q
```

## 边界声明

- 当前目录中的正式报告和证据包对应 AdvLoop 赛事一基线。
- MCP-Sentinel 赛事二目标形态以根目录 `ROADMAP.md` 为准，尚需按 TP-00 到 TP-09 逐步实现。
- 所有攻击只作用于本地 mock 靶场。
- 不接真实淘宝、真实支付、真实企业数据或真实外部攻击目标。
- 无 API key 时使用 `--offline`，核心基线结果仍可确定性复现。

# AdvLoop 智驭：面向 LLM 安全任务的多智能体自治闭环系统

## 1. 背景问题

生成式大语言模型正在从问答走向智能体：它们能够解析任务、规划步骤、检索信息、调用工具并根据环境反馈做决策。与此同时，LLM / RAG 应用也面临提示注入、知识库投毒、工具篡改、记忆污染、目标漂移、越权检索和敏感信息泄露等复杂风险。

本项目并不把安全只当作规则集合，而是把它作为一个适合智能体自治解决的实际问题：能否让多个 Agent 自己发现风险、量化损伤、选择加固动作，并验证系统是否收敛。

## 2. 核心思路

AdvLoop 提出“多智能体对抗自进化框架”。Attack Agent 负责解析任务、规划攻击、记录失败并反思重规划；Evaluation Agent 负责感知环境、读取响应和工具调用并量化指标；Defense Agent 负责根据损伤报告自主选择加固动作；最后通过同一攻击集回归验证决策效果。

代表性环境是本地电商 RAG Agent，覆盖商品搜索、导购、订单、支付模拟、退款、客服和商家运营等业务流。所有数据均为本地合成数据，不接真实淘宝、真实支付、真实企业数据或真实外部攻击目标。

## 3. 系统架构

```text
Attack Agent
  解析任务 -> 规划攻击 -> 执行 -> 失败反思 -> 重规划
        |
        v
本地电商 RAG 环境
  搜索 / 导购 / 订单 / 支付模拟 / 退款 / 客服 / 商家操作
        |
        v
Evaluation Agent
  环境感知 -> 轨迹分析 -> 指标量化 -> 损伤归因
        |
        v
Defense Agent
  根据损伤报告自主选择加固动作
        |
        v
回归验证 -> 智能体决策报告 / 收敛曲线 / 消融实验 / 数据卡
```

## 4. 三智能体职责

| 智能体 | 职责 | 当前产物 |
|---|---|---|
| Attack Agent | 生成攻击计划，记录攻击历史，失败后反思并升级策略 | `attack_history.jsonl`、`reflection_log.json`、`coverage_table.md` |
| Evaluation Agent | 从轨迹、工具调用和审计记录中判断攻击是否成功，计算 ASR、误伤率和覆盖率 | `report.json`、`regression_report.json`、`convergence.json` |
| Defense Agent | 根据损伤报告选择精准加固动作，并通过良性请求回归控制误伤 | `hardening_decisions.json`、`defense_summary.md` |

## 5. 任务与环境

项目将本地电商 Agent 的风险划分为 7 类：提示注入、知识库投毒、越权检索、工具篡改、记忆污染、目标漂移和敏感信息泄露。这些风险既是安全问题，也是智能体任务规划、环境感知和自主决策能力的测试场。

## 6. 实验设计

| 能力 | 命令 | 验证目标 |
|---|---|---|
| 多智能体闭环 | `python run.py --closed-loop-demo` | 攻击、环境、评测、防御、审计一键串通 |
| 攻击规划与失败反思 | `python run.py --attack-campaign --offline` | 验证 Attack Agent 能通过 reflection 扩大攻击面覆盖 |
| 防御自主决策 | `python run.py --defense-regression --offline` | 验证 Defense Agent 能降低 ASR 且不误伤正常请求 |
| 决策证据包 | `python run.py --evidence-pack --offline` | 生成收敛曲线、雷达图、消融实验和数据卡 |

## 7. 结果分析

| 指标 | 结果 | 说明 |
|---|---:|---|
| 初始 ASR | 44% | 未加固时，多类攻击可成功 |
| 收敛后 ASR | 0% | 7 轮精准加固后攻击成功率降至 0% |
| 攻击面覆盖 | 7/7 | Attack reflection 后覆盖全部威胁类别 |
| 精准加固误伤率 | 0% | 良性购物请求未被错误拦截 |
| 一刀切防御误伤率 | 100% | 证明需要智能体精准决策而不是简单全拦 |

## 8. 消融实验

| 对照组 | 结果 | 结论 |
|---|---|---|
| 完整系统 | ASR 收敛到 0%，攻击面覆盖 7/7 | 多智能体闭环有效 |
| 去掉 Defense Agent | ASR 保持 44% | 没有防御决策就不会产生安全收益 |
| 去掉 Attack reflection | 攻击面覆盖停在 2/7 | 失败反思是扩大覆盖面的关键 |

## 9. 创新点

1. **把安全任务转化为多智能体自治闭环**：攻击、评测、防御 Agent 分工协作。
2. **显式体现任务解析与步骤规划**：Attack Agent 生成攻击计划，Defense Agent 生成加固动作。
3. **环境感知可落地**：Evaluation Agent 读取响应、工具调用、guard decision 和审计记录。
4. **自主决策可验证**：Defense Agent 的加固选择直接通过 ASR 和误伤率回归验证。
5. **离线确定性复现**：无 API key 时仍可用 `--offline` 复现核心结论。

## 10. 边界与局限

- 本项目不接真实淘宝、真实支付、真实用户数据或真实外部攻击目标。
- 当前环境是本地 mock 电商场景，不代表生产系统集成已完成。
- 当前重点是竞赛级可复现的智能体闭环，未来可扩展更多行业环境和真实模型实测。

## 11. 复现方式

```powershell
python run.py --closed-loop-demo
python run.py --attack-campaign --offline
python run.py --defense-regression --offline
python run.py --evidence-pack --offline
python -m pytest -q
```

完整环境说明见 [`reproducibility.md`](./reproducibility.md)。
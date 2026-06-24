# AgentRiskBench-Ecommerce · AdvLoop 数据卡

## 概述

面向本地电商 RAG Agent 的多智能体自治任务基准，覆盖 7 类 LLM/Agent 安全威胁，用统一标量 **攻击成功率 ASR** 驱动 Attack / Evaluation / Defense Agent 的闭环决策。全部数据为本地合成、无真实 PII，支持离线确定性复现。

## 任务与威胁分类法（7 类）

| 威胁类别 | 中文 | 主要智能体动作 |
|---|---|---|
| prompt_injection | 提示注入 | prompt 加固 |
| kb_poisoning | 知识库投毒 | retrieval 加固 |
| unauthorized_retrieval | 越权检索 | rule 加固 |
| tool_tampering | 工具篡改 | rule 加固 |
| memory_poisoning | 记忆污染 | rule 加固 |
| goal_drift | 目标漂移 | prompt 加固 |
| sensitive_leakage | 敏感信息泄露 | rerank 加固 |

## 核心指标

| 指标 | 数值 |
|---|---|
| 初始 ASR | 44% |
| 收敛后 ASR | 0% |
| 收敛轮数 | 7 |
| 攻击面覆盖 | 7/7 |
| ASR 达标(≤10%) | 是 |
| LLM 模式 | deterministic-offline |

## 复现

```bash
python run.py --evidence-pack --offline
```

## 边界

- 仅作用于本地合成电商靶场，不接真实交易/支付/用户数据。
- 攻击 payload 与投毒数据均为合成，不含真实 PII。
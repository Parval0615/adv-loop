# MCP-Sentinel · AgentRiskBench-Ecommerce 数据卡

## 概述

面向电商 RAG Agent 的多智能体对抗安全基准,覆盖 7 类 LLM/Agent 安全威胁,用统一标量 **攻击成功率(ASR)** 驱动攻防自进化收敛。全部数据为本地合成、无真实 PII,离线确定性复现。

## 任务与威胁分类法（7 类）

| 威胁类别 | 中文 | 加固动作类型 |
|---|---|---|
| prompt_injection | 提示注入 | prompt |
| kb_poisoning | 知识库投毒 | retrieval |
| unauthorized_retrieval | 越权检索 | rule |
| tool_tampering | 工具篡改 | rule |
| memory_poisoning | 记忆污染 | rule |
| goal_drift | 目标漂移 | prompt |
| sensitive_leakage | 敏感信息泄露 | rerank |

## 核心指标

| 指标 | 数值 |
|---|---|
| 初始 ASR | 30% |
| 收敛后 ASR | 0% |
| 收敛轮数 | 7 |
| ASR 单调下降 | 是 |
| ASR 达标(≤10%) | 是 |
| LLM 模式 | deterministic-offline |

## 复现

```bash
python run.py --evidence-pack --offline   # 离线确定性复现
```

## 边界

- 仅作用于本地合成电商靶场,不接真实交易/支付/用户数据。
- 攻击 payload 与投毒数据均为合成,不含真实 PII。

# MCP-Sentinel 八分钟演示脚本

## 0:00–0:40 开场

各位老师好，我们的项目是 MCP-Sentinel，一个大模型驱动的多智能体安全自治系统。

它解决的问题是：当 LLM Agent 能调用工具、访问文件和网络、保存记忆并派发子 Agent 后，如何自动发现风险、分析损伤、选择加固动作并验证防御是否真正有效。

## 0:40–1:30 赛题能力

系统闭环是：

```text
任务解析 → 攻击规划 → 环境执行 → 风险评测
        → 防御决策 → 重新攻击 → 收敛判断 → 审计证据
```

Attack Agent 会根据失败历史反思和升级策略；Defense Agent 根据被攻破类别选择精确动作；Evaluation Agent 将 ASR、覆盖率和误伤率反馈给下一轮决策。

## 1:30–2:40 Attack Agent

运行：

```powershell
python run.py --attack-campaign --offline
```

讲解输出中的轮数、攻击面覆盖、首次覆盖数、反思增益和策略升级次数。重点不是载荷数量，而是 Agent 能根据未覆盖类别和失败结果改变下一步选择。

## 2:40–3:50 Defense Agent

运行：

```powershell
python run.py --defense-regression --offline
```

系统读取损伤报告，为不同威胁选择 prompt、rule、retrieval 或 rerank 加固，然后重放同一攻击战役并运行良性请求。展示加固前后 ASR、缓解率和精准加固误伤率。

## 3:50–5:00 自动评测与消融

运行：

```powershell
python run.py --evidence-pack --offline
```

打开本轮生成的收敛曲线、损伤雷达图和消融表：完整系统、去掉 Defense Agent、去掉 Attack reflection 三组结果说明防御决策和失败反思对闭环都有独立贡献。所有口头数字以当前生成的 JSON 为准。

## 5:00–6:00 闭环与审计

运行：

```powershell
python run.py --closed-loop-demo
```

展示三类受控风险的检测、clean/controlled 防御决策、审计链完整性和通过记录。再打开 trace 或控制台，说明每个工具调用、策略判断和跨 Agent 关系都可以追溯。

## 6:00–6:50 通用任务智能体补充

运行：

```powershell
python run.py --agent-demo --offline
```

`basic-search` 展示自然语言任务解析和工具调用；`replan-stock-recovery` 展示库存不足后根据 observation 生成新计划并成功执行替代动作。

赛事默认链路 = v2 / run.py。`invoke_ecommerce_agent()` 是 legacy 兼容入口，正式演示使用 `run.py` 与 `invoke_ecommerce_agent_v2()`。

需要主动说明：离线重规划场景使用脚本化双桩保证现场稳定，只证明编排闭环；真实大模型自主规划应使用有效 Qwen API 轨迹证明。

## 6:50–7:30 在线与离线边界

- 在线模式：真实模型参与解析、计划、动作选择和反思。
- 离线模式：确定性 fallback，适合 CI 和现场兜底。
- 两者共用同一执行器、工具、环境状态和证据格式，但不能混用指标。

## 7:30–8:00 收尾

MCP-Sentinel 的核心不是固定规则集合，而是一个能够理解目标、规划行动、感知结果、自主调整并证明效果的多智能体安全闭环。它以智能体运行安全这一实际问题，完整对应赛题的任务解析、规划、环境感知和自主决策要求。

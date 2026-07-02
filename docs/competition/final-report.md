# MCP-Sentinel：大模型驱动的多智能体安全自治系统

## 1. 项目定位

MCP-Sentinel 面向“生成式大语言模型与智能体”赛题，以 LLM Agent 运行安全为代表性实际问题。系统接收自然语言任务或安全目标后，由大模型参与结构化解析、计划生成、动作选择与失败反思；多个 Agent 读取工具和评测环境反馈，自主调整攻击或防御策略，直至达到目标或停止条件。

项目不是单一规则扫描器。它同时包含通用任务 Agent、Attack Agent、Defense Agent、Evaluation Agent、MCP 调用拦截流水线和可审计 trace，使“理解—规划—执行—观察—重规划—验证”成为统一闭环。

## 2. 实际问题与代表性场景

具备文件、网络、工具、记忆和子 Agent 能力的智能体可能受到提示注入、知识库投毒、越权检索、工具篡改、记忆污染、目标漂移和敏感信息泄露影响。人工枚举攻击、分析损伤和选择加固动作成本高，且很难持续验证策略是否有效、是否误伤正常业务。

MCP-Sentinel 使用两个本地场景验证解决方案：

1. 电商 RAG Agent：覆盖搜索、购物车、订单、模拟支付、退款、客服和商家操作，验证自然语言任务执行与业务安全策略。
2. MCP 研发助手靶场：覆盖文件、命令、模拟网络、模拟 Git 和子 Agent 派发，验证注入识别、工具治理和跨链路溯源。

所有业务与攻击数据均为本地合成，不连接真实交易或外部目标。

## 3. 多智能体闭环

```text
用户目标
  -> Task Agent：解析 goal、subgoals、constraints、entities，生成计划
  -> Attack Agent：选择攻击类别与载荷，执行并记录失败
  -> Evaluation Agent：分析轨迹、损伤、覆盖、ASR 与审计完整性
  -> Defense Agent：根据被攻破类别选择精确加固动作
  -> 重新执行攻击与良性回归
  -> 未达标则继续反思与重规划，达标后输出证据包
```

| Agent | 感知输入 | 自主决策 | 产物 |
|---|---|---|---|
| Task Agent | 用户指令、工具目录、业务 observation | 计划工具步骤、生成参数、失败后重规划 | TaskSpec、Plan、TaskRunResult |
| Attack Agent | 靶场状态、历史尝试、失败原因、未覆盖类别 | 选择候选载荷、升级攻击策略 | 战役历史、覆盖表、反思日志 |
| Defense Agent | 损伤报告、被攻破类别、候选加固动作 | 选择 prompt、rule、retrieval 或 rerank 加固 | 加固决策、回归报告 |
| Evaluation Agent | 攻防轨迹、审计事件、业务状态 | 判断攻击成功、误伤、目标达成和收敛 | 指标、曲线、雷达图、消融、数据卡 |

## 4. 大模型接入与离线复现

`SharedLLMClient` 读取以下 OpenAI-compatible 配置：

| 变量 | 用途 |
|---|---|
| `LLM_API_BASE` | 兼容 API endpoint |
| `LLM_API_KEY` | API 密钥 |
| `LLM_MODEL` | Qwen 等模型标识 |

在线模式用于证明真实模型参与任务解析、计划、动作选择和反思。未配置密钥或强制 `--offline` 时，系统使用确定性 fallback，保证相同输入和 seed 可稳定复现。离线证据用于验证工程闭环，不作为真实模型效果指标。

## 5. 关键实现

| 模块 | 职责 |
|---|---|
| `task_agent` | 通用任务解析、计划、ReAct 执行、观察、重规划、目标验证 |
| `auto_attack_system` | 七类威胁、载荷、攻击选择、失败反思和战役执行 |
| `auto_defense_system` | 防御候选、策略执行、最小权限、输入输出保护和审计 |
| `auto_evaluation_system` | sandbox、detector、闭环 runner、指标和证据生成 |
| `sentinel_proxy` | 工具、资源和子 Agent 调用的统一拦截 |
| `injection_radar` / `intent_aligner` | 多源注入检测与意图—计划—工具对齐 |
| `policy_dsl` | allow、ask、block 三态裁决 |
| `trace_dag` | 跨 MCP 与子 Agent 的 DAG、时间线和完整性证据 |

赛事默认链路 = v2 / run.py。`run.py --agent-demo`、`run.py --agent-task` 和 `invoke_ecommerce_agent_v2()` 使用 Task Agent 主链路；`invoke_ecommerce_agent()` 暂保留 legacy 关键词路由，仅用于旧单步电商接口兼容。

## 6. 可复现结果

当前离线命令覆盖以下证据：

| 命令 | 验证内容 |
|---|---|
| `python run.py --attack-campaign --offline` | Attack Agent 反思、升级与七类攻击面覆盖 |
| `python run.py --defense-regression --offline` | Defense Agent 精确加固、ASR 缓解和良性误伤回归 |
| `python run.py --evidence-pack --offline` | 收敛曲线、雷达图、消融和数据卡 |
| `python run.py --closed-loop-demo` | 三类受控风险的攻击—检测—防御—审计闭环 |
| `python run.py --agent-demo --offline` | 通用任务解析、真实工具调用和库存失败后的重规划 |

固定数字以 [`evidence-pack/`](evidence-pack/) 中当前代码重新生成的 JSON 为准。Markdown、图片和讲稿不得使用与 JSON 不一致的历史数字。

离线 `replan-stock-recovery` 场景使用脚本化 LLM 双桩稳定复现“库存不足 → observation → revision+1 → 替代商品”编排；它不作为真实大模型自主规划的证据。在线模型能力需要另行保存有效 API 轨迹。

## 7. 可靠性与安全设计

- 工具目录按角色过滤，未知工具和参数异常默认阻断。
- 输入、输出、工具、目标和记忆均有独立 guard。
- 高风险动作由服务端重新校验业务状态，不接受模型自行声明的金额或权限。
- blocked、缺货、预算超限和工具异常进入 observation，可触发重规划。
- trace DAG、审计哈希链和完整性摘要支持答辩复盘。

## 8. 已知边界

- 当前靶场是本地合成环境，不是生产 MCP 网关或真实电商平台。
- 固定证据以确定性离线模式生成；Qwen 在线批量指标仍需有效 API 和独立轨迹。
- 默认任务评测集规模较小，正式实验应扩展多步骤、失败恢复和越权场景，并保留每条任务的 store 状态。
- 当前控制台是本地静态复盘产物，不代表完整 SaaS 管理平台。

## 9. 结论

MCP-Sentinel 将大模型任务理解与多个 Agent 的自主行动结合，用于解决智能体运行安全评估和加固问题。其核心价值不是一次性检测，而是能读取环境反馈、调整策略、重复验证并输出可追溯证据的自治闭环。

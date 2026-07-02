# 大模型驱动电商自治任务智能体 Spec

## Why
现有系统的电商主入口、攻防规划和部分评测逻辑仍以关键词路由、查表和阈值比较模拟“智能”，无法充分支撑赛事一对复杂指令解析、规划执行、环境感知和自主决策的要求。需要在保留真实电商状态机、安全策略和离线可复现能力的基础上，新增一个由 LLM 决策驱动的 Plan-Execute-Replan 自治任务智能体。

## What Changes
- 扩展 `auto_attack_system/src/auto_attack_system/llm_client.py`，在不破坏 `complete()` 的前提下新增 `complete_json()`、`decide()` 和确定性 JSON 兜底。
- 新增顶层包 `task_agent/`，包含数据模型、工具目录、任务解析、计划生成、执行器、重规划器、编排器、轨迹适配器、提示词和测试。
- 将真实电商工具封装为 LLM 可选工具目录，复用 `auto_defense_system/src/auto_defense_system/ecommerce_agent/store.py` 与 `tools.py`，不重写业务状态机。
- 新增 TaskAgent 的 ReAct 执行循环，按真实 `ToolExecution` 的 `blocked`、`answer`、`value`、`risk_level` 做环境感知，并在失败、拦截、缺货、超预算等条件下触发重规划。
- 在 `run.py` 增加 `--agent-task` 与 `--agent-demo`，输出任务摘要并通过 `trace_dag` 生成规划 DAG、timeline 和完整性证据。
- 改造电商主入口为 `invoke_ecommerce_agent_v2`，主链路使用 TaskAgent，保留旧 `_route_message` 作为离线或兼容兜底。
- 将 `defense_agent.py`、`attack_agent.py`、`threat_taxonomy.py` 和 `agent/react.py` 中的查表、机械递增、阈值判定或关键词路由降级为候选池或 legacy 兜底。
- 新增任务成功率评测与竞赛报告、答辩脚本，主叙事从“安全攻防”调整为“电商领域自治智能体”，安全作为可靠性子系统呈现。

## Impact
- Affected specs: 赛事一“生成式大语言模型与智能体”；电商任务执行；安全可靠性子系统；任务评测与证据包。
- Affected code:
  - `auto_attack_system/src/auto_attack_system/llm_client.py`
  - `task_agent/`
  - `run.py`
  - `pyproject.toml`
  - `auto_defense_system/src/auto_defense_system/ecommerce_agent/agent.py`
  - `auto_defense_system/src/auto_defense_system/ecommerce_agent/tools.py`
  - `auto_defense_system/src/auto_defense_system/defense_agent.py`
  - `auto_attack_system/src/auto_attack_system/attack_agent.py`
  - `auto_attack_system/src/auto_attack_system/threat_taxonomy.py`
  - `auto_defense_system/src/auto_defense_system/agent/react.py`
  - `trace_dag/builder.py` 的现有 schema 适配调用点
  - `auto_evaluation_system/src/auto_evaluation_system/`
  - `docs/competition/final-report.md`
  - `docs/competition/comp1-agent-demo-script.md`
- 核对结果: 当前真实电商模块位于 `auto_defense_system/src/auto_defense_system/ecommerce_agent/`；当前 `tools.py` 核对到 13 个公开 `ToolExecution` 工具函数，工具目录以当前代码为准，若实现阶段发现新增公开工具则纳入目录和测试。
- 非目标: 不替换现有电商状态机，不删除旧兼容入口，不将安全攻防重新扩展为主线。

## ADDED Requirements

### Requirement: LLM JSON 决策引擎
系统必须提供结构化 JSON 补全和候选动作决策能力，使上层模块可以得到可解析、可校验、可复现的决策结果。

#### Scenario: 在线 JSON 正常返回
- **WHEN** 调用 `SharedLLMClient.complete_json(system, user, schema_hint=...)` 且在线模型返回合法 JSON
- **THEN** 系统返回 `dict`，并保留调用方要求的结构化字段。

#### Scenario: JSON 解析失败后重试
- **WHEN** 首次在线返回不可解析 JSON
- **THEN** 系统使用 `seed + 1` 重试一次。
- **AND** 若重试成功，返回第二次结果。
- **AND** 若仍失败或在线异常，返回确定性兜底结构，不抛未捕获异常。

#### Scenario: 候选决策强约束
- **WHEN** 调用 `SharedLLMClient.decide(..., choices=[...])`
- **THEN** 返回 `{"choice": <choices 之一>, "reason": str, "confidence": float}`。
- **AND** 若模型选择非法项，系统回退到 `choices[0]` 并在 reason 中标记 fallback。

#### Scenario: 离线确定性
- **WHEN** `force_offline=True` 或没有 API key
- **THEN** `complete_json()` 与 `decide()` 对相同输入和 seed 返回一致结果。

### Requirement: TaskAgent 数据模型
系统必须定义任务解析、规划、观察、轨迹和最终结果的数据结构，作为规划、执行、重规划、可视化和评测的共同契约。

#### Scenario: 任务解析结果可被后续模块消费
- **WHEN** `parse_task()` 返回 `TaskSpec`
- **THEN** 结果包含 `raw_instruction`、`goal`、`subgoals`、`constraints`、`entities`、`parse_mode`。

#### Scenario: 执行轨迹记录完整决策链
- **WHEN** 执行一个 `PlanStep`
- **THEN** `TaskStep` 记录 thought、action tool、action args、decision reason、Observation 和是否触发重规划。

### Requirement: 真实电商工具目录
系统必须把现有电商工具层封装成可由 LLM 选择的工具目录，并按角色过滤不可用工具。

#### Scenario: 买家工具目录不包含商家工具
- **WHEN** 调用 `catalog_for_role("buyer")`
- **THEN** 返回目录不包含 `merchant_update_price` 和 `merchant_update_stock`。

#### Scenario: 工具调用复用真实业务逻辑
- **WHEN** 调用 `tool_registry.invoke("cart_add_item", args, store=..., user_id=..., role=...)`
- **THEN** 系统调用 `auto_defense_system.ecommerce_agent.tools.cart_add_item()` 并返回原始 `ToolExecution` 语义。

#### Scenario: 未知工具被安全阻断
- **WHEN** LLM 选择未知工具名
- **THEN** `invoke()` 返回 `blocked=True` 的 `ToolExecution`，并给出可解释原因。

### Requirement: 复杂任务解析与有序计划生成
系统必须将自然语言购物指令解析为 `TaskSpec`，并基于角色可见工具目录生成有序 `Plan`。

#### Scenario: 多目标购物指令解析
- **WHEN** 用户输入“找800元内降噪耳机，比价后下单，再处理我上次的退款”
- **THEN** `TaskSpec.subgoals` 至少包含搜索/比价、下单、退款三类子目标。

#### Scenario: 计划只引用合法工具
- **WHEN** `make_plan(spec, role="buyer", llm=...)` 生成 `PlanStep`
- **THEN** 每个 `candidate_tool` 都来自 `catalog_for_role("buyer")`。

### Requirement: ReAct 执行与环境感知
系统必须通过模型生成 thought、选择工具、生成参数，再读取真实工具返回形成 `Observation`。

#### Scenario: 执行一步会改变真实状态
- **WHEN** 执行包含 `cart_add_item` 的 `PlanStep`
- **THEN** 对应用户购物车在 `EcommerceStore` 中发生真实变化。

#### Scenario: 观察结果保留风控信号
- **WHEN** 真实工具被 policy、tool guard 或 goal guard 拦截
- **THEN** `Observation.blocked=True`，并保留 `answer`、`risk_level` 和结构化摘要。

### Requirement: 自主重规划
系统必须基于观察结果判断是否重规划，并让 LLM 基于主目标、历史轨迹和失败诊断生成替代计划。

#### Scenario: 预算不足触发重规划
- **WHEN** 工具结果显示下单或支付金额超过 `constraints["budget_cents"]`
- **THEN** `should_replan()` 返回 `(True, <诊断文本>)`。
- **AND** `replan()` 返回 `revision=上一版本+1` 的新计划。

#### Scenario: 缺货后选择替代方案
- **WHEN** 目标商品缺货或搜索无匹配结果
- **THEN** 系统触发重规划，优先尝试有货同类商品、优惠券、数量调整或客服工单等替代路径。

#### Scenario: 重规划有上限
- **WHEN** 连续失败导致多次重规划
- **THEN** `TaskAgent.run()` 不超过 `max_replans`，并在 `final_answer` 中说明未达成原因。

### Requirement: TaskAgent 编排结果
系统必须提供 `TaskAgent.run()`，完整串联解析、规划、执行、重规划、总结和目标验证。

#### Scenario: 离线端到端可复现
- **WHEN** 使用 `TaskAgent(force_offline=True).run(instruction)`
- **THEN** 系统返回 `TaskRunResult`，包含所有计划版本、轨迹、最终答复、目标达成状态、重规划次数和 LLM 模式。

#### Scenario: 目标达成判定可解释
- **WHEN** 任务结束
- **THEN** `_verify_goal()` 结合真实状态规则和 LLM JSON 判定，输出布尔结果供评测复用。

### Requirement: CLI 与规划可视化
系统必须提供一键运行入口，并把 TaskAgent 轨迹适配到现有 `trace_dag` 证据格式。

#### Scenario: 单任务 CLI
- **WHEN** 执行 `python run.py --agent-task "找800元内降噪耳机比价后下单" --offline`
- **THEN** 系统完成任务运行，打印 goal、subgoals 数、步骤数、工具调用数、重规划次数、goal_achieved、llm_mode。
- **AND** 系统落盘 `trace_graph.md`、`trace_timeline.jsonl`、`trace_integrity.json` 等 trace artifacts。

#### Scenario: Demo 至少包含重规划
- **WHEN** 执行 `python run.py --agent-demo --offline`
- **THEN** 至少一个预设场景触发重规划，并在输出和 trace 中可见。

### Requirement: 任务成功率评测
系统必须新增任务级评测，输出任务达成率、平均步数、重规划触发率、重规划成功率、无效工具调用率。

#### Scenario: 客观规则和 LLM judge 结合
- **WHEN** 评测 TaskAgent 运行结果
- **THEN** 系统同时读取 `TaskRunResult`、真实 `EcommerceStore` 状态和 `llm.complete_json()` judge 结果，生成可复核指标。

### Requirement: 竞赛交付材料
系统必须更新报告和答辩脚本，将主线聚焦于电商领域自治任务智能体，安全能力作为可靠性保障呈现。

#### Scenario: 报告主线对齐赛题
- **WHEN** 阅读 `docs/competition/final-report.md`
- **THEN** 报告标题和章节围绕任务解析、自主规划、环境感知、动态重规划、目标达成展开。

#### Scenario: 答辩脚本可现场演示
- **WHEN** 阅读 `docs/competition/comp1-agent-demo-script.md`
- **THEN** 脚本包含复杂指令输入、规划 DAG 展示、预算或缺货重规划、安全事件绕行和双线复现说明。

## MODIFIED Requirements

### Requirement: 电商主入口默认使用 TaskAgent
`auto_defense_system/src/auto_defense_system/ecommerce_agent/agent.py` 必须新增 `invoke_ecommerce_agent_v2()`，在主链路中使用 `TaskAgent.run(message)` 驱动工具选择与执行。原 `invoke_ecommerce_agent()` 和 `_route_message()` 保留为兼容兜底，输入防火墙与目标漂移拦截继续生效。

#### Scenario: 兼容旧返回结构
- **WHEN** 调用新入口处理普通买家消息
- **THEN** 返回结构仍可表达 `answer`、`tool_calls`、`business_events`、`audit_events`、`blocked`、`risk_level`。

### Requirement: 攻防子系统候选池由 LLM 选择
`defense_agent.py::harden()`、`attack_agent.py::_reflect()`、`attack_agent.py::_plan()` 和 `threat_taxonomy.py::SyntheticTarget.attempt()` 必须把查表、机械递增或阈值逻辑降级为候选池/离线兜底，在线或非强制离线场景由 `SharedLLMClient.decide()` 或 `complete_json()` 产生选择。

#### Scenario: 删除模型后行为显著退化
- **WHEN** 对比在线/LLM 决策路径与强制离线路径
- **THEN** 规划、反思、加固或判定结果在可解释范围内体现模型决策差异，支持消融论证。

### Requirement: legacy ReAct 标记
`auto_defense_system/src/auto_defense_system/agent/react.py` 必须标记为 legacy，避免作为赛事一主链路展示；主链路统一指向 `task_agent/executor.py`。

### Requirement: 工程入口与测试配置
`run.py` 必须支持 TaskAgent 子命令；`pyproject.toml` 必须确保 `task_agent/tests` 被 pytest 收集；`.env.example` 如存在必须补充 Qwen 兼容模式示例。

## REMOVED Requirements

### Requirement: 关键词路由作为电商智能主实现
**Reason**: 关键词路由无法证明复杂任务解析、规划、环境感知和自主决策，且是答辩中的核心风险点。
**Migration**: 保留 `_route_message()` 作为兼容兜底；新增 `invoke_ecommerce_agent_v2()` 和 CLI 入口作为赛事主链路。

### Requirement: 查表和阈值比较作为攻防决策主实现
**Reason**: 固定 playbook、ladder index 递增和 `ladder_index >= threshold` 只能表达确定性流程，不能支撑“模型参与决策”的消融论证。
**Migration**: 将原有表和阈值转为离线兜底或候选池；在线/主链路由 `SharedLLMClient.decide()`、`complete_json()` 或 LLM-as-judge 驱动。

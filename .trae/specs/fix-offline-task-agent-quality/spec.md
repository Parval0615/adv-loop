# 离线 TaskAgent 质量修复 Spec

## Why
修复前旗舰离线指令 `找800元内降噪耳机比价后下单` 可运行但 `GOAL_ACHIEVED=False`，直接削弱“离线可复现”和答辩现场演示可信度。根因集中在搜索词清洗过弱、离线重规划未复用稳定多步计划、离线决策被上层强制首项覆盖，以及任务评测能力未接入 CLI。

## What Changes
- P0: 强化 `task_agent/agent.py::_search_query()`，剥离预算、比价和流程类噪声，确保旗舰指令搜索词稳定为 `降噪耳机` 并命中真实商品。
- P0: 在 `TaskAgent.run()` 的重规划分支复用离线稳定器，避免离线 `replan()` 退化为单步随机工具计划。
- P0: 扩展离线稳定器，使搜索无匹配、缺货、预算约束等失败信号能产生有意义的 search -> cart -> create_order 路径。
- P1: 移除攻防上层对 `offline=True` 的 `choices[0]` 强制覆盖，改为信任 `SharedLLMClient.decide()` 的确定性哈希选择；非法选择才回退首项。
- P2: 为 `run.py` 增加 `--task-eval` 和 `--task-file`，调用已有 `auto_evaluation_system.task_eval.evaluate_task_runs()` 输出批量任务指标和 JSON 报告。
- P2: 统一或显式标注电商公开入口策略；默认推荐让 `invoke_ecommerce_agent()` 委托 `invoke_ecommerce_agent_v2()`，旧关键词路由仅作异常兜底。
- 更新报告中“批量任务评测待补”部分，回填 `--task-eval --offline` 的真实指标或明确剩余在线数据边界。

## Impact
- Affected specs: `build-autonomous-task-agent` 的离线复现、重规划质量、去查表化证据、批量评测能力。
- Affected code:
  - `task_agent/agent.py`
  - `task_agent/replanner.py`
  - `task_agent/tests/test_agent_e2e.py`
  - `task_agent/tests/test_replanner.py`
  - `auto_attack_system/src/auto_attack_system/attack_agent.py`
  - `auto_defense_system/src/auto_defense_system/defense_agent.py`
  - `auto_attack_system/tests/test_comp2_campaign.py`
  - `auto_defense_system/tests/test_comp3_defense.py`
  - `run.py`
  - `auto_evaluation_system/src/auto_evaluation_system/task_eval.py` 的调用点
  - `auto_evaluation_system/tests/` 或 `task_agent/tests/` 中新增 CLI 评测测试
  - `auto_defense_system/src/auto_defense_system/ecommerce_agent/agent.py`
  - `auto_defense_system/tests/test_ecommerce_agent.py`
  - `docs/competition/final-report.md`
- 非目标:
  - 不重写电商 `EcommerceStore` 或工具层业务逻辑。
  - 不改变 `SharedLLMClient.decide()` 的候选校验契约。
  - 不引入在线 API 作为离线验收前提。

## ADDED Requirements

### Requirement: 旗舰离线指令稳定达成
系统必须在离线模式下完成 `找800元内降噪耳机比价后下单`，并输出可解释的真实工具轨迹。

#### Scenario: 旗舰离线任务达成
- **WHEN** 执行 `python run.py --agent-task "找800元内降噪耳机比价后下单" --offline`
- **THEN** 输出 `GOAL_ACHIEVED=True`。
- **AND** trace 至少包含成功的 `product_search`、`cart_add_item`、`create_order`。
- **AND** 若包含预算或库存失败，重规划必须产生有意义的替代路径，而不是直接跳到无订单支付。

### Requirement: 搜索词清洗剥离预算和流程噪声
系统必须从购物指令中提取适合 `EcommerceStore.search_products()` 的名词性 query，预算信息保留在 constraints 中，不进入搜索词。

#### Scenario: 预算和流程词被剥离
- **WHEN** `_search_query()` 处理 `找800元内降噪耳机比价后下单`
- **THEN** 返回 `降噪耳机`。
- **AND** `store.search_products("降噪耳机")` 命中 `p1001`。

#### Scenario: 兜底逻辑保持可用
- **WHEN** 指令没有可提取商品词
- **THEN** `_search_query()` 仍返回非空兜底字符串，不破坏现有搜索类任务。

### Requirement: 离线重规划复用稳定多步计划
系统必须在 `replan()` 返回后，对 deterministic fallback 场景再次执行离线计划稳定化，保证重规划路径仍是可执行的多步工具链。

#### Scenario: 搜索无匹配后重规划
- **WHEN** 上一步 observation 显示 `product_search` 无匹配或 query 过窄
- **THEN** 重规划使用放宽后的 query 重试搜索。
- **AND** 若找到商品，则继续生成 `cart_add_item` 和必要的 `create_order` 步骤。

#### Scenario: 缺货后重规划
- **WHEN** 上一步 observation 显示缺货或 stock 为 0
- **THEN** 重规划选择有货同类商品或客服工单等可解释替代路径。
- **AND** 不允许生成只有 `mock_payment` 且没有订单上下文的单步计划。

### Requirement: 离线候选决策差异化且可复现
系统必须让离线模式保留 `SharedLLMClient.decide()` 的确定性哈希选择能力，使不同上下文可选择不同候选，同时保持同输入同 seed 可复现。

#### Scenario: 防御动作离线不强制首项
- **WHEN** `DefenseAgent._choose_action()` 在离线模式下处理不同 category
- **THEN** 候选选择来自 `llm.decide()` 的合法 choice。
- **AND** 只有 choice 非法或异常时才回退到 `choices[0]`。

#### Scenario: 攻击反思离线不强制首项
- **WHEN** `AttackAgent._reflect()` 在离线模式下处理不同失败诊断
- **THEN** 升级、重试或停止选择来自 `llm.decide()` 的合法 choice。
- **AND** 选择结果对同 category、round、seed 稳定可复现。

### Requirement: 批量任务评测 CLI
系统必须提供一键批量任务评测入口，复用已有 `TaskEvaluationReport` 结构输出指标和落盘 JSON。

#### Scenario: 默认批量评测
- **WHEN** 执行 `python run.py --task-eval --offline`
- **THEN** 系统运行内置 3-5 条任务集。
- **AND** 打印 `task_achievement_rate`、`average_steps`、`replan_success_rate`、`invalid_tool_call_rate`。
- **AND** 在结果目录落盘 `task_evaluation_report.json`。

#### Scenario: 文件驱动批量评测
- **WHEN** 执行 `python run.py --task-eval --task-file <path> --offline`
- **THEN** 系统从 txt 或 JSON 文件读取指令集。
- **AND** 每条指令生成 `TaskRunResult` 并纳入 `evaluate_task_runs()`。

### Requirement: 批量评测结果回填报告
报告必须用真实 `--task-eval --offline` 产物替换“批量任务评测待补”描述，避免交付材料与代码能力不一致。

#### Scenario: 报告指标可复核
- **WHEN** 阅读 `docs/competition/final-report.md`
- **THEN** 能看到离线批量评测命令、输出指标、报告路径或样例数值。
- **AND** 在线 Qwen 数据仍可标注为需要 API key 的待补项。

## MODIFIED Requirements

### Requirement: TaskAgent 离线计划稳定器
`TaskAgent._stabilize_offline_plan()` 必须同时服务首轮计划和重规划计划，并能结合失败原因、上一步 observation 和任务目标修正工具序列。

#### Scenario: 重规划后仍是多步可执行计划
- **WHEN** deterministic fallback 下 `replan()` 返回单步或非法上下文计划
- **THEN** 稳定器将其修正为角色合法、上下文完整的计划。

### Requirement: 公开电商入口策略
公开 `invoke_ecommerce_agent()` 必须消除“默认走 legacy 关键词路由”的歧义。推荐改为委托 `invoke_ecommerce_agent_v2(force_offline=True)`，旧 `_route_message()` 仅作为异常兜底；若为兼容保留旧默认行为，报告和脚本必须明确默认演示链路是 v2 和 `run.py`。

#### Scenario: 老测试不回归
- **WHEN** 运行 `pytest -q auto_defense_system/tests/test_ecommerce_agent.py`
- **THEN** 旧用例仍通过，新增用例证明公开入口策略与文档一致。

### Requirement: 回归底线
每个实现阶段必须至少运行本阶段专项测试；最终必须运行全量相关测试和两条 CLI 验收命令。

#### Scenario: 最终回归通过
- **WHEN** 修复完成
- **THEN** `python -m pytest -q` 或当前仓库可用的全量测试命令通过。
- **AND** `python run.py --agent-demo --offline` 通过。
- **AND** `python run.py --agent-task "找800元内降噪耳机比价后下单" --offline` 通过且 `GOAL_ACHIEVED=True`。
- **AND** `python run.py --task-eval --offline` 通过并落盘报告。

## REMOVED Requirements

### Requirement: 离线决策上层强制首项
**Reason**: `SharedLLMClient.decide()` 已提供确定性哈希选择，上层再用 `offline -> choices[0]` 会抹掉离线可见的候选择优证据。
**Migration**: 删除防御和攻击反思中的 offline 首项覆盖；保留非法 choice 和异常场景的首项兜底。

### Requirement: 批量评测只能通过 Python API 使用
**Reason**: 仅有 `evaluate_task_runs()` 无 CLI 无法一键产出赛事报告所需指标。
**Migration**: 新增 `run.py --task-eval`，继续保留 Python API 供测试和扩展使用。

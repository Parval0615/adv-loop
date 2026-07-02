# Tasks

- [x] Task 1: 建立失败复现基线
  - [x] SubTask 1.1: 运行 `python run.py --agent-task "找800元内降噪耳机比价后下单" --offline`，记录当前 `GOAL_ACHIEVED`、工具轨迹和失败原因。
  - [x] SubTask 1.2: 用单元方式验证 `_search_query()` 当前对旗舰指令会产生包含预算/流程噪声的 query。
  - [x] SubTask 1.3: 检查 `TaskAgent.run()` 重规划分支确认 `replan()` 返回后未再次稳定化。
  - 描述: 先固定失败证据，避免后续只修局部但没有证明旗舰链路变绿。
  - Prompt: “请只做复现和最小测试准备，不修改业务逻辑；输出当前失败轨迹、搜索 query 和重规划退化证据。”
  - 验证: `python run.py --agent-task "找800元内降噪耳机比价后下单" --offline`

- [x] Task 2: 修复 `_search_query()` 搜索词清洗
  - [x] SubTask 2.1: 在 `task_agent/agent.py::_search_query()` 增加预算数字清洗，剥离 `\d+\s*元(内|以内)?`、`\d+\s*块(钱)?` 等价格串。
  - [x] SubTask 2.2: 扩充流程/预算/比较类停用词，包括 `元内`、`元以内`、`预算`、`比价`、`对比`、`之后`、`后`、`以内`、`块钱`、`块`。
  - [x] SubTask 2.3: 保留名词性商品词，确保旗舰指令 query 为 `降噪耳机`。
  - [x] SubTask 2.4: 新增或扩展 `task_agent/tests/test_agent_e2e.py` / 专项测试，覆盖旗舰 query 清洗和 `store.search_products("降噪耳机")` 命中 `p1001`。
  - 描述: 这是 P0 最小修复，预期单独即可让旗舰指令搜索命中。
  - Prompt: “请只改搜索词清洗和相关测试；不要改 store 或工具层，不要把指令关键词硬编码为固定商品 ID。”
  - 验证: `pytest -q task_agent/tests/test_agent_e2e.py`

- [x] Task 3: 修复离线重规划稳定器复用
  - [x] SubTask 3.1: 在 `TaskAgent.run()` 的重规划分支中，`replan()` 返回后若 `_uses_deterministic_fallback(task_spec)` 为真，则再次执行离线稳定化。
  - [x] SubTask 3.2: 允许稳定器接收失败上下文，或新增 `_stabilize_offline_replan()`，根据失败类型修正搜索 query、商品选择和工具序列。
  - [x] SubTask 3.3: 对搜索无匹配场景使用放宽后的 `_search_query()` 重试，避免直接跳到 `mock_payment`。
  - [x] SubTask 3.4: 对缺货场景选择有货同类商品；无法选择时转客服工单或给出明确失败，不生成无订单支付。
  - [x] SubTask 3.5: 新增测试覆盖搜索无匹配重规划、缺货重规划、重规划后无单步 `mock_payment`。
  - 描述: 这是 P0 治本修复，保证其它离线重规划任务不退化为随机单步工具。
  - Prompt: “请复用现有 Plan/PlanStep/Observation 结构做最小扩展；规则只用于 deterministic fallback 稳定器，不影响在线模型正常重规划。”
  - 验证: `pytest -q task_agent/tests/test_agent_e2e.py task_agent/tests/test_replanner.py`

- [x] Task 4: 修复离线去查表化证据
  - [x] SubTask 4.1: 在 `auto_defense_system/src/auto_defense_system/defense_agent.py::_choose_action()` 删除 `offline -> choices[0]` 覆盖，只在非法 choice 或异常时回退。
  - [x] SubTask 4.2: 在 `auto_attack_system/src/auto_attack_system/attack_agent.py::_reflect()` 删除 `offline -> fallback_choice` 覆盖，只在非法 choice 或异常时回退。
  - [x] SubTask 4.3: 审查 `_plan()` 和 `task_agent/executor.py::_decide_action()`，确认它们不再额外覆盖 `llm.decide()` 的合法离线 choice；如有同类覆盖则按同一规则修正。
  - [x] SubTask 4.4: 增加测试证明离线同输入可复现、不同 category/上下文可出现差异化合法选择。
  - 描述: P1 修复，让“去查表化”在离线评审路径上也有可复核证据。
  - Prompt: “请信任 `SharedLLMClient.decide()` 的确定性哈希选择；不要引入随机性，不要破坏非法选择首项兜底。”
  - 验证: `pytest -q auto_attack_system/tests auto_defense_system/tests/test_comp3_defense.py task_agent/tests/test_executor.py`

- [x] Task 5: 接入批量任务评测 CLI
  - [x] SubTask 5.1: 在 `run.py::_parse_args()` 新增 `--task-eval` 和 `--task-file`。
  - [x] SubTask 5.2: 新增主流程分支：读取内置默认任务或任务文件，逐条运行 `TaskAgent(force_offline=args.offline)`。
  - [x] SubTask 5.3: 调用 `auto_evaluation_system.task_eval.evaluate_task_runs()` 生成 `TaskEvaluationReport`。
  - [x] SubTask 5.4: 落盘 `task_evaluation_report.json`，并打印 `_print_task_eval_summary()`，至少包含 `task_achievement_rate`、`average_steps`、`replan_success_rate`、`invalid_tool_call_rate`。
  - [x] SubTask 5.5: 支持 txt 每行一条指令和 JSON 数组两种 `--task-file` 输入；空文件给出清晰错误。
  - [x] SubTask 5.6: 增加 CLI 测试覆盖默认任务集、txt/json 任务文件和报告落盘。
  - 描述: P2 修复，把已有评测 API 变成一键产出赛事指标的入口。
  - Prompt: “请复用现有 `TaskEvaluationReport`，CLI 输出要稳定；不要改 evaluator 指标语义，除非测试证明必须。”
  - 验证: `python run.py --task-eval --offline`

- [x] Task 6: 统一或标注公开电商入口
  - [x] SubTask 6.1: 评估 `invoke_ecommerce_agent()` 改为委托 `invoke_ecommerce_agent_v2(force_offline=True)` 对老测试的影响。
  - [x] SubTask 6.2: 若老测试可兼容，则将公开入口默认委托 v2，legacy `_route_message()` 仅作异常兜底。
  - [x] SubTask 6.3: 若兼容成本过高，则保留旧默认行为，但在 `docs/competition/final-report.md` 和答辩脚本明确“赛事默认链路 = v2 / run.py”。
  - [x] SubTask 6.4: 增加测试证明公开入口策略与文档一致，且旧用例不回归。
  - 描述: P2 收尾，消除 legacy/v2 双入口歧义。
  - Prompt: “优先选择最小可兼容改法；不要删除 legacy 路由，必要时保留为显式 fallback。”
  - 验证: `pytest -q auto_defense_system/tests/test_ecommerce_agent.py`

- [x] Task 7: 回填报告中的批量评测结果
  - [x] SubTask 7.1: 运行 `python run.py --task-eval --offline` 获取真实指标和报告路径。
  - [x] SubTask 7.2: 更新 `docs/competition/final-report.md` 中“批量任务评测汇总待补”描述，回填离线指标或样例数值。
  - [x] SubTask 7.3: 保留 Qwen 在线真实轨迹为需要 API key 的明确边界，不虚构在线指标。
  - 描述: 让报告与新 CLI 能力一致，减少答辩材料“待补”项。
  - Prompt: “请只写真实跑出的离线指标；没有运行证据的数据必须继续标注待补。”
  - 验证: `rg -n "批量任务评测汇总|task_achievement_rate|task_evaluation_report" docs/competition/final-report.md`

- [x] Task 8: 最终回归验收
  - [x] SubTask 8.1: 运行 `python -m pytest -q`，若环境全量不可用则运行并记录当前仓库可用全量命令。
  - [x] SubTask 8.2: 运行 `python run.py --agent-demo --offline`。
  - [x] SubTask 8.3: 运行 `python run.py --agent-task "找800元内降噪耳机比价后下单" --offline`，确认 `GOAL_ACHIEVED=True`。
  - [x] SubTask 8.4: 运行 `python run.py --task-eval --offline`，确认指标打印与 JSON 落盘。
  - [x] SubTask 8.5: 检查所有 checklist 通过后再返回。
  - 描述: 最终验收必须覆盖旗舰任务、demo、批量评测和测试回归。
  - Prompt: “请执行完整验证；只修复与本规格直接相关的问题，不做无关重构。”
  - 验证: `python -m pytest -q && python run.py --agent-demo --offline && python run.py --agent-task "找800元内降噪耳机比价后下单" --offline && python run.py --task-eval --offline`

# Task Dependencies
- Task 2 depends on Task 1。
- Task 3 depends on Task 1 and Task 2。
- Task 4 depends on Task 1。
- Task 5 depends on Task 1。
- Task 6 depends on Task 1。
- Task 7 depends on Task 5。
- Task 8 depends on Tasks 2-7。

# Parallelization Notes
- Task 2 and Task 4 can run in parallel after Task 1 because they touch different files.
- Task 5 and Task 6 can also run in parallel after Task 1 if tests are kept scoped.
- Task 3 should wait for Task 2 so重规划稳定器使用修复后的 query 提取。
- Task 7 should wait for Task 5 so报告使用真实 CLI 产物。

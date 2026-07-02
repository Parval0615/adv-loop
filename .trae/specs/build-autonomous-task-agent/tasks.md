# Tasks

- [x] Task 1: 建立基线核对与测试入口
  - [x] SubTask 1.1: 记录当前关键路径事实：`llm_client.py` 仅有文本 `complete()`，`run.py` 尚无 TaskAgent 参数，电商工具位于 `auto_defense_system/src/auto_defense_system/ecommerce_agent/`。
  - [x] SubTask 1.2: 确认当前公开电商工具函数清单，并以实现时 `tools.py` 为准生成 `TOOL_CATALOG`。
  - [x] SubTask 1.3: 确认 `pyproject.toml` 的 pytest 收集路径，并规划新增 `task_agent/tests`。
  - 描述: 该任务不做功能改造，只消除路径和工具数量的不确定性，防止后续实现按错误路径落地。
  - Prompt: “请核对仓库现状并形成实现前事实清单；不要重构业务代码，只确认路径、工具函数、测试收集配置和可能影响实现的约束。”
  - 验证: `rg -n "def complete|def _route_message|^def .*ToolExecution|testpaths" auto_attack_system auto_defense_system pyproject.toml`

- [x] Task 2: 扩展 `SharedLLMClient` 为 JSON 决策引擎
  - [x] SubTask 2.1: 在 `auto_attack_system/src/auto_attack_system/llm_client.py` 新增 `complete_json(system, user, *, schema_hint, seed=0, max_tokens=1024) -> dict`。
  - [x] SubTask 2.2: 新增 `decide(system, user, *, choices, seed=0) -> dict`，强制 `choice in choices`，非法选择回退 `choices[0]`。
  - [x] SubTask 2.3: 新增 `_deterministic_json()`，保证离线输出可解析、同 seed 稳定。
  - [x] SubTask 2.4: 在线 JSON 调用使用 `response_format={"type": "json_object"}`；解析失败重试一次，再兜底。
  - [x] SubTask 2.5: 新增 `task_agent/tests/test_llm_decide.py` 覆盖合法选择、非法回退、离线确定性、坏 JSON 重试。
  - 描述: 这是所有后续规划、执行、重规划和 judge 的基础能力，必须先完成。
  - Prompt: “请只改 LLM 客户端和对应测试；保持 `complete()` 兼容，不引入硬依赖在线 API，所有异常都必须返回可解析结构。”
  - 验证: `pytest -q task_agent/tests/test_llm_decide.py`

- [x] Task 3: 新增 `task_agent` 数据模型与提示词
  - [x] SubTask 3.1: 新建 `task_agent/__init__.py`、`task_agent/models.py`、`task_agent/prompts.py`。
  - [x] SubTask 3.2: 在 `models.py` 定义 `TaskSpec`、`PlanStep`、`Plan`、`Observation`、`TaskStep`、`TaskRunResult`。
  - [x] SubTask 3.3: 在 `prompts.py` 定义任务解析、计划生成、执行思考、参数生成、重规划、最终总结和目标判定提示词。
  - [x] SubTask 3.4: 保持 dataclass 字段与 `spec.md` 契约一致，避免后续 trace/eval 各自定义重复结构。
  - 描述: 建立跨模块共享契约，后续 planner、executor、trace_adapter 和 eval 均依赖这些模型。
  - Prompt: “请新增最小必要的数据模型和提示词常量；不要写复杂框架，不要提前加入未使用抽象。”
  - 验证: `python -m pytest -q task_agent/tests/test_models.py` 或通过后续 planner/executor 测试间接覆盖。

- [x] Task 4: 实现真实电商工具目录 `task_agent/tool_registry.py`
  - [x] SubTask 4.1: 定义 `TOOL_CATALOG`，覆盖当前公开电商工具：搜索、详情、画像、购物车新增/改量、订单状态、客服工单、优惠券、下单、支付、退款、商家改价、商家改库存。
  - [x] SubTask 4.2: 实现 `catalog_for_role(role)`，买家不可见 `merchant_*` 工具。
  - [x] SubTask 4.3: 实现 `invoke(tool_name, args, *, store, user_id, role)`，映射到真实 `auto_defense_system.ecommerce_agent.tools` 函数。
  - [x] SubTask 4.4: 对未知工具和缺失/错误参数返回 blocked `ToolExecution`，不得抛出未捕获异常。
  - [x] SubTask 4.5: 新增测试覆盖角色过滤、真实购物车变更、未知工具阻断。
  - 描述: 工具目录是 LLM 的可行动作空间，必须复用真实业务逻辑和策略校验。
  - Prompt: “请封装现有电商工具为 LLM 可选目录；不要复制业务逻辑，所有业务状态变化必须来自现有 `tools.py` 和 `store.py`。”
  - 验证: `pytest -q task_agent/tests/test_tool_registry.py`

- [x] Task 5: 实现任务解析与计划生成 `task_agent/planner.py`
  - [x] SubTask 5.1: 实现 `parse_task(instruction, llm) -> TaskSpec`，调用 `llm.complete_json()` 抽取 goal、subgoals、constraints、entities。
  - [x] SubTask 5.2: 实现 `make_plan(spec, role, llm) -> Plan`，把 `TaskSpec` 和 `catalog_for_role(role)` 交给模型生成 `PlanStep`。
  - [x] SubTask 5.3: 对离线或字段缺失结果做最小规范化，保证 PlanStep 有合法 `step_id`、`candidate_tool`、`args_hint`。
  - [x] SubTask 5.4: 新增 `test_planner.py::test_parse_multi_goal` 和计划合法工具测试。
  - 描述: 命中“解析复杂任务指令”和“规划任务执行步骤”两个赛题题眼。
  - Prompt: “请实现解析和规划，不要使用关键词直接路由执行；离线 fallback 可以做确定性结构补全，但计划仍必须基于工具目录校验。”
  - 验证: `pytest -q task_agent/tests/test_planner.py`

- [x] Task 6: 实现 ReAct 执行器 `task_agent/executor.py`
  - [x] SubTask 6.1: 新增 `Executor.__init__(store, user_id, role, llm, recorder=None)`。
  - [x] SubTask 6.2: 实现 `run_step(step, history) -> TaskStep`，串联 `_think()`、`_decide_action()`、`_observe()`。
  - [x] SubTask 6.3: `_decide_action()` 使用 `llm.decide()` 从候选工具中选择，并用 `complete_json()` 生成参数。
  - [x] SubTask 6.4: `_observe()` 调用 `tool_registry.invoke()`，从真实 `ToolExecution` 构造 `Observation`。
  - [x] SubTask 6.5: 新增 `test_executor.py::test_step_calls_real_tool`，断言购物车或订单状态真实变化。
  - 描述: 执行器是“环境感知”和“自主决策”的核心落点。
  - Prompt: “请实现最小 ReAct 循环；不要把中文关键词映射成工具，工具选择必须经过 `llm.decide()`，工具结果必须来自真实 registry。”
  - 验证: `pytest -q task_agent/tests/test_executor.py`

- [x] Task 7: 实现自主重规划 `task_agent/replanner.py`
  - [x] SubTask 7.1: 实现 `should_replan(obs, spec) -> tuple[bool, str]`。
  - [x] SubTask 7.2: 覆盖触发条件：blocked、缺货/搜索无匹配、超预算、支付/下单失败、工具异常兜底。
  - [x] SubTask 7.3: 实现 `replan(spec, history, failure, role, llm) -> Plan`，生成 `revision+1` 的替代计划。
  - [x] SubTask 7.4: 新增预算不足、缺货、blocked 的单元测试。
  - 描述: 把真实环境反馈转化为模型可解释的替代计划生成。
  - Prompt: “请实现重规划判断和计划再生成；保持规则只用于触发和诊断，替代方案由 LLM JSON 结果产生并经过工具目录校验。”
  - 验证: `pytest -q task_agent/tests/test_replanner.py`

- [x] Task 8: 实现 TaskAgent 编排 `task_agent/agent.py`
  - [x] SubTask 8.1: `TaskAgent.__init__` 复用 `create_demo_store()`，支持 `store`、`user_id`、`role`、`force_offline` 注入。
  - [x] SubTask 8.2: `run(instruction, max_steps=12, max_replans=3)` 串联 parse、plan、execute、should_replan、replan、summary、verify。
  - [x] SubTask 8.3: 实现 `_summarize_result()` 与 `_verify_goal()`，优先结合真实状态规则，必要时调用 LLM JSON judge。
  - [x] SubTask 8.4: 新增 `test_agent_e2e.py`，覆盖离线端到端、缺货恢复、max_steps/max_replans 上限。
  - 描述: 提供赛事主链路的统一编排结果 `TaskRunResult`。
  - Prompt: “请实现编排器；保持循环简单可读，确保每步 trace 都被保留，避免重规划死循环。”
  - 验证: `pytest -q task_agent/tests/test_agent_e2e.py`

- [x] Task 9: 打通轨迹适配与 CLI 入口
  - [x] SubTask 9.1: 新建 `task_agent/trace_adapter.py`，把 `TaskStep` 转为 `trace_dag.build_trace_report()` 支持的 event schema。
  - [x] SubTask 9.2: 实现 `export_plan_trace(result, out_dir)`，写出 `trace_graph.md`、`trace_timeline.jsonl`、`trace_integrity.json` 等 artifacts。
  - [x] SubTask 9.3: 在 `run.py` 新增 `--agent-task`、`--agent-demo`、`_print_agent_summary(result)`。
  - [x] SubTask 9.4: 确保 `run.py` 的 source path 可导入 `task_agent`，并在 `pyproject.toml` 加入 `task_agent/tests`。
  - [x] SubTask 9.5: 新增 CLI smoke 测试或最小集成测试。
  - 描述: 让规划能力可见、可复现、可答辩展示。
  - Prompt: “请复用现有 `trace_dag`，只做字段适配；CLI 输出应简洁稳定，适合脚本和答辩读取。”
  - 验证: `python run.py --agent-task "找800元内降噪耳机比价后下单" --offline`

- [x] Task 10: 接入电商 v2 主入口并保留兼容兜底
  - [x] SubTask 10.1: 在 `auto_defense_system/src/auto_defense_system/ecommerce_agent/agent.py` 新增 `invoke_ecommerce_agent_v2()`。
  - [x] SubTask 10.2: 新入口复用现有输入防火墙，正常路径调用 `TaskAgent.run(message)`。
  - [x] SubTask 10.3: 将 TaskAgent 结果转换为 `EcommerceAgentResult`，保留旧结构字段。
  - [x] SubTask 10.4: 旧 `invoke_ecommerce_agent()` 和 `_route_message()` 保留为 legacy/offline 兼容路径。
  - [x] SubTask 10.5: 目标漂移拦截继续作为 blocked observation 或兼容兜底信号参与重规划。
  - 描述: 替换最关键的关键词路由主链路，同时降低破坏现有测试的风险。
  - Prompt: “请新增 v2，不要删除旧入口；新入口必须走 TaskAgent，返回结构要兼容现有消费者。”
  - 验证: `pytest -q auto_defense_system/tests/test_ecommerce_agent.py task_agent/tests/test_agent_e2e.py`

- [x] Task 11: 攻防子系统去查表化
  - [x] SubTask 11.1: `defense_agent.py::harden()` 将 `DEFENSE_PLAYBOOK` 从唯一答案降级为 candidates，并通过 `llm.decide()` 选择动作。
  - [x] SubTask 11.2: `attack_agent.py::_reflect()` 不再机械 `index+1`，改由 `llm.decide()` 基于失败诊断选择升级方向。
  - [x] SubTask 11.3: `attack_agent.py::_plan()` 使用 `complete_json()` 基于历史生成下一条 payload，ladder 仅作为候选池。
  - [x] SubTask 11.4: `threat_taxonomy.py::SyntheticTarget.attempt()` 增加 `online_judge` 分支，阈值逻辑保留为离线兜底。
  - [x] SubTask 11.5: `auto_defense_system/src/auto_defense_system/agent/react.py` 文件头标记 legacy，主链路指向 `task_agent/executor.py`。
  - [x] SubTask 11.6: 更新原有攻防测试，增加非法 LLM 选择回退和离线确定性测试。
  - 描述: 消除答辩中容易被追问的“查表冒充智能”问题。
  - Prompt: “请做最小行为迁移：候选池可复用旧 playbook/ladder，但最终选择要经过 LLM 客户端；旧确定性逻辑只作为离线兜底。”
  - 验证: `pytest -q auto_attack_system/tests auto_defense_system/tests/test_comp3_defense.py`

- [x] Task 12: 新增任务成功率评测
  - [x] SubTask 12.1: 新建 `auto_evaluation_system/src/auto_evaluation_system/task_eval.py` 或贴合现有 runner 结构的任务评测模块。
  - [x] SubTask 12.2: 输出任务达成率、平均步数、重规划触发率、重规划成功率、无效工具调用率。
  - [x] SubTask 12.3: 评测判定结合 `TaskRunResult`、真实 `EcommerceStore` 状态和 `llm.complete_json()` judge。
  - [x] SubTask 12.4: 增加测试覆盖指标计算、空 trace、失败 trace、成功重规划 trace。
  - 描述: 把赛事主成果从 ASR/FPR 转为任务达成与自治能力指标。
  - Prompt: “请新增任务评测能力，保持与现有 evaluation 模块风格一致；不要移除原 ASR/FPR 指标。”
  - 验证: `pytest -q auto_evaluation_system/tests`

- [x] Task 13: 配置与双线复现材料
  - [x] SubTask 13.1: 确认 `auto_defense_system/src/auto_defense_system/config.py` 已读取 `LLM_API_BASE`、`LLM_API_KEY`、`LLM_MODEL`。
  - [x] SubTask 13.2: 如存在 `.env.example`，补充 Qwen 兼容模式示例；如不存在，在实现阶段先征询是否新增，避免无关文件扩张。
  - [x] SubTask 13.3: 在报告或文档中明确在线/离线双线策略：在线用于真实轨迹，离线用于 CI 和答辩兜底。
  - 描述: 降低现场 API 不稳定风险，确保一键复现。
  - Prompt: “请只补必要配置说明；不要改变现有 `LLMConfig.from_project()` 的读取语义，除非测试证明必须。”
  - 验证: `python run.py --agent-demo --offline`

- [x] Task 14: 重写竞赛报告和答辩脚本
  - [x] SubTask 14.1: 重写 `docs/competition/final-report.md`，标题改为“大模型驱动的电商领域自治任务智能体”。
  - [x] SubTask 14.2: 新增 `docs/competition/comp1-agent-demo-script.md`，覆盖 8 分钟演示流程。
  - [x] SubTask 14.3: 报告主线使用任务解析、规划、环境感知、动态重规划、目标达成；安全作为可靠性保障单列。
  - [x] SubTask 14.4: 引用 CLI 和 trace artifact 产物，说明真实模型与离线复现双线证据。
  - 描述: 交付物必须匹配赛事一评分语言，避免主语仍停留在安全攻防。
  - Prompt: “请基于实现后的真实命令输出和 trace 产物写报告；不要虚构指标，未跑出的数据明确标注待补。”
  - 验证: 人工检查报告结构；运行 `python run.py --agent-demo --offline` 生成可引用证据。

- [x] Task 15: 全量验收与回归
  - [x] SubTask 15.1: 运行 TaskAgent 专项测试、攻防回归测试、trace_dag 测试和 evaluation 测试。
  - [x] SubTask 15.2: 运行 CLI 验收：`--agent-task` 与 `--agent-demo` 均在 offline 模式成功。
  - [x] SubTask 15.3: 检查至少一个 demo 场景触发重规划且最终达成目标。
  - [x] SubTask 15.4: 检查所有新增任务和 checklist 项目完成后再返回最终结果。
  - 描述: 作为实施收口任务，确保规格不是“写完代码但无法复现”。
  - Prompt: “请执行完整验证并只修复与本规格相关的问题；不要顺手重构无关模块。”
  - 验证: `pytest -q task_agent/tests trace_dag/tests auto_attack_system/tests auto_defense_system/tests auto_evaluation_system/tests`

- [x] Task 16: 修复全量 pytest 收集阶段依赖导入失败
  - [x] SubTask 16.1: 处理 `auto_defense_system/tests/test_defense_smoke.py` 收集时导入 `auto_defense_system.security.firewall.classifier` 触发的 `ModuleNotFoundError: No module named 'langchain_openai'`。
  - [x] SubTask 16.2: 确保离线/CI 环境无需额外在线 LLM 依赖即可完成本规格相关测试收集与执行，或在项目依赖中明确补齐该依赖。
  - 失败原因: 执行全量验收命令时，pytest 在收集阶段因缺少 `langchain_openai` 直接退出，无法继续验证 Task 15 checkpoint。
  - 验证: `pytest -q task_agent/tests trace_dag/tests auto_attack_system/tests auto_defense_system/tests auto_evaluation_system/tests`

# Task Dependencies
- Task 2 depends on Task 1。
- Task 3 depends on Task 1。
- Task 4 depends on Task 1 and Task 3。
- Task 5 depends on Task 2, Task 3, and Task 4。
- Task 6 depends on Task 2, Task 3, and Task 4。
- Task 7 depends on Task 3, Task 5, and Task 6。
- Task 8 depends on Task 5, Task 6, and Task 7。
- Task 9 depends on Task 8。
- Task 10 depends on Task 8。
- Task 11 depends on Task 2。
- Task 12 depends on Task 8。
- Task 13 can run after Task 2 and in parallel with Task 9-12 where it does not touch the same files。
- Task 14 depends on Task 9, Task 10, Task 12, and validated CLI evidence。
- Task 15 depends on all implementation tasks。
- Task 16 depends on Task 15 的全量验收暴露出 pytest 收集阶段阻塞。
- 最终 checklist 收口依赖 Task 16。

# Parallelization Notes
- After Task 1, Task 2 and Task 3 can start independently.
- After Task 3, Task 4 can proceed while Task 2 tests are being completed.
- After Task 8, Task 9, Task 10, Task 11, and Task 12 can be split across sub-agents if file ownership is kept separate.
- Task 14 should wait for real artifacts to avoid report metrics drifting from implementation.
- Task 16 是全量验收后的顺序修复任务，不应与实现任务并行。

# AdvLoop 提交前检查清单

## 必须包含

- 根目录 `README.md`
- `ROADMAP.md`
- `docs/competition/README.md`
- `docs/competition/final-report.md`
- `docs/competition/comp1-agent-demo-script.md`
- `docs/competition/defense-script-8min.md`，历史安全攻防补充讲稿
- `docs/competition/reproducibility.md`
- `docs/competition/submission-checklist.md`
- `docs/competition/evidence-pack/`，作为历史安全可靠性补充证据
- `task_agent/`
- `trace_dag/`
- `auto_attack_system/`
- `auto_defense_system/`
- `auto_evaluation_system/`
- `sdk/python/`
- `run.py`
- `pyproject.toml`

## 固定文档和证据文件

确认以下文件存在：

- `docs/competition/final-report.md`
- `docs/competition/comp1-agent-demo-script.md`
- `docs/competition/evidence-pack/convergence_curve.png`
- `docs/competition/evidence-pack/damage_radar.png`
- `docs/competition/evidence-pack/convergence.json`
- `docs/competition/evidence-pack/ablation.json`
- `docs/competition/evidence-pack/ablation_table.md`
- `docs/competition/evidence-pack/benchmark_datacard.md`
- `docs/competition/evidence-pack/evidence_pack.md`
- `docs/competition/evidence-pack/README.md`

## 不要提交或打包

- `.venv/`、`venv/`
- `.pytest_cache/`、`.ruff_cache/`
- `__pycache__/`
- `runs/`、`attack-runs/`、`defense-runs/`、`evidence-runs/`
- `logs/`、`storage/`
- `.env`

## 推荐提交方式

优先从项目根目录导出提交包，不要混入本地运行产物、API key 或无关赛事目录。

## 提交前验证命令

```bash
python run.py --agent-demo --offline
python run.py --agent-task "找800元内降噪耳机比价后下单" --offline
python run.py --task-eval --offline
python -m pytest -q task_agent/tests trace_dag/tests auto_attack_system/tests auto_defense_system/tests auto_evaluation_system/tests
python -m compileall -q auto_attack_system auto_defense_system auto_evaluation_system sdk task_agent trace_dag
```

## 关键数字一致性

- `python run.py --agent-demo --offline`：`basic-search` 与 `replan-stock-recovery` 均 `GOAL_ACHIEVED=True`。
- `replan-stock-recovery`：首步 `cart_add_item` 因库存不足 blocked，随后 `REPLANS=1` 并成功加购。
- `python run.py --agent-task "找800元内降噪耳机比价后下单" --offline`：`GOAL_ACHIEVED=True`，轨迹为 `product_search > cart_add_item > create_order`。
- `python run.py --task-eval --offline`：`total_tasks=3`，`achieved_tasks=3`，`task_achievement_rate=1.000000`，`invalid_tool_call_rate=0.000000`。
- 历史安全攻防补充：ASR 44% -> 0%，7 轮收敛，证据位于 `docs/competition/evidence-pack/`。

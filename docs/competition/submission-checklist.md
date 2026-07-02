# MCP-Sentinel 提交前检查清单

## 项目身份

- [ ] 展示名称仅使用 `MCP-Sentinel`
- [ ] GitHub 仓库为 `Parval0615/mcp-sentinel`
- [ ] 本地根目录为 `D:\mcp-sentinel`
- [ ] Python 发行包名为 `mcp-sentinel`
- [ ] 不再出现旧项目名、旧仓库 URL或其他赛题主线

## 必须包含

- `README.md`
- `ROADMAP.md`
- `competition-strategy.md`
- `docs/competition/README.md`
- `docs/competition/final-report.md`
- `docs/competition/comp1-agent-demo-script.md`
- `docs/competition/reproducibility.md`
- `docs/competition/submission-checklist.md`
- `docs/competition/evidence-pack/`
- `run.py`、`pyproject.toml`
- Task、Attack、Defense、Evaluation、MCP 拦截和 trace 相关源码

## 固定证据

- `convergence.json` 与 `convergence_curve.png`
- `ablation.json` 与 `ablation_table.md`
- `damage_radar.png`
- `benchmark_datacard.md`
- `evidence_pack.md`
- 所有 Markdown 数字必须能从对应 JSON 推导

## 不得提交

- `.env`、API key、真实用户或企业数据
- `.venv/`、`__pycache__/`、`.pytest_cache/`、`.ruff_cache/`
- `runs/`、`attack-runs/`、`defense-runs/`、`evidence-runs/`
- `logs/`、`storage/`
- 真实外部攻击 payload、真实支付或真实外部目标配置

## 验证命令

```powershell
python run.py --attack-campaign --offline
python run.py --defense-regression --offline
python run.py --evidence-pack --offline
python run.py --closed-loop-demo
python run.py --agent-demo --offline
python -m pytest -q
python -m compileall -q auto_attack_system auto_defense_system auto_evaluation_system sdk task_agent trace_dag arena evasion_shield injection_radar intent_aligner policy_dsl sentinel_console sentinel_proxy
git diff --check
```

## 口径检查

- [ ] 离线确定性结果没有被称为真实模型结果
- [ ] 脚本化重规划场景没有被称为真实模型自主规划证据
- [ ] 固定证据数字来自当前代码重新运行
- [ ] 电商与 MCP 场景均明确为本地合成环境
- [ ] 项目主语始终是多智能体安全自治系统
- [ ] 八分钟演示覆盖任务解析、规划、执行、环境反馈、自主决策、重规划和量化验证

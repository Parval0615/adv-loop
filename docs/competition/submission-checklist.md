# AdvLoop 提交前检查清单

## 必须包含

- 根目录 `README.md`
- `ROADMAP.md`
- `docs/competition/README.md`
- `docs/competition/final-report.md`
- `docs/competition/defense-script-8min.md`
- `docs/competition/reproducibility.md`
- `docs/competition/submission-checklist.md`
- `docs/competition/evidence-pack/`
- `auto_attack_system/`
- `auto_defense_system/`
- `auto_evaluation_system/`
- `sdk/python/`
- `run.py`
- `pyproject.toml`

## 固定证据文件

确认以下文件存在：

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

优先从 `D:\adv-loop` 导出提交包，不要混入其他赛事目录或本地运行产物。

## 提交前验证命令

```powershell
python run.py --closed-loop-demo
python run.py --attack-campaign --offline
python run.py --defense-regression --offline
python run.py --evidence-pack --offline
python -m pytest -q
python -m compileall -q auto_attack_system auto_defense_system auto_evaluation_system sdk
```

## 关键数字一致性

- ASR：44% → 0%
- 收敛轮数：7
- Attack reflection 消融：2/7 vs 7/7
- Defense 消融：ASR 保持 44%
- 精准加固误伤率：0%
- 全量测试：215 passed, 1 skipped, 2 warnings
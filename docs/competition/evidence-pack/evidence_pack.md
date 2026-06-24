# AdvLoop 竞赛证据包总览

本目录汇总 AdvLoop 的答辩证据：智能体决策闭环、ASR 收敛曲线、损伤雷达图、消融实验与可复用 Benchmark 数据卡。

## 关键结论

- **智能体自治闭环**：Attack / Evaluation / Defense 三类 Agent 能完成发现、量化、决策和回归验证。
- **对抗收敛**：ASR 从 44% 经 7 轮加固降至 0%（达标线 ≤10%）。
- **消融·去掉 Defense**：最终 ASR 仍达 44% → 防御决策不可或缺。
- **消融·去掉 Attack reflection**：攻击面覆盖停在 2/7 → 失败反思不可或缺。

## 产物清单

| 文件 | 用途 |
|---|---|
| `convergence_curve.png` | 攻击成功率收敛曲线 |
| `convergence.json` | 多轮 ASR/覆盖收敛数据 |
| `damage_radar.png` | 加固前后多维损伤雷达图 |
| `ablation.json` / `ablation_table.md` | 三组消融对照 |
| `benchmark_datacard.md` | AgentRiskBench-Ecommerce 数据卡 |
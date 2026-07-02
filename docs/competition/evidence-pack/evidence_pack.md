# MCP-Sentinel 竞赛证据包总览

本目录汇总 MCP-Sentinel 多智能体安全自治闭环的答辩证据：收敛曲线、损伤雷达图、消融实验与可复用 Benchmark 数据卡。

## 关键结论

- **对抗收敛（答辩王牌）**：ASR 从 30% 经 7 轮加固单调降至 0%（达标线 ≤10%：达标）。
- **消融·去掉 Defense**：最终 ASR 仍达 30%（高位不降）→ 防御 Agent 不可或缺。
- **消融·去掉 Attack reflection**：攻击面覆盖停在 2/7（完整系统达 7/7）→ 攻击反思不可或缺。

## 产物清单

| 文件 | 用途 |
|---|---|
| `convergence_curve.png` | 攻击成功率收敛曲线（答辩王牌） |
| `convergence.json` | 多轮 ASR/覆盖收敛数据 |
| `damage_radar.png` | 加固前后多维损伤雷达图 |
| `ablation.json` / `ablation_table.md` | 三组消融对照 |
| `benchmark_datacard.md` | AgentRiskBench-Ecommerce 数据卡 |

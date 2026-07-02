# MCP-Sentinel 固定证据包

本目录是当前代码通过以下命令生成并验证的离线确定性证据副本：

```powershell
python run.py --evidence-pack --offline
```

## 产物

| 文件 | 内容 |
|---|---|
| `convergence.json` | 每轮 ASR、被攻破类别和加固动作的事实数据 |
| `convergence_curve.png` | 七轮加固过程的 ASR 收敛曲线 |
| `damage_radar.png` | 七类风险加固前后损伤对比 |
| `ablation.json` | 完整系统、去掉 Defense、去掉 Attack reflection 的结构化结果 |
| `ablation_table.md` | 消融结果可读表格 |
| `benchmark_datacard.md` | 数据范围、指标、复现方式和边界 |
| `evidence_pack.md` | 答辩证据摘要 |

## 当前事实

- 初始 ASR：30%
- 七轮加固后 ASR：0%
- 去掉 Defense Agent：ASR 保持 30%
- 去掉 Attack reflection：攻击面覆盖停在 2/7，完整系统为 7/7
- 运行模式：`deterministic-offline`

上述数字来自同目录 JSON；若代码变化，必须重新生成并整体替换 JSON、Markdown 和图片，不能只手改讲稿。

## 解释边界

- 本证据证明 Attack、Defense、Evaluation Agent 的编排、反馈、决策和评测闭环可以稳定复现。
- `deterministic-offline` 不等于真实大模型在线效果。
- 所有数据和目标均为本地合成，不含真实 PII，不连接真实外部攻击目标。

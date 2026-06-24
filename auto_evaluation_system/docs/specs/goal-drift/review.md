# Goal Drift W8 Review

**状态：通过 v0.1 review**

## Checklist

- [x] Goal Representation 有最小可校验字段。
- [x] GDM 输入 / 输出边界明确。
- [x] Probe 协议不进入 agent context window。
- [x] clean vs controlled 对照协议明确。
- [x] false positive / false negative 边界已记录。
- [x] Phase 3 detector 实现仍被明确隔离到 `auto_evaluation_system.detection`。

## Review 结论

GDM v0.1 具备可计算性：`GoalRepresentation`、trajectory、probe 和 controlled labels 足以支持 Phase 3 离线指标与在线 detector。

GDM v0.1 具备可验证性：Phase 2 已提供 goal perturbation controlled scenario，可与 clean scenario 形成 ground truth 对照。

允许进入 Phase 3 Task 1 / Task 2 的指标与 detector 设计；Phase 2 不实现 detector。

## 已知限制

- v0.1 不处理真实用户偏好变化，只处理受控扰动。
- v0.1 不定义阈值校准方法，留给 Phase 3 评估协议。
- v0.1 不声称能区分所有普通 task failure 与 goal drift，只要求 detector 未来必须报告失败案例。

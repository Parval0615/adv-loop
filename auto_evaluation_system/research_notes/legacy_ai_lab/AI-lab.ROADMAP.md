# Agent Runtime Security Lab - 研究路线图

> Agent 运行时安全研究基础设施。从可重放 sandbox 开始，逐步构建 telemetry、memory、risk injector、detection、benchmark 与论文产出。

文档版本：v1.1

当前阶段：Phase 3 - Detection & Trajectory Modeling

当前完成：Phase 1 · Task 1-4 + Phase 2 · Task 1-4 - Sandbox / Telemetry / Memory / Runner + GDM spec / Risk Injectors v0.1

---

## 总览

| 阶段 | 名称 | 建议周期 | 核心目标 | 阶段门禁 |
|------|------|----------|----------|----------|
| Phase 1 | Sandbox & Telemetry Foundation | Week 1-6 | 搭建可观测、可重放、可落盘的实验基础设施 | replay 稳定、trajectory schema 稳定、telemetry 不进 context |
| Phase 2 | Risk Injector & Goal Formalization | Week 7-12 | 完成 Goal Drift 形式化与三类受控注入 | GDM 通过 review，注入实验可复现 |
| Phase 3 | Detection & Trajectory Modeling | Week 13-19 | 基于标注轨迹构建 TRS / GDM / MIS 检测与评估 | 指标可计算、评估协议固定、结果可解释 |
| Phase 4 | Research Output & Release | Week 20-24 | 产出 Paper #1、Benchmark v0.1、开源发布材料 | 可复现实验包、论文主线闭环、公开文档完整 |

> 路线图原则：宁可缩小单次交付范围，也不要牺牲可重放性、数据质量和阶段门禁。

---

## 当前仓库状态

| 模块 | 状态 | 说明 |
|------|------|------|
| `arl.sandbox` | 已完成 v0.1 | Direct API / LangGraph replay、mock tools、session isolation、5-step golden trajectory |
| `arl.events` | 已完成 v0.1 | `StepEvent` / `InMemoryStepEmitter` 已可支撑 sandbox smoke |
| `schemas/trajectory-v1.schema.json` | 已完成 v0.1 | 可验证 golden trajectory，后续 telemetry 只做兼容扩展 |
| `arl.telemetry` | 已完成 v0.1 | `TelemetryStepEmitter`、`TrajectoryRecorder`、overhead 计量、context non-interference 测试 |
| `arl.memory` | 已完成 v0.1 | 本地 MVP：namespace isolation、三层 memory、CRUD、audit log、`MemoryOpPayload` 对接 |
| `arl.runner` | 已完成 v0.1 | 串行 Runner MVP：`runs/` 结果落盘、metadata、trajectory、scenario copy、baseline diff |
| `arl.injectors` | scaffold | Phase 2 前只保留目录与 README，不实现业务逻辑 |
| `arl.detection` | scaffold | Goal Drift review 前不得实现 `goal_drift` 检测逻辑 |
| `arl.dashboard` | scaffold | Phase 3 后半段再实现 |

---

## 核心设计原则

1. **可重放性优先**：所有实验必须包含 seed、scenario config、LLM cassette 或等价 replay 机制。
2. **轨迹是一等数据结构**：后续检测、注入、论文实验都以标准化 trajectory 为中心。
3. **观测与执行解耦**：Telemetry 只能走 side-channel，不得写入 Agent context window。
4. **先工程、后算法**：Phase 1-2 打数据底座，Phase 3 再正式做检测算法与建模。
5. **受控注入与自然涌现分离**：controlled injection 与 observational run 必须在配置、数据与评估中明确区分。
6. **门禁比进度更重要**：Phase 1 未稳定不进入 Phase 2；Goal Drift 未 review 不进入 Phase 3。

---

## Phase 1 - Sandbox & Telemetry Foundation

**周期**：Week 1-6

**核心目标**：形成可重放、可观测、可落盘、可集成测试的实验基座。

**当前状态**：Task 1-4 已完成 v0.1；下一阶段进入 Phase 2 Goal Drift 形式化。

### Task 1: Sandbox SDK

**状态**：已完成 v0.1

范围：

- 多框架执行入口：Direct API、LangGraph、AutoGen scaffold
- 隔离 session：emitter、tool registry、LLM client、memory namespace 不共享状态
- LLM cassette replay：按 turn index 回放，支持无 API key 的 CI / 本地 smoke
- Mock Tool Registry：支持 mock / real handler 切换
- 5-step golden scenario：`llm_inference -> tool_call -> llm_inference -> tool_call -> llm_inference`

验收标准：

- `pytest tests/sandbox -q` 通过
- `ruff check src tests` 通过
- Direct API 与 LangGraph replay 输出符合 `schemas/trajectory-v1.schema.json`
- 同一 scenario 连续运行后，归一化 trajectory 完全一致

后续注意：

- AutoGen 暂保持 scaffold，不把完整集成作为 Phase 1 硬门禁
- `TrajectoryBuilder` 已迁移为 `arl.telemetry.TrajectoryRecorder` 的兼容壳，sandbox 只负责执行和发事件

### Task 2: Telemetry 采集系统

**状态**：已完成 v0.1

**优先级**：Phase 1 已收口

范围：

- 将 `StepEvent` 采集正式纳入 telemetry 层，保留稳定事件契约
- 实现 `TelemetryStepEmitter` side-channel collector
- 由 `TrajectoryRecorder` 生成符合 `trajectory-v1` 的 trajectory，并支持后续兼容扩展
- 记录 LLM I/O、tool call、memory ops、state delta、timestamp
- 增加 telemetry overhead 计量
- 明确禁止 telemetry 数据进入 Agent prompt / context

验收标准：

- sandbox backend 只发事件，不直接拼 trajectory
- telemetry 输出可通过 JSON Schema 校验
- overhead 字段可测量，已有 smoke-level 断言
- 已有测试验证 telemetry 不修改 input messages / agent context

### Task 3: Memory Store

**状态**：已完成 v0.1

优化后的交付策略：

- Phase 1 已完成最小可用 memory interface，不急于一次性接满 Chroma/Qdrant/PostgreSQL
- 已优先保证 namespace isolation、CRUD、audit log、memory ops telemetry
- 使用 `InMemoryMemoryStore` 作为本地 MVP
- 向量库和 PostgreSQL adapter 作为 Phase 2+ 增强

范围：

- Memory schema：short-term / long-term / episodic 三层
- Memory namespace：每个 experiment / session 隔离
- CRUD audit log：记录 op、namespace、layer、key、timestamp、source
- 与 telemetry 对接：memory read/write/delete 产生 `memory_ops`

验收标准：

- 不同 namespace 之间读写隔离
- CRUD 操作均有 audit record
- memory ops 能进入 trajectory step
- Memory Poisoning injector 能在 Phase 2 基于该接口扩展

### Task 4: Experiment Runner

**状态**：已完成 v0.1

优化后的交付策略：

- Phase 1 已实现串行 runner 和结果落盘
- 并行队列、复杂调度和大规模 diff 放到增强阶段

范围：

- 读取 `configs/scenarios/*.yaml`
- 初始化 sandbox、telemetry、memory namespace
- 串行执行 scenario
- 保存结果目录：config copy、trajectory、run metadata
- 提供 baseline diff 的最小版本
- 支持固定 seed 和一键重跑

验收标准：

- `runner -> sandbox -> telemetry -> result directory` 集成测试通过
- 运行结果包含 scenario config、seed、trajectory、metadata
- 同一 scenario 可重复运行并生成可比较结果
- Phase 2 injector 能复用 runner 执行受控实验

### Phase 1 周度计划

| 周期 | 重点 | 交付 |
|------|------|------|
| W1-W2 | Sandbox SDK | Direct API / LangGraph replay、mock tools、schema smoke |
| W3 | Telemetry 管道 | side-channel collector、trajectory writer、overhead smoke |
| W4 | Memory MVP | namespace、CRUD、audit log、memory ops event |
| W5 | Runner MVP | scenario runner、结果落盘、baseline diff 最小版 |
| W6 | 集成与硬化 | integration tests、文档、Phase 2 readiness review |

### Phase 1 门禁

- `pytest` 和 `ruff` 通过
- 至少一个 Direct API scenario 和一个 LangGraph scenario 可稳定 replay
- trajectory schema 固定并有 golden fixture
- telemetry 不影响 Agent context
- memory namespace isolation 有测试
- runner 能保存可复现实验结果

---

## Phase 2 - Risk Injector & Goal Formalization

**周期**：Week 7-12

**核心目标**：完成可计算、可验证的 Goal Drift 定义，并实现三类受控风险注入。

### Task 1: Goal Drift 形式化定义

**周期**：W7-W8

**状态**：已完成 v0.1

**优先级**：最高，独立专项

范围：

- Goal Representation：定义目标如何编码为可计算表示
- Goal Drift Metric：定义 drift 的数学形式、输入、输出、阈值语义
- Ground truth 协议：使用有/无注入轨迹差异作为受控对照
- Probe 协议：在 trajectory 不同步骤插入一致性检测问题
- Review 文档：记录定义假设、反例、适用边界与不可覆盖场景

验收标准：

- GDM 能用代码实现
- GDM 能用受控实验验证
- 评估样例中能解释 false positive / false negative
- 内部 review 通过后，才允许进入 Phase 3 的 `detection.goal_drift`

### Task 2: Memory Poisoning Injector

**周期**：W9-W10

**状态**：已完成 v0.1

范围：

- 基于 memory interface 的投毒入口
- 毒素强度梯度：light / medium / heavy
- 三类策略：语义相近替换、权威伪造注入、时序操控注入
- retrieval 验证：确保 poisoned memory 被实际召回
- 输出带标注 trajectory，用于 MIS 和 Paper #1

验收标准：

- 每次注入有 seed、config、audit log、trajectory
- 能生成 clean vs poisoned 的对照实验
- 注入强度可参数化，结果可复现

### Task 3: Tool Tampering Injector

**周期**：W11

**状态**：已完成 v0.1

范围：

- Tool Registry 和 Agent backend 之间的 tamper proxy
- 返回值替换、延迟注入、渐进式可信度降解
- tool dependency graph 的最小记录
- 权限越界模拟场景

验收标准：

- clean vs tampered trajectory 可对比
- tamper 行为有明确标注，不污染自然观测数据
- 代理层不破坏现有 mock / real tool 切换

### Task 4: Goal Perturbation Injector

**周期**：W12

**状态**：已完成 v0.1

范围：

- System prompt 目标语义扰动
- Context window 扰动样例
- 扰动强度 0.0-1.0 参数化
- 多轮对话目标漂移追踪协议

验收标准：

- 扰动配置可复现
- 与 GDM 定义直接对齐
- 输出可作为 Phase 3 Goal Drift Detector 的 ground truth

### Phase 2 门禁

- Goal Drift 定义通过 review，并配有结构校验器
- 三类 injector 至少各有一个 clean / controlled 对照 scenario
- 注入数据集有明确 label、seed、config、trajectory
- related work 初版完成，尤其是 Memory Poisoning 与 Tool Security 边界

---

## Phase 3 - Detection & Trajectory Modeling

**周期**：Week 13-19

**核心目标**：基于 Phase 1-2 的高质量轨迹数据，构建可解释、可评估的检测系统。

### Task 1: Trajectory Risk Modeling

**周期**：W13-W14

优化后的交付策略：

- 先实现规则/统计 baseline，再考虑复杂序列模型
- 避免在数据量不足时过早引入重模型

范围：

- Trajectory Risk Score (TRS)
- 行为序列相似度：编辑距离 / DTW baseline
- risk-annotated trajectory 数据集
- 早期预警原型：步骤 N 时估计后续 K 步风险

### Task 2: Goal Drift Detector

**周期**：W15-W16

**前置条件**：Goal Drift 定义已通过 Phase 2 review

范围：

- 基于 GDM 的在线检测管道
- 滑动窗口检测
- 步骤级、对话轮级、任务级多粒度输出
- ROC / precision-recall 评估

### Task 3: Memory Poisoning Detection

**周期**：W17

范围：

- retrieval consistency 检测
- memory provenance 追踪
- poisoning impact 估计
- Memory Integrity Score (MIS)

### Task 4: Analysis Engine & Dashboard

**周期**：W18-W19

优化后的交付策略：

- 先做离线分析和静态报告，再做实时 dashboard

范围：

- TRS / GDM / MIS 汇总报告
- trajectory diff 视图
- 风险热力图和时间线
- anomaly pattern 聚类原型

### Phase 3 门禁

- 每个指标都有定义、输入、输出和失败案例说明
- 所有检测结果能追溯到具体 trajectory steps
- 评估集区分 train/dev/test 或等价实验切分
- 至少形成 Paper #1 所需的主实验图表

---

## Phase 4 - Research Output & Release

**周期**：Week 20-24

**核心目标**：将工程与实验闭环整理成可发表、可复现、可开源的研究产出。

### Task 1: Paper #1 - Memory Poisoning

**周期**：W20-W21

**定位**：优先投稿突破口

内容：

- Agentic Systems 中 memory poisoning 的 taxonomy
- 受控注入框架
- MIS 指标与检测实验
- clean vs poisoned trajectory 证据链
- 与现有 memory / RAG / agent security 工作的边界

### Task 2: AgentRiskBench v0.1

**周期**：W22

优化后的交付策略：

- v0.1 先发布 30-50 个高质量场景
- `>=200` 场景作为后续扩展目标，不作为首次发布硬门禁

内容：

- 标准 scenario schema
- clean / controlled / observational 三类运行模式
- Docker 或脚本化复现实验环境
- leaderboard 设计文档可先行，不必第一版上线

### Task 3: Open Source Release

**周期**：W23

内容：

- README / CONTRIBUTING / architecture docs
- install 与 quickstart
- replay demo
- 数据与 API key 安全说明
- license 与引用格式

### Task 4: Submission & Phase 5 Planning

**周期**：W24

内容：

- Paper #1 投稿版
- Paper #2 Goal Drift 草稿大纲
- Paper #3 TRS 长期计划
- Phase 5 预研：multi-agent risk propagation、mitigation、防御策略

### Phase 4 门禁

- 外部用户可在无 API key 情况下跑通 replay demo
- Paper #1 的主实验可一键复现
- Benchmark v0.1 有固定版本号和数据说明
- 开源发布不包含 `.env`、API key、`datasets/raw/` 大文件

---

## 研究方向优先级

| 方向 | 成熟度 | 工程难度 | 差异化潜力 | 定位 |
|------|--------|----------|------------|------|
| Goal Drift | 低 | 高 | 极高 | 核心研究方向，先定义后检测 |
| Trajectory Risk Modeling | 低 | 极高 | 极高 | 长期核心，依赖高质量 trajectory |
| Memory Poisoning | 中 | 中 | 高 | Paper #1 优先突破口 |
| Tool Security | 中 | 中 | 中高 | 注入与传播分析的重要支撑 |

---

## 关键风险与应对

### 风险 1: Phase 1 范围过大

问题：Telemetry、Memory、Runner 都是基础设施，原计划一周一个模块偏紧。

应对：每个模块先做 MVP 和验收测试；复杂 adapter、并行调度、实时 dashboard 延后。

### 风险 2: Goal Drift 定义不可操作

问题：定义过抽象会导致 Phase 3 无法实现或无法评估。

应对：W7-W8 只做形式化与 review；没有可计算性和可验证性就不进入检测实现。

### 风险 3: Telemetry 影响 Agent 行为

问题：观测数据进入 context window 会改变被测对象。

应对：side-channel collector、测试 input messages 不变、overhead 计量。

### 风险 4: 数据集质量不足

问题：Phase 3 检测有效性完全依赖 Phase 1-2 数据质量。

应对：每个 controlled scenario 必须有 clean baseline、seed、label、config、trajectory。

### 风险 5: Phase 4 产出过载

问题：5 周内完成两篇论文、200 场景 benchmark 和完整社区建设不现实。

应对：首次发布聚焦 Paper #1 + Benchmark v0.1；Paper #2/#3 作为后续路线。

---

## 阶段推进规则

1. Phase 1 未通过门禁，不实现 Phase 2 业务逻辑。
2. Goal Drift 未通过 W8 review，不实现 `arl.detection.goal_drift`。
3. 所有新 scenario 放入 `configs/scenarios/`，必须包含 seed 和 experiment_id。
4. 所有 trajectory 必须符合 `schemas/trajectory-v1.schema.json` 或经过版本化迁移。
5. 声称完成任务前必须运行相关 pytest / ruff。

---

## 当前进度

统计口径：每个 Phase 按 4 个主要 task 计数，总计 16 个主要 task。当前完成 8 / 16。

总体进度：`[########--------] 8/16 tasks - 50%`

| Phase | 进度条 | 完成度 | 当前状态 |
|-------|--------|--------|----------|
| Phase 1 - Sandbox & Telemetry Foundation | `[################]` | 4/4 tasks - 100% | 已完成 v0.1 |
| Phase 2 - Risk Injector & Goal Formalization | `[################]` | 4/4 tasks - 100% | 已完成 v0.1 |
| Phase 3 - Detection & Trajectory Modeling | `[----------------]` | 0/4 tasks - 0% | 下一步 Task 1 Trajectory Risk Modeling |
| Phase 4 - Research Output & Release | `[----------------]` | 0/4 tasks - 0% | 未开始 |

### 已完成任务

- Phase 1 · Task 1: Sandbox SDK v0.1
  - Direct API replay
  - LangGraph replay
  - AutoGen scaffold
  - Mock Tool Registry
  - isolated session
  - 5-step golden trajectory
  - sandbox tests and ruff passing
- Phase 1 · Task 2: Telemetry MVP
  - TelemetryStepEmitter side-channel collector
  - TrajectoryRecorder schema-compatible trajectory builder
  - telemetry overhead measurement
  - context non-interference tests
  - telemetry tests and ruff passing
- Phase 1 · Task 3: Memory Store MVP
  - InMemoryMemoryStore local MVP
  - namespace isolation
  - short-term / long-term / episodic layers
  - CRUD audit log
  - MemoryOpPayload telemetry bridge
- Phase 1 · Task 4: Experiment Runner MVP
  - serial scenario runner
  - `runs/` result directory layout
  - scenario / trajectory / metadata artifacts
  - minimal baseline diff
  - integration tests and ruff passing
- Phase 2 · Task 1: Goal Drift 形式化定义 v0.1
  - Goal Representation
  - probe protocol
  - W8 review checklist
  - lightweight spec validator
- Phase 2 · Task 2: Memory Poisoning Injector v0.1
  - semantic substitution / authority fabrication / temporal manipulation
  - light / medium / heavy intensity
  - memory audit log and `memory_ops` telemetry
- Phase 2 · Task 3: Tool Tampering Injector v0.1
  - registry proxy
  - response replacement / simulated delay / confidence degradation
  - targeted tool tamper labels
- Phase 2 · Task 4: Goal Perturbation Injector v0.1
  - system prompt / user goal perturbation
  - clean vs controlled scenarios
  - labeled trajectory metadata

### 当前下一步

- Phase 3 · Task 1: Trajectory Risk Modeling
  - 基于 Phase 1-2 的 schema-valid trajectories 构建规则 / 统计 baseline
  - 明确 TRS 输入、输出、失败案例与可解释 attribution
  - 继续遵守门禁：未明确要求前不实现 `arl.detection.goal_drift`

# 三赛事差异化参赛策略

> 一套内核，三个产品形态。本文档基于现有项目真实代码模块，给出三个赛事的差异化定位、复用关系、缺口分析与优化路线，确保 "不是同一个项目投三次"。

- 文档版本:v1
- 适用项目：Agent-Runtime-Security-Lab (多智能体对抗自进化框架)
- 时间线：赛事三临近截止 (优先冲刺) → 赛事一、赛事二 约两个月

------

## 0. 三赛事题目摘要

| 赛事       | 方向                         | 题眼                                                         |
| ---------- | ---------------------------- | ------------------------------------------------------------ |
| **赛事一** | 生成式大语言模型与智能体     | 用大模型驱动的**智能体**解析任务、规划步骤、环境感知、自主决策，解决领域实际问题 |
| **赛事二** | 大模型智能体安全             | 针对在线 LLM Agent, 设计**提示注入与工具滥用的检测→研判→阻断→溯源闭环防护系统**(SDK/Sidecar/MCP 中间代理 / Hook), 实现五大核心能力 |
| **赛事三** | 面向大模型及应用的安全性研究 | **红队视角**研究攻击面 + 设计**可嵌入 / 旁路的行为监督机制**(实时审计工具调用 / 代码执行 / 文件访问)+ 防御策略 |

------

## 1. 核心原则：一个内核，三个产品形态

要做到 "不是同一个项目投三次", 关键不是改内核，而是让三份交付物在

**产品形态、叙事主角、核心交付物**上各不相同 —— 共享底层、产出不同外壳。

|                | 赛事一                                          | 赛事二                                     | 赛事三                      |
| -------------- | ----------------------------------------------- | ------------------------------------------ | --------------------------- |
| **一句话定位** | 大模型驱动的多智能体自治系统 (安全是其应用场景) | MCP 中间代理防护网关 (注入 / 工具滥用闭环) | 红队攻防 + 旁路行为监督插件 |
| **叙事主角**   | Attack/Defense Agent 的自主规划与决策能力       | 防护系统 (检测→研判→阻断→溯源)             | 红队攻击面 + 监督审计       |
| **核心交付物** | 智能体决策报告 + 收敛曲线                       | MCP 代理 + 策略 DSL + 溯源 DAG             | 风险分析报告 + 实时监督看板 |
| **建议产品名** | AdvLoop「智驭」                                 | MCP-Sentinel「关哨」                       | RedSentinel「灵哨」         |
| **系统形态**   | CLI 闭环 demo                                   | Sidecar / MCP-in-the-middle 代理           | 可旁路插件 + Web 看板       |
| **被监督对象** | 电商 RAG agent                                  | 带 MCP / 子 Agent 的工具链                 | 真实开源 Agent (旁路嵌入)   |

> 三者复用同一个 `auto_attack / auto_defense / auto_evaluation` 内核，
>
> 但对外是三个独立仓库、三个独立可执行入口、三份独立报告。

------

## 2. 现有代码资产盘点 (复用底座)

经实际扫描，项目已具备以下可复用模块 (远超 "最小 demo"):

### 攻击侧 `auto_attack_system`

- `payloads/`:injection /jailbreak/leakage /obfuscation 四类载荷库
- `injectors/`:goal_perturbation /memory_poisoning/tool_tampering 注入器
- `indirect_injection.py`:HTML / Email (.eml) / Markdown 多格式投毒生成器
- `doc_poison.py`:PDF 投毒
- `threat_taxonomy.py`:7 类威胁分类法 + 合成靶场
- `attack_agent.py`: 攻击历史 / 失败反思 / 重规划 / 策略升级
- `llm_client.py`:SharedLLMClient (项目 API + 离线确定性 fallback)

### 防御侧 `auto_defense_system`

- `security/policy/engine.py`:**工具策略引擎 (JSON 可配，非硬编码)** — 已是策略 DSL 雏形
- `security/tool_guard.py`: 工具调用 allow/block + 风险等级 + attribution 归因
- `security/goal_guard.py`: 目标漂移 allow/block + 归因
- `security/memory_guard.py`: 记忆污染 allow/block + 归因
- `security/permission.py`: 角色最小权限 (guest/user/admin)
- `security/firewall/`: 输入防火墙 (classifier + input_guard)
- `security/output/filter.py`: 输出过滤
- `security/ingest/doc_scanner.py`: 文档投毒扫描
- `security/audit.py`:**审计哈希链 + Ed25519 签名 + trace_id /tool_call_id**
- `security/integrity.py`: 完整性校验
- `ecommerce_agent/`: 本地电商 RAG Agent (被测对象)
- `defense_agent.py`: 据损伤报告自动选加固动作 (prompt/rule/retrieval/rerank)

### 评测侧 `auto_evaluation_system`

- `detection/`:trajectory_risk /goal_drift/memory_integrity 检测基线
- `runner/closed_loop.py`: 闭环评测
- `benchmarks/`:benchmark / doc_poison_eval / output_eval
- `events/emitter.py`: 事件发射 (看板数据源)
- `dashboard/`: 风险看板 (目前离线)
- `product_api/app.py`:FastAPI 服务 (register/session/evaluation 接口)
- `comp4_evidence.py`: 收敛曲线 / 雷达图 / 消融 / 数据卡

> **关键结论**: 赛事二的三大缺口 (策略 DSL、溯源、抗绕过) 中，
>
> 策略 DSL 有 `policy/engine.py` 雏形、溯源有 `audit` 的 trace_id + guard 的
>
> attribution 地基，**并非从零开始**。

------

## 3. 共享内核 vs 各赛事净增量

| 模块   | 共享内核 (三赛都用)                                   | 赛一净增             | 赛二净增                                      | 赛三净增                      |
| ------ | ----------------------------------------------------- | -------------------- | --------------------------------------------- | ----------------------------- |
| 攻击侧 | payloads / injectors / threat_taxonomy / attack_agent | —                    | 抗绕过用例集 (多语言 / Unicode / 分词 / 注释) | 越狱用例集成文                |
| 防御侧 | policy/engine、tool/goal/memory guard、audit          | —                    | 语义策略 DSL 升级、子 Agent 派发管控          | 三态 ask 补全、可旁路插件封装 |
| 评测侧 | detection、closed_loop、benchmark                     | 智能体规划过程可视化 | 跨 MCP 溯源 DAG、意图 - 计划 - 工具对齐       | 实时监督看板                  |
| 外壳   | —                                                     | CLI 报告             | MCP-in-the-middle 代理                        | Web 看板 + 模拟业务工具       |
| 模型   | SharedLLMClient                                       | 接 Qwen              | 接 Qwen                                       | 接 Qwen                       |

------

## 4. 逐赛事：硬要求 → 已有 → 缺口 → 优化

### 4.1 赛事三 (先做，快截止)— 复用率约 80%

| 赛题硬要求                                     | 已有模块                                                     | 缺口 / 优化                                   |
| ---------------------------------------------- | ------------------------------------------------------------ | --------------------------------------------- |
| ≥3 类攻击场景 + 对抗样本 + 越狱用例 + 攻击脚本 | payloads(injection/jailbreak/leakage/obfuscation)、attack_agent | 把现有 payload 成文为越狱用例集；接 Qwen 实测 |
| 行为监督：拦截 agent↔工具，allow/deny/ask      | tool_guard(allow/block)、policy/engine                       | **补 ask (询问) 态** — 当前为二态             |
| 开源应用作被监督对象                           | ecommerce_agent (自写)                                       | 挂真实开源 Agent, 或强调 "可旁路嵌入"         |
| 模型调用链路监控插件                           | audit (哈希链 + 签名)、events/emitter                        | 封装成 "旁路插件" 形态                        |
| **监督端实时展示**告警 / 阻断                  | dashboard (仅离线)                                           | **新建实时看板 (最大短板)**                   |
| 模拟业务工具 (发邮件 / 读写文件 / 调 API)      | tools/、indirect_injection                                   | 补几个模拟业务工具节点                        |

**冲刺四步**:① 接 Qwen → ② 实时看板 → ③ 补 ask 态 → ④ 风险分析报告成文。

### 4.2 赛事二 (两个月，含金量最高)— 复用率约 55%

| 五大能力                                 | 已有基础                                                     | 净增工作                                                     |
| ---------------------------------------- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| 能力 1 多源注入识别 (直接 / 间接 / 记忆) | indirect_injection(HTML/Email/MD)、doc_scanner、memory_guard | 补 URL / 工单 / 邮件 / MCP 返回字段 / 工具注册描述 等间接源  |
| 能力 2 意图 - 计划 - 工具语义对齐        | goal_guard、detection/goal_drift                             | **新做 "用户意图 vs 实际执行偏离度" 可解释研判**             |
| 能力 3 细粒度工具策略 + 三态决策         | policy/engine (JSON 可配) 已是雏形                           | 升级为**语义策略 DSL**(fs.write/net.fetch/exec/git.push 具体规则)+ 补 ask 态 |
| 能力 4 跨 MCP / 子 Agent 溯源 DAG        | audit 的 trace_id/tool_call_id、guard 的 attribution         | **新建 MCP 代理 + 子 Agent 链路还原 + DAG / 时序图 (最大缺口)** |
| 能力 5 对抗鲁棒性 (抗绕过)               | payloads/obfuscation                                         | **建系统化绕过用例集**(多语言 / Unicode 同形 / 零宽 / 分词 / 注释 / 稀释 / 语义伪装) |

**主攻路径**: 选 MCP-in-the-middle 形态作为新外壳 → 升级语义策略 DSL → 构建溯源 DAG → 补抗绕过用例集。前两件命中能力 3, 溯源命中能力 4 (最大缺口), 抗绕过命中能力 5。

#### 赛事二 8 周排期建议

| 周次 | 目标                                                         | 命中能力  |
| ---- | ------------------------------------------------------------ | --------- |
| 1-2  | 搭 MCP 中间代理骨架：拦在 Agent↔工具之间，截获 fs/net/exec/git 调用 | 形态要求  |
| 3-4  | 语义策略 DSL + 三态决策 (敏感路径写入 / 密钥外发 /base64 执行 / 检视时禁 push) | 能力 3    |
| 5-6  | 意图 - 计划 - 工具语义对齐 (偏离度可解释研判)                | 能力 2    |
| 7    | 跨 MCP / 子 Agent 溯源 → 攻击路径 DAG + 时序链路图           | 能力 4    |
| 8    | 抗绕过用例集 + 多源注入补间接源                              | 能力 1、5 |

### 4.3 赛事一 (两个月，几乎零代码)— 复用率约 60%

| 赛题关键词          | 项目体现 (无需改代码)                     |
| ------------------- | ----------------------------------------- |
| 解析复杂任务指令    | Attack/Defense Agent 解析安全目标与约束   |
| 规划任务执行步骤    | 生成攻击 / 加固步骤 (reflection 重规划)   |
| 环境感知            | Evaluation Agent 读响应 / 工具调用 / 审计 |
| 自主决策            | Defense Agent 选加固动作                  |
| 信息检索 + 数据分析 | RAG 检索 + ASR / 泄露率统计               |

**唯一优化**: 给 Agent 加一段 "任务解析→步骤规划" 的显式可视化输出，

让智能体规划能力可见。报告侧重 agent 自治，弱化攻防对抗。

------

## 5. 确保 "不是同一个项目" 的实质区分清单

1. **三个独立仓库**:`adv-loop`(赛一)、`sentinel-mcp`(赛二)、`red-sentinel`(赛三), 各自 README / 报告 / 入口不同。
2. **三个不同可执行入口**: 赛一 `python run.py --agent-demo`; 赛二 `mcp-proxy serve`; 赛三 `python run.py --monitor`(起看板)。
3. **三份不同核心产出**: 赛一 = 智能体决策报告；赛二 = 溯源 DAG + 策略 DSL; 赛三 = 风险报告 + 实时看板。
4. **三个不同被测对象**: 赛一 = 电商 agent; 赛二 = 带 MCP / 子 agent 工具链；赛三 = 开源 agent 旁路。
5. **三张不同的 "赛题交付物↔模块" 映射表**, 主语各不相同。

> 报名前务必确认各赛事章程是否允许同一作品多投 / 是否要求实质性差异；
>
> 以上区分策略即为满足 "实质性差异" 的设计。

------

## 6. 行动优先级 (对齐时间线)

| 阶段              | 任务                                              | 分工                                               |
| ----------------- | ------------------------------------------------- | -------------------------------------------------- |
| 现在 → 赛三截止   | 接 Qwen + 实时看板 + ask 态 + 风险报告            | 代码 / 报告由助手产出，本地起看板 + 跑 Qwen 由本人 |
| 赛三交完～第 4 周 | 赛一报告 (换叙事)+ 规划可视化小增强               | 助手主笔，本人审                                   |
| 第 3 周 → 第 8 周 | 赛二：MCP 代理 + 策略 DSL + 溯源 DAG + 抗绕过用例 | 助手分模块实现，本人联调                           |

------

## 7. 接真模型 (Qwen) 说明

- 现状：离线模式下 SharedLLMClient 不真实调用模型，攻击成败由靶场 resistance 阈值判定。
- 接 Qwen 后：攻击 payload 真实发送给 Qwen, 以其真实回复判定是否被攻破；评测可用 LLM-as-judge + 客观规则交叉验证。
- 接入方式：Qwen DashScope 提供 OpenAI 兼容接口，只需将 `LLM_API_BASE / LLM_API_KEY / LLM_MODEL` 指向 Qwen (如 qwen-plus /qwen-max)。
- 双线并存:`--offline` 确定性兜底 (答辩防翻车)+ 接 Qwen 真实攻击线 (产出真实 ASR 证据)。

------

## 附：三赛事一句话差异化总结

- **赛事一**: 我做了一个会自己规划、自己决策的多智能体系统，它解决的实际问题恰好是 LLM 安全。
- **赛事二**: 我做了一个挡在 Agent 和工具之间的 MCP 防护网关，能检测注入、研判意图偏离、三态阻断、全链路溯源。
- **赛事三**: 我从红队视角打穿了大模型应用，并做了一个旁路监督插件，实时审计并展示每一次工具调用的放行 / 拒绝 / 询问。

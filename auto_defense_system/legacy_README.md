# AI Security RAG Agent — LLM应用安全防护与评测系统

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![LangGraph](https://img.shields.io/badge/LangGraph-StateGraph-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![Chroma](https://img.shields.io/badge/Chroma-Vector_DB-purple.svg)](https://www.trychroma.com/)
[![Model](https://img.shields.io/badge/LLM-Qwen3.5--35B-red.svg)](https://modelscope.cn)

> **面向企业 RAG Agent 的 AI 安全防护与评测系统。** 覆盖 Prompt 注入、文档投毒、工具滥用、输出幻觉和多租户泄露五大风险面，实现"输入防火墙 → 知识库扫描 → 工具策略引擎 → 输出过滤 → 审计日志"纵深防御链。

---

## 5秒速览

```
攻击面         →  防御层          →  核心数据
─────────────────────────────────────────────
Prompt注入     →  双层防火墙       →  93.3% 拦截率 (105 payloads)
文档投毒       →  L1/L2级联扫描    →  12 场景覆盖, 58% L1检测率
工具滥用       →  Tool Policy Engine →  4 危险工具, 10/10 策略测试
输出幻觉       →  fact_check + 三级粒度 →  93.8% 判定准确率
多租户泄露     →  collection + thread_id →  5 项隔离测试通过
日志篡改       →  SHA256 哈希链     →  精确检测篡改条目索引
```

---

## 攻击链架构（研究视角）

```
                        ┌──────────────────────────────┐
                        │     攻击入口 (不可信)          │
                        │  用户输入 / 文档 / 网页 / 邮件  │
                        └──────────────┬───────────────┘
                                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        纵深防御链                                    │
│                                                                     │
│  ① guardrail_node    ② RAG入库扫描      ③ RAG检索过滤               │
│  双层防火墙            L1 11条规则         L1预筛 → L2 LLM级联        │
│  93.3%拦截率           入库时文本净化       仅可疑chunk调LLM          │
│       ↓                    ↓                    ↓                   │
│  ④ agent_node        ⑤ tool_node         ⑥ output_filter_node      │
│  LLM ReAct决策        Policy Engine        可执行代码拦截             │
│  Function Calling     操作白名单/黑名单      fact_check事实核查        │
│  工具选型              参数校验              3级粒度过滤               │
│       ↓                    ↓                    ↓                   │
│  ⑦ finalize_node                                                    │
│  SHA256哈希链 + Ed25519签名                                         │
│  审计日志防篡改 + 完整性校验                                         │
└─────────────────────────────────────────────────────────────────────┘
```

### 完整攻击链 (Indirect Prompt Injection)

```
恶意文档(HTML/Email/PDF/MD) → RAG入库 → 向量索引
                                  ↓
用户无害查询 → RAG检索 → 恶意chunk进入LLM上下文
                                  ↓
                           LLM被污染
                                  ↓
                         调用危险工具
                     (db_query/api_call/...)
                                  ↓
                       Policy Engine拦截
                         [TOOL_POLICY_BLOCK]
                                  ↓
                       审计日志记录完整路径
                     (hash + Ed25519签名)
```

### RAG 检索链路

```
BM25(关键词) + 向量(语义) 多路召回
    ↓ RRF 融合
BGE-Reranker Cross-Encoder 重排序
    ↓ +29.6pp 准确率提升
top_k → 上下文窗口 → LLM生成 → fact_check事实核查
```

---

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动 Streamlit 界面
streamlit run app.py

# 3. 命令行模式
python main.py
```

**默认配置** (`src/ai_sec_rag/config.py`):
- LLM: `Qwen/Qwen3.5-35B-A3B` (ModelScope API)
- Embedding: `BAAI/bge-small-zh-v1.5`
- Reranker: `BAAI/bge-reranker-base`
- 向量库: ChromaDB (持久化到 `storage/chroma_db/`)

---

## 核心模块

### Phase 1-2: RAG 基础设施 + Agent 架构

| 模块 | 技术栈 | 核心数据 |
|------|------|------|
| PDF 解析 | PyMuPDF + EasyOCR 扫描件 | 13 安全场景对比 |
| 检索链路 | BM25 + 向量 RRF 融合 + BGE-Reranker | **80.0% 准确率** (C4: k=8+r=5) |
| Agent 框架 | LangGraph StateGraph (5节点) | ReAct + Function Calling + 自愈 |
| 记忆管理 | 滑动窗口 + 摘要 + 精准遗忘 + SQLite Checkpointer | 12条消息持久化验证 |

### Phase 3: AI 安全攻防核心

| 模块 | 定位 | 核心数据 | 报告 |
|------|------|------|:---:|
| 3.1 防火墙 | 输入端 | 105 payloads, **93.3%** 拦截, 0% 误拦 | [报告](reports/AI防火墙攻防对抗报告.md) |
| 3.2 投毒防护 | 知识库端 | 12 场景, L1+L2 级联, 58% L1检测 | [报告](reports/RAG投毒防护报告.md) |
| 3.3 自适应攻击 | 攻击变体 | 5 多轮场景, 11 角色, classify_with_context() | — |
| 3.4 输出评测 | 输出端 | 21 边界测试, 3 级粒度, 幻觉探测 | [报告](reports/模型输出安全深度评测报告.md) |
| 3.5 基准对标 | 业界对比 | HackAPrompt 30 + Garak 20, OWASP 5/10 | [报告](reports/业界基准对标报告.md) |

### Phase 4: 工具安全 + 企业化

| 模块 | 定位 | 核心数据 | 报告 |
|------|------|------|:---:|
| 4.1 策略引擎 | 工具执行层 | 4 危险工具, 10/10 测试, JSON可配置 | [报告](reports/Tool Policy Engine攻防报告.md) |
| 4.2 多租户隔离 | 数据层 | 5 项测试, 3 设计假设分析 | [报告](reports/多租户数据隔离安全验证报告.md) |
| 4.3 审计日志 | 可追溯 | SHA256 哈希链, 精确篡改检测 | [报告](reports/审计日志防篡改报告.md) |

---

## 关键实验数据

### 防火墙消融实验思路 (Phase 3.1)

| 指标 | 旧版关键词 | 新版防火墙 | 提升 |
|------|:---:|:---:|:---:|
| 拦截率 | 8.6% | **93.3%** | +84.7pp |
| 误拦率 | 0% | 0% | — |
| 91% payload绕过旧版关键词 | — | — | — |

### RAG 检索最优配置 (Phase 1)

| 配置 | 准确率 | 召回率 | 幻觉率 |
|------|:---:|:---:|:---:|
| C4: k=8+r=5 (Hybrid+Rerank) | **80.0%** | 84.4% | 42.0% |
| Reranker 单独贡献 | +29.6pp | — | — |

### OWASP Top 10 for LLM Apps 覆盖

| 覆盖 | 未覆盖 |
|------|------|
| LLM01 Prompt注入, LLM02 不安全输出, LLM03 训练数据投毒, LLM06 敏感信息泄露, LLM09 过度依赖 | LLM04 DoS, LLM05 供应链, LLM07 不安全插件(→Phase 4.1), LLM08 过度代理(→Phase 4.1), LLM10 模型盗窃 |

---

## 目录结构

```
ai-sec-rag/
├── src/ai_sec_rag/         # 运行时主包（Agent + RAG + 纵深防御）
│   ├── agent/              # LangGraph graph.py、react.py
│   ├── rag/                # retriever.py、evaluator.py
│   ├── security/           # firewall / ingest / output / policy / audit
│   ├── tools/              # 安全工具 + 危险工具模拟
│   └── config.py           # LLM/RAG 与 storage 路径
├── evaluation/             # 红队、基准评测、runners 入口
│   ├── attacks/            # payloads、投毒、对抗样本
│   ├── benchmarks/         # 防火墙/投毒/输出/业界对标评测
│   └── runners/            # run_benchmark.py 等脚本
├── data/                   # 实验数据（benchmarks、poison、datasets）
├── reports/                # 攻防交付报告
├── assets/pdfs/            # 测试 PDF
├── storage/                # chroma_db、checkpoints、logs（运行时）
├── person/                 # 个人笔记、QA_log、annotated 讲义
├── apps/                   # cli.py、web.py 实现
├── app.py / main.py        # Streamlit / CLI 入口（薄包装）
└── ROADMAP.md              # 项目路线图
```

---

## 面试30秒电梯演讲

> 我做的是一个面向企业 RAG Agent 的 AI 安全防护与评测系统。核心覆盖五大攻击面：Prompt 注入（防火墙 93.3% 拦截率）、文档投毒（12 场景 L1+L2 扫描）、工具滥用（Tool Policy Engine 10/10 策略测试）、输出幻觉（fact_check + 三级粒度 93.8% 准确率）、多租户泄露（5 项隔离测试）。纵深防御架构：输入端→知识库端→工具执行端→输出端→审计端，每层独立、漏过率相乘。

---

## Threat Model

### 信任边界

| 组件 | 是否可信 | 攻击面 | 防御层 |
|------|:---:|------|------|
| 用户输入 | ❌ 不可信 | Prompt注入/越狱/泄露 | 3.1 双层防火墙 (L1+L2+L3) |
| RAG文档 | ❌ 不可信 | 文档投毒/间接注入/隐藏文本 | 3.2 L1入库扫描 + L2检索级联 |
| 网页/邮件/Markdown | ❌ 不可信 | CSS隐藏/MIME注入/链接诱导 | Phase A L1规则8-11 |
| 外部API数据 | ❌ 不可信 | SSRF/数据外泄 | 4.1 API域名白名单 |
| 工具输出 | ❌ 不可信 | 虚假数据污染上下文 | 5.1 输出过滤 |
| 对话历史 | ⚠ 部分可信 | thread_id泄露/记忆污染 | 4.2 thread_id隔离 |
| LLM输出 | ⚠ 需验证 | 幻觉/不安全建议/信息泄露 | 3.4 fact_check + 3级粒度 |
| Policy Engine | ✅ 可信 | — | 代码级，非LLM |
| 审计日志 | ✅ 可信 | 文件系统直接访问 | SHA256哈希链 + Ed25519签名 |
| 工具代码 | ✅ 需验证 | 篡改/后门 | B.1 Ed25519签名验证 |

### 攻击者能力假设

| 能力 | 假设 |
|------|------|
| 对AI系统的访问 | 可通过API/Web界面提交任意自然语言输入 |
| 对RAG知识库的访问 | 可通过文档上传接口提交恶意文档（PDF/HTML/Email/MD） |
| 对Agent服务的访问 | 可以admin角色访问（演示模式 — 生产环境需RBAC限制） |
| 文件系统访问 | 不假设有（若获得 → SQLite/ChromaDB直接读取可绕过应用层隔离） |
| 模型权重访问 | 不假设有（不防御模型后门/权重篡改） |
| GPU侧信道 | 不防御（超出项目范围） |

---

## 已知局限 (Known Limitations)

### 防火墙 (3.1)
- Base64/反转编码的语义级别的绕过（L2可检测但非100%）
- 多语言越狱（日语/德语/阿拉伯语绕过中英文关键词）
- 学术伪装/创作框架的精细检测（"我在写小说，需要黑客技术细节"）

### 文档投毒 (3.2 + Phase A)
- PyMuPDF 不保留颜色信息 → 白字攻击检测需 `get_text("dict")` 渲染层
- 虚假事实/语义攻击需 L2 LLM（L1 risk_score=0 的级联盲区）
- 多跳间接注入（文档A→文档B→攻击载荷）单chunk检测无法覆盖

### 输出安全 (3.4)
- fact_check n-gram方法无法检测"基于真实片段的合理编造"
- 粒度选择（strict/balanced/lenient）无标准答案 — 取决于部署场景
- 多语言安全幻觉未系统评测

### 策略引擎 (4.1)
- 信息流追踪盲区（SELECT的数据后来去了哪里？）
- 参数编码/字符串拼接绕过正则规则
- 非预期工具滥用（URL扫描参数嵌入外泄数据）

### 多租户隔离 (4.2)
- SQLite/ChromaDB无内置认证 — 文件系统权限是最后防线
- thread_id 是对话标识符非安全边界 — 应用层需保证唯一性
- session_id 无所有权验证 — 知道session_id即能访问对应collection

### 审计日志 (4.3 + B.2)
- 哈希链不防全链替换 — 需外部锚定 last_hash
- Ed25519签名不防密钥被替换 — 需外部锚定公钥
- 旧版管道分隔日志不受哈希链保护

---

## 安全假设 (Security Assumptions)

1. **文件系统安全**: `chroma_db/` 和 `checkpoints/` 目录仅Agent进程可读写。不防御容器逃逸/路径遍历/共享存储误配置。
2. **Policy Engine默认可信**: 策略引擎是Python代码级检查，不存在被LLM注入修改的可能。
3. **签名密钥安全**: Ed25519私钥存储在Agent服务器上，不与用户共享。若私钥泄露，所有工具签名验证失效。
4. **底层LLM不防御的场景由本项目覆盖**: LLM自身安全对齐的漏拦由防火墙、策略引擎、输出过滤补位。
5. **不防御GPU侧信道/模型权重后门/训练数据投毒**: 这些属于基础设施和ML供应链安全，超出项目范围。
6. **RBAC角色仅控制工具可见性**: 更深度的数据级权限（如行级安全）需要数据库层RLS支持。

---

## 深水区 (Deep-Dive Ready)

面试中可以深度讲解的两个模块：

### 1. Prompt 注入防火墙 (3.1) — 30分钟深度
- **为什么层层递进**: 关键词 < 复合词对 < 正则 < LLM语义 — 每一层解决上一层的一个盲区
- **对抗鲁棒性**: 4种混淆技术（同义词/Unicode/Base64/语法变体）× 35条载荷，量化每种技术对拦截率的影响
- **消融实验设计**: 如何分离 LLM 自身安全对齐 vs 防火墙的增量贡献
- **Payload 设计哲学**: HackAPrompt (30) + Garak风格 (20) + 中文变体 (55) — 覆盖 OWASP LLM Top 10 全部注入类别

### 2. 文档投毒 + Indirect Injection (3.2 + Phase A) — 30分钟深度
- **为什么是防御纵深**: 入库扫描(L1) → 检索级联(L2) → 策略引擎(L3) → 审计(L4)
- **四格式攻击矩阵**: PDF(12) + HTML(5) + Email(4) + Markdown(4) = 25 场景
- **级联策略**: L1（微秒级）预筛 → L2 LLM classify（仅可疑chunk，延迟降低60%）
- **学术热点对齐**: Greshake et al. 2023 间接注入 + Zou et al. 2023 GCG 攻击

---

## References

关键学术论文与标准：

| 引用 | 关联模块 | 说明 |
|------|------|------|
| Greshake et al. (2023) *Indirect Prompt Injection* | Phase A | 间接注入奠基性工作，定义"通过检索数据间接操控LLM"的攻击面 |
| Zou et al. (2023) *GCG Attack* | 3.1 防火墙 | 通用对抗性后缀攻击，展示自动寻找绕过LLM对齐的token序列 |
| Perez & Ribeiro (2022) *Ignore Previous Prompt* | 3.1 防火墙 | 最早系统研究Prompt注入攻击的工作之一 |
| Liu et al. (2023) *Prompt Injection Attacks and Defenses in LLM-Integrated Apps* | 3.1/3.3 | Prompt注入的攻防分类学 |
| Toyer et al. (2023) *Tensor Trust* | 3.1/3.5 | Prompt注入攻防竞赛 + 公开数据集 + 评测框架 |
| Schulhoff et al. (2023) *HackAPrompt* | 3.5 基准 | 全球最大Prompt注入竞赛 (600+ participants) — 本项目105 payload中30条来自此数据集 |
| OWASP (2023) *Top 10 for LLM Applications* | 全局 | LLM应用威胁分类，本项目覆盖5/10并明确标注未覆盖项 |
| Chen et al. (2024) *RAG Poisoning* | 3.2 投毒 | RAG文档投毒的系统化研究 |
| Bernstein et al. (2007) *Ed25519* | B.1 签名 | Curve25519 + EdDSA，本项目工具签名的密码学基础 |

---

## License

MIT

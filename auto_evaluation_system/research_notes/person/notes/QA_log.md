# QA Log

## 2026-06-01

- 原始问题：之前的电话面，面试官跟我说让我多关注一下前沿的大模型知识，要了解agent的架构，可以向小白介绍清楚大模型内部的机制，例如他就问了我为什么大模型会被越狱，同时我的简历应该是这份
- 答案核心：新版简历应定位为 AI Evaluation / Agent Evaluation / 大模型安全评测；面试需要补齐三条主线：大模型内部机制（token、embedding、Transformer、logits、sampling、alignment）、Agent 架构（LLM、planner/controller、tools、memory/state、guardrail/trace）、越狱机理（LLM 没有天然指令/数据隔离，安全对齐是软约束，攻击 prompt 通过上下文竞争和分布外输入绕过安全行为）。
- 相关引用：Transformer <https://arxiv.org/abs/1706.03762>；ReAct <https://arxiv.org/abs/2210.03629>；Toolformer <https://arxiv.org/abs/2302.04761>；NCSC Prompt Injection <https://www.ncsc.gov.uk/blog-post/prompt-injection-is-not-sql-injection>；OWASP LLM06 Excessive Agency <https://genai.owasp.org/llmrisk/llm062025-excessive-agency/>；MCP Architecture <https://modelcontextprotocol.io/docs/learn/architecture>

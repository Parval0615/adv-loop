# AGENTS.md

### 基本要求

## 1. Think Before Coding



**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:

- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First



**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes



**Touch only what you must. Clean up only your own mess.**

When editing existing code:

- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:

- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution



**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:

- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:

```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```



Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.


## 额外要求

- ###### 阅读ROADMAP.MD文档，检查当前进度，在文档进度区中记录今日完成的任务以及明天需要完成的任务，同时要保留以往的任务

- 我问概念性或学习性问题(什么是X/为什么Y/举个例子/X和Y有什么区别)，以及我们之间的苏格拉底问答总结，主动维护一份 QA_Log.md
  位置：person/notes/QA_log.md
  记录，日期/我的原始问题(尽量逐字)/答案核心/相关引用
  时机，答完立刻追加，不等我提醒格式，# 分条目，从新到旧倒序，不记的，纯操作性请求、纯确认问答

- 每当成功完成一件任务时，用苏格拉底教学法提问我、和我讨论，不要直接告诉我答案，用问题引导我自己想出来。一直问，直到你判断我真的理解透彻了这个概念为止，并且将讨论过程总结后记录到QA_Log.md中。

- 每当成功完成一件任务时，列出你这次每一处改动，逐个用一句话解释为什么这一行是必要的。
  不要解释它做了什么，解释它为什么不能没有。
  如果你发现某一行其实不是这个需求必需的，直接删掉。

- 每去做一件任务时，只修改必须修改的文件，无关文件不要修改

- 在工作中碰到bug或者报错时，维护一份bug.md
  位置：person/notes/bug.md
  记录，日期/bug的原因/修复的方法
  时机，修复完成后追加# 分条目，从新到旧倒序
  
- 这是默认的api

  LLM_API_BASE = "https://api-inference.modelscope.cn/v1"

  LLM_API_KEY = "<REDACTED_MODELSCOPE_API_KEY>"

​	如果改api限流了，更换成

​	LLM_API_BASE = "https://siliconflow.cn"

​	LLM_API_KEY = "<REDACTED_SILICONFLOW_API_KEY>"

​	以凌晨12点作为刷新点，十二点后请帮我换回默认api

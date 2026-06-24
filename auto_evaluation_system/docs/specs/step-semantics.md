# Step 语义规范

Task 1 定稿 · Task 2 迁移时不改 schema / StepEvent 字段。

## 一步的定义

| `step_type` | 触发 | 计数 |
|-------------|------|------|
| `llm_inference` | 每次 chat completion HTTP 请求 | 1 步 |
| `tool_call` | 每次实际执行一个 tool | 1 步 |

## Golden 5 步结构

任务：查天气 → 搜新闻 → LLM 文字汇总（无第三 tool）。

```
llm_inference → tool_call → llm_inference → tool_call → llm_inference
```

完整 JSON 靶子见 [`schemas/fixtures/golden-5step-trajectory.json`](../../schemas/fixtures/golden-5step-trajectory.json)：

```json
{
  "schema_version": "1.0",
  "session_id": "00000000-0000-4000-8000-000000000001",
  "experiment_id": "p1-sandbox-5step-golden",
  "seed": 42,
  "framework": "direct_api",
  "goal": { "text": "Query weather, search news, summarize in text." },
  "injection_mode": "none",
  "steps": [
    {
      "step_index": 0,
      "step_type": "llm_inference",
      "timestamp": "2026-01-01T00:00:00+00:00",
      "llm": {
        "model": "gpt-4o-mini",
        "turn_index": 0,
        "tool_call_intents": [{ "call_id": "call_weather_001", "name": "get_weather", "arguments": { "city": "Beijing" } }]
      }
    },
    {
      "step_index": 1,
      "step_type": "tool_call",
      "timestamp": "2026-01-01T00:00:01+00:00",
      "tool_call": {
        "call_id": "call_weather_001",
        "name": "get_weather",
        "parent_turn_index": 0
      }
    },
    {
      "step_index": 2,
      "step_type": "llm_inference",
      "timestamp": "2026-01-01T00:00:02+00:00",
      "llm": { "turn_index": 1, "tool_call_intents": [{ "name": "search_news" }] }
    },
    {
      "step_index": 3,
      "step_type": "tool_call",
      "timestamp": "2026-01-01T00:00:03+00:00",
      "tool_call": { "name": "search_news", "parent_turn_index": 1 }
    },
    {
      "step_index": 4,
      "step_type": "llm_inference",
      "timestamp": "2026-01-01T00:00:04+00:00",
      "llm": {
        "turn_index": 2,
        "output_content": "Beijing is sunny at 22C. Top tech news: AI agents gain runtime security tooling.",
        "tool_call_intents": []
      }
    }
  ]
}
```

（以上为结构示意；完整字段以 fixture 文件为准。）

## 验证

```bash
pytest tests/sandbox/test_golden_trajectory_schema.py -q
```

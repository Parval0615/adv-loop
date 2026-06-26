# Sentinel Proxy

`sentinel_proxy` is the MCP-Sentinel interception layer used by the local arena.
It wraps every TP-00 development-agent tool call and sends it through one
pipeline:

```text
normalizer -> injection_radar -> intent_aligner -> policy_dsl -> trace_dag
```

Modes:

- `observe`: record the selected decision and still execute the tool.
- `enforce`: execute only `allow`; return `blocked` or `requires_confirmation`
  for `block` and `ask`.

Artifacts written by arena runs include:

- `events.jsonl`
- `sentinel_decisions.jsonl`
- `trace_graph.json`
- `trace_report.json`
- `trace_timeline.jsonl`
- `trace_graph.md`
- `trace_integrity.json`

The implementation remains local and deterministic. It does not connect to real
MCP servers, real private keys, real external endpoints, or real remote git
repositories.

Current limits:

- Detection is deterministic and fixture-oriented; it is not a live LLM security
  classifier.
- `policy_dsl` loads declarative default rules from `default_rules.json`, but it
  is still a minimal arena policy language, not a general-purpose policy system.
- `trace_dag` produces local evidence artifacts for review; it is not a
  production audit backend.

# Sentinel Proxy Skeleton

`sentinel_proxy` 是 TP-01 的 MCP-Sentinel 代理骨架。它为 TP-00 研发助手靶场提供统一的拦截入口、上下文聚合和可插拔三态裁决流水线。

当前默认 stage 都返回 `allow`，其中 `normalizer` 会先写入归一化记录：

```text
normalizer -> radar -> aligner -> policy -> trace
```

代理模式：

- `observe`：记录真实裁决，但继续透传执行。
- `enforce`：只执行 `allow`；`block` 和 `ask` 不执行真实工具。

本包不实现真实注入识别、意图对齐、策略 DSL 或 DAG 溯源；这些能力由后续任务包补齐。

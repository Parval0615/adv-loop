# Infrastructure

## Docker（Phase 4）

`docker/` 目录将提供：

- Sandbox + Memory（PostgreSQL + Qdrant/Chroma）+ Runner 的一键 compose
- AgentRiskBench 评测环境
- 可复现实验的固定镜像版本

当前为占位。Phase 1 Memory Store 选型确定后开始编写 Dockerfile。

## 规划服务

| 服务 | 用途 |
|------|------|
| `arl-runner` | 实验调度 |
| `postgres` | 关系型 memory + audit log |
| `qdrant` / `chroma` | 向量 memory |
| `dashboard` | Phase 3 风险看板 |

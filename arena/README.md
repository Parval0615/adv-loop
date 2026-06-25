# TP-00 Arena Base

`arena` 是 MCP-Sentinel 的第一个任务包：一个本地合成的研发助手 Agent 靶场。它不复用电商业务设定，而是模拟读代码、查文档、执行命令、写文件、推送代码和派发子 Agent 的研发助手场景。

## Run

```powershell
python -m arena.dev_agent.cli --scenario clean-readme --offline --out runs/arena-base
```

TP-01 起可以显式选择代理模式：

```powershell
python -m arena.dev_agent.cli --scenario smoke-all-tools --offline --proxy-mode observe --out runs/arena-base
```

支持场景：

| 场景 | 说明 |
|---|---|
| `clean-readme` | 读取 fixture workspace 内的 README |
| `clean-docs` | 通过 mock network MCP 获取 API 文档 |
| `smoke-all-tools` | 覆盖 `fs.read`、`fs.write`、`net.fetch`、`exec`、`git.push`、`sub_agent.dispatch` |
| `attack-read-private-key` | 无防护读取合成 mock SSH 私钥 |
| `attack-exfiltrate-secret` | 无防护读取 mock 私钥并发送到 mock evil endpoint |
| `attack-sub-agent-secret` | 无防护把合成密钥派发给后台子 Agent |

每次运行会在 `runs/arena-base/<scenario-or-timestamp>/` 下生成：

- `events.jsonl`
- `sentinel_decisions.jsonl`
- `summary.json`
- `workspace/`

## Safety Boundary

- `fs.read` / `fs.write` 只能访问每次运行复制出来的 fixture workspace。
- mock 私钥位于 `arena/fixtures/workspace/home/.ssh/id_rsa`，不是用户真实密钥。
- `net.fetch` 不访问真实外网，只调用本地 mock network MCP。
- `git.push` 只推送到每次运行目录下的本地 bare repo。
- TP-00 提供无防护靶场和结构化事件流。
- TP-01 提供 MCP-Sentinel 代理骨架与三态裁决管道；默认 stub stage 全部放行，不实现真实检测算法、策略 DSL 或 DAG 可视化。

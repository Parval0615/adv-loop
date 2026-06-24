# Contributing

感谢关注 Agent Runtime Security Lab。本仓库处于早期 scaffold 阶段，Phase 1 基础设施正在构建中。

## 开发环境

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## 阶段顺序

请按 [ROADMAP.md](./ROADMAP.md) 阶段推进，不要越级：

1. Phase 1 工程底座（当前）
2. Phase 2 风险注入 + Goal Drift 形式化
3. Phase 3 检测算法
4. Phase 4 论文 / Benchmark / 开源

## 代码规范

- Python ≥ 3.11
- `ruff` 格式化与 lint（line-length 100）
- 测试镜像 `src/arl/` 结构，放 `tests/`
- 所有实验必须可重放（seed + 场景配置）

## 提交规范

- 一个 commit 聚焦一个模块或一个阶段任务
- 不提交密钥、`.env`、`datasets/raw/` 大文件
- PR 描述中注明对应 ROADMAP 任务编号

## 研究复现

每次实验应附带：

- `configs/scenarios/` 中的场景 YAML
- `seed` 值
- 输出 trajectory 符合 `schemas/trajectory-v1.schema.json`

## License

Apache 2.0（Phase 4 正式开源）

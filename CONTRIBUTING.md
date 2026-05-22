# 贡献指南

感谢你为 `SDT Batch Exporter` 做出贡献。

## 开发环境

```bash
uv venv --python 3.12
uv sync --dev
uv run pytest
uv run ruff check .
uv run mypy src tests
```

## 数据要求

- 不要提交真实 `.sdt` 文件；
- 不要提交 `.zarr`、CSV/TXT、PNG、EXE 或 ZIP 导出结果；
- 仅允许把小型测试 fixture 放入 `tests/fixtures/`。

## 提交 PR

- 为 reader、exporter、workflow、GUI helper 的改动补充测试；
- 说明改动目的、影响范围和验证方式；
- 保持中文文档与公开发布内容一致。

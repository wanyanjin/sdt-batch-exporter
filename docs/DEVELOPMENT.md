# 开发说明

## 1. 开发环境

本项目使用 Python 3.12，并优先使用 `uv` 管理虚拟环境、依赖和锁文件。

## 2. Python 版本

- 要求版本：`>=3.12,<3.13`
- 不要在本项目中混用 Python 3.11 或更低版本

## 3. uv 虚拟环境

```bash
uv venv --python 3.12
uv sync --dev
```

默认使用项目内 `.venv/`，不得提交 `.venv/` 到 Git。

## 4. 安装依赖

当前阶段依赖：

- `numpy`
- `pytest`
- `ruff`
- `mypy`

Phase 01A 允许引入 `numpy`，因为纯后端 `intensity` 计算和 synthetic tests 需要它。

本阶段仍不引入 `sdtfile`、`zarr`、`numcodecs`、`PySide6` 等其他正式运行依赖。  
Phase 01B 已引入 `sdtfile`，用于 `storage/` 的只读 `.sdt` 读取和 preview data 构建。  
Phase 01C 已引入 `zarr` 和 `numcodecs`，用于单 dataset Zarr 导出和 readback。

## 5. 常用命令

```bash
uv run pytest
uv run ruff check .
uv run mypy src tests
uv run python -m sdt_batch_exporter --help
uv run sdt-export --help
uv run sdt-export-gui --help
SDT_EXPORTER_TEST_DATA_DIR=test-data uv run pytest -m realdata
```

## 6. 代码分层

```text
src/sdt_batch_exporter/
├── core/
├── storage/
├── workflows/
├── models/
├── gui/
└── utils/
```

- `core/` 只负责纯计算；
- `storage/` 负责外部格式适配；
- `workflows/` 负责串联流程；
- `gui/` 负责界面与交互；
- `utils/` 负责通用工具。

## 7. 新增依赖规则

- 新增依赖前必须说明用途和层级；
- `core/` 不得为了方便而引入 GUI 或 I/O 依赖；
- 只有当对应实现真正开始时，才引入 `zarr`、`PySide6` 等其余依赖；
- 依赖声明以 [pyproject.toml](../pyproject.toml) 为准。

## 8. 根目录零污染

- 根目录只保留稳定入口文件、配置文件和一层目录；
- 临时脚本、临时 CSV/TXT/JSON、导出结果、调试日志不得散落在根目录；
- 临时输出必须进入受控目录，例如 `tmp/`、`runs/`、`exports/` 或 `tests/fixtures/`。

## 9. 公开发布说明

- `scripts/prepare_public_release.py` 负责生成 `public-release/sdt-batch-exporter/`；
- `scripts/build_windows.py` 负责 Windows zip 构建；
- `packaging/gui_entry.py` 负责 PyInstaller GUI 入口；
- 公开目录不应包含内部记忆文件、真实数据或导出结果。

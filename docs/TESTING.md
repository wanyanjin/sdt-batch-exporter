# 测试说明

## 1. 目标

本项目测试分为三类：

- 纯单元测试；
- 真实数据可选测试；
- 发布和打包脚本测试。

## 2. 目录结构

```text
tests/
├── __init__.py
├── test_import_package.py
└── fixtures/
    └── README.md
```

## 3. 核心测试文件

- `tests/test_import_package.py`
- `tests/test_axis_resolver.py`
- `tests/test_intensity.py`
- `tests/test_metadata_extractor.py`
- `tests/test_sdt_reader_unit.py`
- `tests/test_sdt_reader_realdata.py`
- `tests/test_zarr_writer.py`
- `tests/test_zarr_writer_realdata.py`
- `tests/test_zarr_benchmark.py`
- `tests/test_zarr_benchmark_realdata.py`
- `tests/test_text_exporter.py`
- `tests/test_text_exporter_realdata.py`
- `tests/test_export_workflow.py`
- `tests/test_export_workflow_realdata.py`
- `tests/test_cli.py`
- `tests/test_cli_realdata.py`
- `tests/test_gui_request_builder.py`
- `tests/test_gui_imports.py`

## 4. 覆盖范围

Phase 01A 覆盖：

- `axis_resolver`
- `intensity`
- `metadata_extractor.to_jsonable`

后续阶段分别覆盖：

- `storage/`
- `workflows/`
- CLI
- GUI

## 5. fixture 规则

- 优先使用 synthetic numpy arrays；
- `.sdt` 真实数据不能进入 Git；
- fixture 必须放在 `tests/fixtures/`；
- 测试应使用 `tmp_path` 或 `tmp_path_factory`；
- realdata 测试必须由环境变量显式启用。

## 6. realdata 命令

```bash
SDT_EXPORTER_TEST_DATA_DIR=test-data uv run pytest -m realdata
```

说明：

- `test-data/` 仅用于本地验证，不进入 Git；
- realdata benchmark 必须写入临时目录；
- realdata CSV/TXT、workflow、CLI 测试都必须使用临时目录。

## 7. GUI 测试

- GUI request builder 需要覆盖；
- GUI import smoke test 需要覆盖；
- 预览渲染、比例尺和预览图导出都需要对应测试。

## 8. 发布脚本测试

- `tests/test_public_release_script.py` 会检查公开发布生成器只复制白名单文件；
- 安全扫描必须在发现敏感路径或同步路径标记时失败；
- Windows 打包 workflow 在本地 Linux CI 中不会真正执行，只检查定义和辅助脚本。

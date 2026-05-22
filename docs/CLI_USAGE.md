# CLI 使用说明

## 1. 定位

CLI 是后端 workflow 的命令行入口，用于批量导出 `.sdt` 到 Zarr / CSV / TXT。
它只负责参数解析和流程编排，不直接实现 `.sdt` 读取或格式写入逻辑。

## 2. 基本命令

```bash
uv run python -m sdt_batch_exporter input.sdt -o exports --zarr
```

```bash
uv run sdt-export input.sdt -o exports --zarr
```

## 3. 输入文件和目录

- `input` 可以是单个 `.sdt` 文件或目录；
- 目录默认扫描当前层的 `*.sdt`；
- `--recursive` 可以递归扫描子目录。

## 4. 输出目录

- `-o/--output` 必填；
- CLI 不提供默认输出目录，必须显式指定。

## 5. Zarr 导出

- 默认启用 Zarr（`--zarr`）；
- 可用 `--no-zarr` 关闭 Zarr；
- 关闭 Zarr 时，至少要启用 `--csv` 或 `--txt` 之一。

## 6. CSV/TXT 导出

- `--csv` 启用 CSV intensity 导出；
- `--txt` 启用 TXT intensity 导出；
- CSV/TXT 是交换格式，大规模后续分析优先使用 Zarr。

## 7. dataset selection

- `--dataset first|all|indices`，默认 `first`；
- `--dataset indices` 时必须配合 `--indices 0,2,3`。

## 8. compression / chunk 参数

- `--compression fast|balanced|max`，默认 `balanced`；
- `--chunk auto|legacy_auto|zarr_auto|spatial_32|spatial_64|spatial_128|whole_if_possible`，默认 `auto`。

## 9. overwrite

- `--overwrite` 启用覆盖已有输出；
- 默认不覆盖已有输出。

## 10. summary-json

- `--summary-json path` 可输出 batch 结果 JSON 摘要。

## 11. exit code

- `0`：全部成功；
- `1`：workflow 执行完成但存在失败或 skipped；
- `2`：参数错误或输入路径错误。

## 12. 注意事项

- 输出目录必须显式指定；
- 默认导出 Zarr；
- `test-data/` 是本地 realdata 目录，不进入 Git；
- 不要把 `.sdt`、`.zarr`、CSV/TXT 导出结果提交到仓库。

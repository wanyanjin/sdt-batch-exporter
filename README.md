# SDT Batch Exporter

`SDT Batch Exporter` 是一个用于 Becker & Hickl `.sdt` 文件批量
预览和导出的桌面工具，支持 GUI 和命令行两种使用方式。

## 主要功能

- 打开单个或多个 `.sdt` 文件；
- 预览积分 PL 强度图；
- 查看 metadata、axis 推断结果和强度统计；
- 导出完整 x-y-t 光子计数数据为 Zarr；
- 导出积分二维强度矩阵为 CSV/TXT；
- 导出带 colormap、color bar 和 scale bar 的 PNG 预览图；
- 同时提供 GUI 和 CLI。

## Windows 可执行程序

Windows 用户可在 GitHub Releases 下载最新 zip，解压后运行：

```text
SDT-Batch-Exporter.exe
```

## 从源码运行

要求：

- Python 3.12
- uv

```bash
uv venv --python 3.12
uv sync --dev
uv run sdt-export-gui
```

命令行示例：

```bash
uv run sdt-export input.sdt -o exports --zarr --csv
```

## 输出格式

| 输出 | 用途 | 是否适合定量分析 |
| --- | --- | --- |
| Zarr | 保存完整 x-y-t 数据，供后续分析 | 是 |
| CSV/TXT | 保存沿 time axis 积分后的二维强度矩阵 | 是 |
| PNG | 保存当前显示风格的预览图 | 否 |

## 当前限制

- 目前不做寿命拟合；
- PNG 只是显示渲染图，不是定量矩阵；
- time axis 推断采用保守策略，无法可靠推断时会跳过 intensity 导出；
- 仓库中不包含真实实验 `.sdt` 数据。

## 许可证

MIT License

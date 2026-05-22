# SDT Batch Exporter 用户指南

## 1. 简介

`SDT Batch Exporter` 是一个面向 Becker & Hickl `.sdt` 文件的批量预览与导出工具，主要输出为光子计数数据、积分强度矩阵和预览图。

## 2. 工作流

```text
导入 `.sdt` 文件
→ 预览 intensity
→ 查看 metadata
→ 导出 Zarr
→ 导出 CSV/TXT
→ 导出 PNG
```

## 3. 支持的输入

- 单个 `.sdt`
- 多个 `.sdt`
- 目录批量导入

## 4. 预览

导入后可以查看：

- 积分 PL 强度图
- metadata
- axis 推断结果
- intensity stats

## 5. metadata

metadata 会尽量保留 `.sdt` 文件中的信息。

- 读取失败的字段会记录为 warning；
- 不会因为单个 metadata 字段失败而阻止整体导出；
- 额外会保存 `str(sdt)` 作为兜底摘要。

## 6. Zarr

Zarr 用于保存完整光子计数数据和 metadata。

- `raw_counts`
- dataset attrs
- `metadata/`

如果可用，还会保存：

- `time`
- `intensity`

## 7. CSV/TXT intensity

CSV/TXT 保存沿 time axis 积分后的二维强度矩阵，适合：

- Origin
- Excel
- MATLAB
- ImageJ

注意：

- CSV/TXT 不是主存储格式；
- 只有当 time axis 可可靠推断时才会导出；
- 若 `intensity is None`，不会生成 CSV/TXT intensity。

## 8. 输出目录结构

```text
exports/
└── sample_001/
    ├── sample_001.zarr
    ├── sample_001_dataset000_intensity.csv
    ├── sample_001_dataset000_intensity.txt
    └── sample_001_export_meta.json
```

## 9. 导出原则

- Zarr 是主数据格式；
- PNG 是显示预览图，不是定量结果；
- CSV/TXT 只保存积分结果；
- 无法可靠判断 time axis 时，跳过 intensity CSV/TXT。

## 10. workflow

workflow 负责串联 `storage` 与 `core`：

- `.sdt -> load dataset -> PreviewData -> Zarr/CSV/TXT`
- 负责单文件、多文件和 batch 的顺序编排

## 11. CLI

```bash
uv run python -m sdt_batch_exporter test-data -o exports --zarr
```

```bash
uv run sdt-export test-data -o exports --zarr --compression balanced --chunk auto
```

## 12. GUI

```bash
uv run sdt-export-gui
```

GUI 主要用于：

- 导入 `.sdt`
- 查看预览
- 选择导出格式
- 启动后台导出

## 13. Phase 03C 导出语义

- `Full TRPL cube (.zarr)`：完整 x-y-t photon-count 数据；
- `Integrated intensity (.csv)`：沿 time axis 求和后的二维强度矩阵；
- `Integrated intensity (.txt)`：tab 分隔的强度矩阵。

## 14. Phase 03D-1 高级预览

- Colormap
- Display mode
- Percentile
- Scale bar
- Color bar

这些设置只影响显示，不改变 Zarr / CSV / TXT 的定量数据。

## 15. Phase 03D-2 预览 PNG

- PNG 只是预览输出；
- PNG 会生成 sidecar JSON；
- PNG 不替代 Zarr / CSV / TXT。

## 16. Phase 03D-2A 故障提示

- 若部分文件成功、部分失败，先检查输出目录是否位于同步文件夹；
- 建议使用本地非同步目录；
- GUI 日志会显示更详细的失败摘要。

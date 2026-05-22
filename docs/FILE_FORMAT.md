# SDT Batch Exporter Zarr 文件格式说明

## 1. 格式目标

- 为 `.sdt` 数据提供可追溯、可压缩、可批处理的主存储格式；
- 保留完整 photon counts、time axis 和 metadata；
- 为后续 Python 分析提供稳定 schema；
- 为 GUI 预览和批量导出提供一致的中间结果。

## 2. schema_version

- 初始 schema version：`0.1.0`
- 所有 Zarr root attrs 必须包含 `schema_version`
- 任何破坏性变更都必须升级 schema version，并同步更新文档和测试。

## 3. 推荐目录结构

```text
sample_001.zarr/
├── metadata/
│   ├── attrs["sdt_summary"]
│   ├── attrs["header"]
│   ├── attrs["info"]
│   ├── attrs["setup"]
│   ├── attrs["measure_info"]
│   ├── attrs["block_headers"]
│   └── attrs["export_options"]
├── dataset_000/
│   ├── raw_counts
│   ├── time
│   ├── intensity
│   └── attrs
└── dataset_001/
    ├── raw_counts
    ├── time
    ├── intensity
    └── attrs
```

## 4. root attrs

root attrs 至少包含：

```json
{
  "schema_version": "0.1.0",
  "source_file": "sample_001.sdt",
  "source_path": "D:/data/sample_001.sdt",
  "export_time": "2026-05-20T12:00:00+08:00",
  "software_version": "0.1.0",
  "dataset_count": 2,
  "exporter": "SDT Batch Exporter",
  "compression_profile": "balanced",
  "chunk_strategy": "auto"
}
```

## 5. metadata group

- `metadata/` 是一个 Zarr group；
- 第一版优先通过 group attrs 保存 JSON-compatible metadata；
- 无法结构化保存的对象可以转为字符串，但必须保留 warning；
- metadata 保存失败不能导致 `raw_counts` 导出失败。

## 6. dataset group

每个 `dataset_xxx/` 至少包含：

- `raw_counts`
- dataset attrs

如果 time axis 明确，则应生成：

- `intensity`

如果 time axis 可提取，则应保存：

- `time`

如果 time axis 不明确：

- 不得生成正式 `intensity`
- 不得自动导出 intensity CSV/TXT
- 必须记录 `skipped_intensity_export = true`
- 必须记录 `skip_reason`
- 必须记录 `axis_inference_status`

二维源数据如果本身就是强度图，可以保存为 `intensity`，但 attrs 必须说明来源。

## 7. raw_counts

- `raw_counts` 必须尽量保留 `sdtfile` 读取后的原始 shape 和 dtype；
- 不得默认转为 `float64`；
- 不得默认做归一化、平滑、背景扣除、裁剪、插值或重采样。

## 8. time

- 若 `sdt.times[i]` 存在且可用，应保存到 `dataset_xxx/time`；
- `time` 长度应与所判定的 time axis 一致；
- attrs 中应记录 `time_axis_index`、`time_axis_length`、`time_axis_source`、`time_unit`。

## 9. intensity

- `intensity` 是对 `raw_counts` 沿明确 time axis 求和的结果；
- 公式为：

```text
intensity = raw_counts.sum(axis=time_axis_index)
```

- 若 time axis 不明确，不得构造正式 `intensity`。

## 10. metadata 序列化

`to_jsonable()` 至少应处理：

- `dict`
- `list` / `tuple`
- `numpy.ndarray`
- `bytes`
- 自定义对象
- 不可序列化对象

原则：

- 保留 `str(sdt)` 或等价摘要；
- 保存失败的字段应记录 warning；
- 不因单个字段失败而导致整个 Zarr 导出失败。

## 11. chunk 和 compression

当前提供三档压缩预设：

- `fast`：`lz4`, `clevel=1`
- `balanced`：`zstd`, `clevel=5`
- `max`：`zstd`, `clevel=9`

默认建议使用 `balanced + auto`，并在 root attrs 中记录 `compression_profile` 和 `chunk_strategy`。

## 12. 向后兼容

- 已发布 schema 中的既有字段不得随意删除；
- 新字段优先追加，不破坏旧字段语义；
- 破坏性调整必须升级 `schema_version`，并同步更新 `docs/PRD.md`、`docs/FILE_FORMAT.md` 和相关测试。

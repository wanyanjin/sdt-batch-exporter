# GUI 使用说明

## 1. GUI 定位

GUI 通过 workflow 调用后端导入与导出逻辑，用于预览 `.sdt` 的积分强度图和 metadata。
它负责交互和展示，不直接承担核心数据处理。

GUI 可以查看：

- 单个 `.sdt` 文件的预览图；
- metadata；
- Zarr / CSV / TXT 导出选项；
- 运行状态和失败信息。

## 2. 启动方式

```bash
uv run sdt-export-gui
```

## 3. 主界面

- `Add Files`：添加单个 `.sdt` 文件；
- `Add Folder`：批量添加目录中的 `.sdt` 文件；
- `Clear List`：清空当前列表；
- `Output Dir`：选择输出目录；
- 文件表格显示 `Name / Path / Status`。

## 4. 操作流程

- 点击 `Add Files` 选择一个或多个 `.sdt` 文件；
- 点击 `Add Folder` 导入一个目录下的 `.sdt` 文件；
- 选择一个条目后，右侧显示该文件的预览、metadata 和导出信息。

## 5. 预览

- 预览通过后台 worker 计算，避免阻塞 GUI；
- 预览图使用 percentile contrast；
- 右侧会显示 axis、intensity stats 和 metadata；
- 状态栏会显示 `previewed` 或 `failed`。

## 6. 导出

- 可选择 `Zarr`；
- 可选择 `CSV` / `TXT`；
- 可选择预览图导出；
- 导出会通过 worker 调用 workflow。

## 7. dataset selection

- `first`：只处理第一个 dataset；
- `all`：处理所有 dataset；
- `indices`：只处理指定索引，例如 `0,2,3`。

## 8. compression / chunk / overwrite

- Compression：`fast` / `balanced` / `max`
- Chunk：`auto` / `legacy_auto` / `zarr_auto` / `spatial_32` / `spatial_64` / `spatial_128` / `whole_if_possible`
- Overwrite：覆盖已有输出

## 9. 导出状态

- `success`
- `failed`
- `skipped`

## 10. 常见问题

- 如果只有部分文件失败，先检查输出目录是否在 OneDrive 或其他同步文件夹中；
- 大批量导出建议使用本地非同步目录；
- GUI 日志会显示更详细的失败信息。

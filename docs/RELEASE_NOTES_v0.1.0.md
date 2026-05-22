# SDT Batch Exporter v0.1.0 发布说明

这是 `SDT Batch Exporter` 的首次公开版本。

## 主要功能

- 支持 Becker & Hickl `.sdt` 文件读取；
- 支持 GUI 中预览积分 PL 强度图；
- 支持查看 metadata、axis 推断结果和强度统计信息；
- 支持导出完整 x-y-t 数据为 Zarr；
- 支持导出积分强度矩阵为 CSV/TXT；
- 支持导出带 colormap、color bar 和 scale bar 的 PNG 预览图；
- 支持命令行批量导出；
- 提供 Windows 可执行程序构建流程。

## 输出说明

- Zarr：推荐用于后续程序分析；
- CSV/TXT：推荐用于 Origin、Excel、MATLAB 等软件绘图；
- PNG：仅用于展示和记录，不作为定量矩阵。

## 当前限制

- 暂不支持寿命拟合；
- 暂不包含真实 `.sdt` 示例数据；
- time axis 无法可靠推断时会跳过 intensity 导出；
- Windows EXE 仍建议在目标电脑上实际测试后再大范围分发。

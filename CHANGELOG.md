# 更新日志

## v0.2.0

第二次公开发布，覆盖当前阶段已经稳定下来的批量预览、导出和发布链路。

### 新增

- 增强 GUI 预览体验，包含文件列表、metadata 侧栏、色条、比例尺与 PNG 导出；
- 强化批量导出流程与导出前预检查，减少单文件失败对整批任务的影响；
- 完善 Zarr 导出链路，保留原始 counts、time axis 推断结果和 staged write 安全提交；
- 稳定 Windows 打包与公开发布流程，支持通过 tag 自动触发 Release 资产生成；
- 补充 OneDrive / 文件锁场景的错误诊断与恢复策略。

## v0.1.0

首次公开发布。

### 新增

- 支持 Becker & Hickl `.sdt` 文件预览；
- 支持 metadata 和 axis 信息查看；
- 支持完整 x-y-t Zarr 导出；
- 支持积分强度 CSV/TXT 导出；
- 支持 GUI 和 CLI 入口；
- 支持带 colormap、color bar、scale bar 的 PNG 预览图导出；
- 支持 Windows 可执行程序构建流程。

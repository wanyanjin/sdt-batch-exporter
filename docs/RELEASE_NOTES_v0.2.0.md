# SDT Batch Exporter v0.2.0 发布说明

本次发布把 `v0.1.0` 之后完成的稳定更新整理为新的公开版本。重点仍然是保证原始 photon counts、time axis 与 metadata 的完整性，同时把预览、导出和发布流程做得更稳。

## 主要更新

- 完善 GUI 预览体验：文件列表、metadata 侧栏、色条、比例尺与 PNG 预览导出更完整。
- 增强批量导出链路：导出前预检查、单文件失败隔离与错误反馈更稳健。
- 强化 Zarr 导出：继续保留原始 counts，并写入 time axis 推断结果、metadata 与 staged write 信息。
- 稳定 Windows 打包与公开发布：开源仓库通过 tag 触发 `build-windows.yml` 自动构建 Release 资产。
- 改进 OneDrive / 文件锁场景的恢复与诊断，减少半写入和锁定失败带来的数据损坏风险。

## 输出说明

- Zarr 仍然是主数据格式。
- CSV/TXT 仍然只作为明确 time axis 条件下的强度矩阵交换格式。
- 如果 time axis 无法可靠判断，仍会跳过 intensity 导出。

## 兼容性说明

- 软件版本号升级到 `0.2.0`。
- Zarr schema 标识升级到 `0.2.0`。
- 旧的 `v0.1.0` 发布说明仍保留，便于追溯历史版本。

# Test Fixtures

本目录用于保存小型、可公开、可版本管理的测试夹具。

规则：

- 禁止提交真实实验 `.sdt` 原始数据，除非用户明确确认其可公开且体积极小。
- 大型 `.sdt`、`.zarr`、导出 CSV/TXT 不得放入 Git。
- 后续优先使用 synthetic numpy arrays 测试 `core/` 逻辑。
- 若必须加入二进制 fixture，必须说明来源、用途、大小和隐私状态。

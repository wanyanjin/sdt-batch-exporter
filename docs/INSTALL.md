# 安装与运行

## 方式一：Windows 可执行程序

从 GitHub Releases 下载最新 Windows zip，解压后运行：

```text
SDT-Batch-Exporter.exe
```

## 方式二：从源码运行

要求：

- Python 3.12
- uv

```bash
uv venv --python 3.12
uv sync --dev
uv run sdt-export-gui
```

命令行帮助：

```bash
uv run sdt-export --help
```

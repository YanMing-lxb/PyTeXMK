# AGENTS.md

本仓库的代码修改约定集中在 [`docs/code-modification-playbook.md`](docs/code-modification-playbook.md)。

## 开始前

1. 先读 `docs/code-modification-playbook.md`、`docs/python315-migration.md`、`docs/architecture.md`。
2. 先跑基线：`ruff check --config pyproject.toml src tests` 与相关 `pytest`；不要凭记忆判断。
3. 确认本次只做哪一类：行为修复 / Python 3.15 迁移 / pathlib 现代化 / 纯风格清理。

## 硬约束

- **不要混轮**：行为修复不要夹带语法或风格清理；纯风格轮次不要改变行为。
- **保留契约**：`file_ops._replace` 的临时文件 + `Path.replace` + 失败回滚；native biber 的
  `--input-directory` 必须指向 `auxdir`；`--version` 不经过惰性导入开关。
- **不要为清单造使用点**：`Path.info` 已因缓存语义否决，`uuid.uuid7` 当前无场景。
- **PEP 758** 只用于不带 `as` 的处理器；`except A, B as e` 仍非法。
- **不修改系统环境变量或 MiKTeX 本体，不联网，不提交**，除非用户明确要求。

## 验证

```powershell
ruff check --config pyproject.toml src tests
python -m compileall -q src\pytexmk
python -m pytest -q tests
python -m pytexmk.cli --version
```

当前环境若 `PATH` 缺 `xelatex`，先判断是否为测试环境缺 TeX，不要把环境失败写成代码回归。

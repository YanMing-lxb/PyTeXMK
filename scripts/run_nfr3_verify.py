"""NFR-3 命名空间 B 验证脚本：验证 pytexlogs 作为独立顶级库可导入/使用。"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PYTEXLOGS_SRC = PROJECT_ROOT / "src" / "pytexmk" / "pytexlogs"


def build_runner_content(td: Path) -> str:
    project_src = str(PROJECT_ROOT / "src")
    return f'''
import sys
_project_src = r"{project_src}"
_pytexmk_src = _project_src + r"\\pytexmk"
# 只保留标准库+td，过滤掉 pytexmk 项目 src 路径（确保无 pytexmk 依赖泄漏）
td_path = r"{td}"
filtered = []
for p in sys.path:
    p_norm = p.replace("/", "\\\\")
    if _project_src in p_norm or _pytexmk_src in p_norm:
        continue
    filtered.append(p)
sys.path = [td_path] + filtered

try:
    import pytexlogs
except Exception as e:
    import traceback
    print(f"FAIL-IMPORT: {{type(e).__name__}}: {{e}}")
    traceback.print_exc()
    sys.exit(1)

REQUIRED_SYMBOLS = [
    "LatexLogParser", "BibtexParser", "BiberParser", "AsymptoteParser",
    "MintedParser", "PythontexParser", "GlossariesParser", "MakeindexParser",
    "NomenclParser", "XindyParser", "LogParserManager", "LogLevel", "LogEntry",
    "ParsedLog", "ParsedPipelineReport", "RefChangeTracker", "BaseLogParser",
    "print_summary", "format_editor_jumps", "log_editor_jumps", "show_log_entries",
    "run_log_pipeline", "LATEX_LOG_HINTS", "BIBTEX_ERROR_HINTS", "BIBER_WARNING_HINTS",
]

# PASS-1: 验证 __all__ 包含全部符号
all_set = set(getattr(pytexlogs, "__all__", []))
missing = [s for s in REQUIRED_SYMBOLS if s not in all_set]
if missing:
    print(f"FAIL-1: Missing in __all__: {{missing}}")
    sys.exit(1)
# 同时确保符号实际可访问
for s in REQUIRED_SYMBOLS:
    try:
        getattr(pytexlogs, s)
    except AttributeError as e:
        print(f"FAIL-1: Cannot access pytexlogs.{{s}}: {{e}}")
        sys.exit(1)
print("PASS-1: __all__ 符号检查通过")

# PASS-2: LatexLogParser 解析单行错误
try:
    parser = pytexlogs.LatexLogParser(quiet=True)
except TypeError:
    parser = pytexlogs.LatexLogParser()
try:
    parsed = parser.parse_lines([r"C:\\tex\\main.tex:12: Undefined control sequence \\foo"])
except AttributeError:
    parsed = parser.parse(r"C:\\tex\\main.tex:12: Undefined control sequence \\foo")

if not getattr(parsed, "entries", None):
    print("FAIL-2: parsed.entries 为空")
    sys.exit(1)
first = parsed.entries[0]
if first.level != pytexlogs.LogLevel.ERROR:
    print(f"FAIL-2: 首条 level 应为 ERROR, 实际 {{first.level}}")
    sys.exit(1)
if first.line != 12:
    print(f"FAIL-2: 首条 line 应为 12, 实际 {{first.line}}")
    sys.exit(1)
print("PASS-2: LatexLogParser 解析验证通过")

# PASS-3: format_editor_jumps 返回值前缀匹配
jumps = pytexlogs.format_editor_jumps(parsed.entries)
if not jumps:
    print("FAIL-3: format_editor_jumps 返回空列表")
    sys.exit(1)
first_jump = jumps[0]
if not first_jump.startswith("main.tex:12:"):
    print(f"FAIL-3: 首项前缀应为 'main.tex:12:', 实际 '{{first_jump[:50]}}'")
    sys.exit(1)
print("PASS-3: format_editor_jumps 验证通过")

# PASS-4: run_log_pipeline 不抛异常
try:
    result = pytexlogs.run_log_pipeline(
        tex_engine='pdflatex',
        tex_output='',
        bibtex_output='',
        biber_output='',
        other_engine_outputs={{}},
        quiet=True,
        ref_tracker_translate_fn=None,
        pytexmk_version='99.0-test',
    )
except TypeError:
    # 尝试兼容签名：使用 jobname/auxdir 作为必需参数
    import tempfile as _tf
    _td2 = Path(_tf.mkdtemp(prefix='pytexlogs_pipe_'))
    try:
        result = pytexlogs.run_log_pipeline(
            jobname='testjob',
            auxdir=str(_td2),
            captured_outputs={{'pdflatex': '', 'bibtex': '', 'biber': ''}},
            steps=['pdflatex'],
            print_terminal=False,
            write_report=False,
            ref_tracker_translate_fn=None,
            pytexmk_version='99.0-test',
        )
    finally:
        import shutil as _sh
        _sh.rmtree(_td2, ignore_errors=True)
except Exception as e:
    print(f"FAIL-4: run_log_pipeline 抛异常: {{type(e).__name__}}: {{e}}")
    sys.exit(1)
print("PASS-4: run_log_pipeline 不抛异常")

print("G6_PASS_NAMESPACE_B: pytexlogs standalone OK")
sys.exit(0)
'''


def main() -> int:
    td = Path(tempfile.mkdtemp(prefix='pytexlogs_lib_test_'))
    print(f"临时目录 td = {td}")
    try:
        # 步骤 2: 复制 pytexlogs -> td/pytexlogs
        dst = td / "pytexlogs"
        shutil.copytree(PYTEXLOGS_SRC, dst)
        print(f"已复制 {PYTEXLOGS_SRC} -> {dst}")

        # 步骤 3: 写 runner.py
        runner = td / "runner.py"
        runner.write_text(build_runner_content(td), encoding="utf-8")
        print(f"已写入 runner.py -> {runner}")

        # 步骤 4: uv run python td/runner.py
        cmd = ["uv", "run", "python", str(runner)]
        print(f"运行: {' '.join(cmd)}")
        proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True)
        print("----- stdout -----")
        print(proc.stdout)
        if proc.stderr:
            print("----- stderr -----")
            print(proc.stderr)
        print(f"----- exit_code = {proc.returncode} -----")
        return proc.returncode
    finally:
        # 步骤 5: 清理
        shutil.rmtree(td, ignore_errors=True)
        print(f"已清理临时目录: {td}")


if __name__ == "__main__":
    sys.exit(main())

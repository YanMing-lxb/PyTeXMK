"""SyncTeX 双向定位校验（3.11）。

`.synctex.gz` 存在不等于编辑器能跳转：native 构建（`-output-directory`）会改变
记录在 `.synctex.gz` 里的路径。本模块直接调用 `synctex view` / `synctex edit`：

* 正向：源文件第 N 行 → PDF 页码/坐标（编辑器“跳到 PDF”）
* 反向：PDF 坐标 → 源文件行号（编辑器“跳到源码”）

两者都通过才算 SyncTeX 可用。只依赖 TeX 发行版自带的 `synctex`，不引入第三方库。
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

_PAGE_RE = re.compile(r"Page:\s*(\d+)")
_X_RE = re.compile(r"x:\s*([0-9.]+)")
_Y_RE = re.compile(r"y:\s*([0-9.]+)")
_INPUT_RE = re.compile(r"Input:\s*(.*)")
_LINE_RE = re.compile(r"Line:\s*(\d+)")


@dataclass
class SyncTeXReport:
    """一次双向校验的结果。"""

    ok: bool = False
    forward_page: int | None = None
    forward_x: float | None = None
    forward_y: float | None = None
    reverse_file: str | None = None
    reverse_line: int | None = None
    errors: list[str] = field(default_factory=list)
    raw_tail: list[str] = field(default_factory=list)

    def summary(self) -> str:
        if not self.ok:
            return "SyncTeX 校验失败: " + "；".join(self.errors)
        return (
            f"SyncTeX 正常：正向 第 {self.forward_page} 页 "
            f"({self.forward_x:.1f}, {self.forward_y:.1f})，"
            f"反向 {Path(self.reverse_file or '').name}:{self.reverse_line}"
        )


def _run(command: list[str], cwd: Path) -> tuple[int, str]:
    try:
        proc = subprocess.run(  # noqa: S603 - 固定命令，参数由本模块拼装
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, str(exc)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def check(
    pdf_path: str | Path,
    tex_path: str | Path,
    *,
    line: int | None = None,
    page: int = 1,
    root: str | Path = ".",
) -> SyncTeXReport:
    """跑一次正向 + 反向校验；``line`` 缺省取源文件中第一个非空正文行。"""
    pdf = Path(pdf_path).resolve()
    tex = Path(tex_path).resolve()
    report = SyncTeXReport()

    if not pdf.exists():
        report.errors.append(f"PDF 不存在: {pdf}")
        return report
    if not tex.exists():
        report.errors.append(f"源文件不存在: {tex}")
        return report
    binary = shutil.which("synctex")
    if not binary:
        report.errors.append("未找到 synctex 命令（MiKTeX/TeX Live 通常自带）")
        return report

    if line is None:
        line = 1
        for index, text in enumerate(tex.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
            stripped = text.strip()
            if stripped and not stripped.startswith("%") and "\\documentclass" not in stripped:
                line = index
                break

    # 正向：必须用绝对路径，否则 synctex 会报 "No tag for xxx"
    code, output = _run(
        [binary, "view", "-i", f"{line}:1:{tex}", "-o", str(pdf)],
        Path(root),
    )
    report.raw_tail = [ln for ln in output.splitlines() if ln.strip()][-8:]
    page_match = _PAGE_RE.search(output)
    x_match = _X_RE.search(output)
    y_match = _Y_RE.search(output)
    if code != 0 or not page_match:
        report.errors.append("正向搜索失败：synctex view 没有返回 Page")
    else:
        report.forward_page = int(page_match.group(1))
        report.forward_x = float(x_match.group(1)) if x_match else None
        report.forward_y = float(y_match.group(1)) if y_match else None

    # 反向：page:x:y:pdf
    x = report.forward_x if report.forward_x is not None else 100.0
    y = report.forward_y if report.forward_y is not None else 100.0
    code, output = _run(
        [binary, "edit", "-o", f"{report.forward_page or page}:{x}:{y}:{pdf}"],
        Path(root),
    )
    input_match = _INPUT_RE.search(output)
    line_match = _LINE_RE.search(output)
    if code != 0 or not input_match or not line_match:
        report.errors.append("反向搜索失败：synctex edit 没有返回 Input/Line")
    else:
        report.reverse_file = input_match.group(1).strip()
        report.reverse_line = int(line_match.group(1))
        try:
            same_file = Path(report.reverse_file).resolve() == tex
        except OSError:
            same_file = Path(report.reverse_file).name == tex.name
        if not same_file:
            report.errors.append(
                f"反向搜索定位到错误文件: {report.reverse_file}（期望 {tex}）"
            )
        # 行号允许小偏差：SyncTeX 按版面盒子反查，段落/标题的相邻行本来就可能
        # 落在不同 box 上，编辑器只要求“跳到附近”。偏差过大才视为异常。
        if abs(report.reverse_line - line) > 20:
            report.errors.append(
                f"反向搜索行号偏差过大: 期望 {line}，实际 {report.reverse_line}"
            )

    report.ok = not report.errors
    return report

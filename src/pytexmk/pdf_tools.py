"""PDF 预览与修复（原地修复的安全版本）。

C6 修复要点
-----------
旧实现直接 ``open(pdf, "wb")`` 后写回同一路径：中途异常会**立刻毁掉原文件**
（截断成半个 PDF），而且没有任何回滚手段。这里改为：

1. 先写到同目录的临时文件 ``<name>.pytexmk-tmp.pdf``；
2. 写完 ``fsync`` 后 ``os.replace`` 原子替换；
3. 任何异常都删除临时文件，原文件保持原样；
4. 不产生 ``.bak`` 之类的额外残留（用户明确要求“不留任何文件残留”）；
5. 修复对象限定为**项目里真实被引用的 PDF**（``.fls`` 的 INPUT 记录），
   避免把仓库里无关的 PDF 全部重写一遍。
"""

import logging
import os
import shlex
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path

from rich import print

from pytexmk.language import set_language

_ = set_language("pdf_tools")

#: 修复时使用的临时文件后缀（结束时必须消失）
TMP_SUFFIX = ".pytexmk-tmp.pdf"


class PdfFileOperation:
    def __init__(self, viewer="default"):
        self.logger = logging.getLogger(__name__)
        self.viewer = viewer

    def set_viewer(self, new_viewer: str) -> None:
        """设置 PDF 查看器；``default`` 表示交给系统默认程序。"""
        self.viewer = new_viewer

    def _preview_pdf_by_viewer(self, local_path: str) -> None:
        """用系统默认程序或用户配置的查看器打开 PDF。

        自定义查看器支持 ``%f`` 占位符；Windows 上优先 ``os.startfile``，
        而不是给浏览器传 ``file://``（浏览器会把它当成一个“下载”）。
        """
        viewer = (self.viewer or "default").strip()
        if viewer in ("default", "auto", ""):
            self.logger.info(_("未设置 PDF 查看器,使用默认 PDF 查看器"))
            if sys.platform == "win32" and Path(local_path).exists():
                os.startfile(local_path)  # type: ignore[attr-defined]  # noqa: S606
            else:
                webbrowser.open(Path(local_path).as_uri())
            return

        tokens = shlex.split(viewer, posix=False)
        tokens = [t.replace("%f", local_path) for t in tokens]
        if not any("%f" in t for t in shlex.split(viewer, posix=False)):
            tokens.append(local_path)
        self.logger.info(_("设置 PDF 查看器: ") + f"{viewer}")
        try:
            subprocess.Popen(tokens, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError as exc:
            self.logger.warning(_("自定义查看器启动失败，回退系统默认程序: ") + str(exc))
            webbrowser.open(Path(local_path).as_uri())

    def pdf_preview(self, project_name: str, outdir: str) -> None:
        """打开输出目录中的 ``<project>.pdf``。"""
        pdf_name = f"{project_name}.pdf"
        pdf_path = Path(outdir) / pdf_name
        if not pdf_path.exists():
            self.logger.error(_("PDF 不存在: ") + str(pdf_path))
            return
        self.logger.info(_("文件路径: ") + str(pdf_path.resolve()))
        try:
            self._preview_pdf_by_viewer(str(pdf_path.resolve()))
        except Exception as e:  # noqa: BLE001
            self.logger.error(_("打开文件失败: ") + f"{pdf_name} -->{e}")

    # ------------------------------------------------------------------ 修复

    @staticmethod
    def _referenced_pdfs(root: Path, fls_path: Path | None) -> set[Path] | None:
        """从 ``.fls`` 的 INPUT 行取真实被引用的 PDF 集合；没有 .fls 返回 None。"""
        if fls_path is None or not fls_path.exists():
            return None
        pdfs: set[Path] = set()
        try:
            for line in fls_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                if not line.startswith("INPUT "):
                    continue
                raw = line[len("INPUT "):].strip().replace("\\", "/")
                candidate = Path(raw)
                if candidate.suffix.lower() == ".pdf" and candidate.is_file():
                    pdfs.add(candidate.resolve())
        except OSError:
            return None
        return pdfs

    def _repair_one(self, pdf_file: Path) -> None:
        """把一个 PDF 重写为干净副本；失败时原文件不被触碰。"""
        tmp = pdf_file.with_name(pdf_file.stem + TMP_SUFFIX)
        try:
            if shutil.which("qpdf"):
                # qpdf 能保留书签/元数据，且不会像 pypdf 那样丢表单
                subprocess.run(  # noqa: S603
                    ["qpdf", "--qdf", "--object-streams=generate", str(pdf_file), str(tmp)],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                )
            else:
                from pypdf import PdfReader, PdfWriter

                reader = PdfReader(str(pdf_file))
                writer = PdfWriter()
                for page in reader.pages:
                    writer.add_page(page)
                if reader.metadata:
                    writer.add_metadata(dict(reader.metadata))
                with tmp.open("wb") as fh:
                    writer.write(fh)
                    fh.flush()
                    os.fsync(fh.fileno())
            if not tmp.exists() or tmp.stat().st_size == 0:
                raise OSError("修复产物为空")
            os.replace(tmp, pdf_file)  # 原子替换，原文件要么完整要么不变
            self.logger.info(_("修复成功: ") + str(pdf_file))
        except Exception as e:  # noqa: BLE001
            self.logger.error(_("修复失败（原文件未改动）: ") + f"{pdf_file} --> {e}")
        finally:
            # 无论成功失败，临时文件都不能留下
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass

    def pdf_repair(self, project_name: str, root_dir: str, excluded_folder: str) -> None:
        """修复项目引用的 PDF（默认排除主 PDF 与输出目录）。"""
        root = Path(root_dir)
        excluded = Path(excluded_folder)
        referenced = self._referenced_pdfs(root, root / f"{project_name}.fls")

        candidates: list[Path]
        if referenced is not None:
            candidates = [
                p for p in referenced
                if p.exists() and p.name != f"{project_name}.pdf" and excluded not in p.parents
            ]
        else:
            candidates = [
                path
                for path in root.rglob("*.pdf")
                if ".git" not in path.parts
                and ".github" not in path.parts
                and path.is_file()
                and path.name != f"{project_name}.pdf"
                and path.parent.name != excluded.name
            ]

        if not candidates:
            print(_("当前路径下没有被引用的 PDF 文件"))
            return

        print(_("找到 PDF 文件数目: ") + f"[bold cyan]{len(candidates)}[/bold cyan]")
        for pdf_file in sorted(candidates):
            self._repair_one(pdf_file)
        print(_("[bold green]修复 PDF 结束[/bold green]"))

"""PDF 预览与修复（原地修复的安全版本）。

C6 修复要点
-----------
旧实现直接 ``open(pdf, "wb")`` 后写回同一路径：中途异常会**立刻毁掉原文件**
（截断成半个 PDF），而且没有任何回滚手段。这里改为：

1. 先写到同目录的临时文件 ``<name>.pytexmk-tmp.pdf``；
2. 写完 ``fsync`` 后 ``Path.replace`` 原子替换；
3. 任何异常都删除临时文件，原文件保持原样；
4. 不产生 ``.bak`` 之类的额外残留（用户明确要求“不留任何文件残留”）；
5. 修复对象限定为**项目里真实被引用的 PDF**（``.fls`` 的 INPUT 记录），
   避免把仓库里无关的 PDF 全部重写一遍。
"""

import contextlib
import hashlib
import logging
import os
import shlex
import shutil
import subprocess
import sys
import webbrowser
from dataclasses import dataclass
from pathlib import Path

from rich import print

from pytexmk.fls import iter_fls_inputs
from pytexmk.language import set_language

_ = set_language("pdf_tools")

#: 修复时使用的临时文件后缀（结束时必须消失）
TMP_SUFFIX = ".pytexmk-tmp.pdf"


@dataclass
class PdfStatus:
    """一次 PDF 产物的可用性检查结果。

    ``reason`` 取值：``ok`` / ``missing`` / ``empty`` / ``not-pdf`` / ``no-pages`` /
    ``corrupt`` / ``unreadable``。调用方据此给出稳定状态，而不是只看“文件存在”。
    """

    ok: bool
    reason: str
    pages: int | None = None
    size: int = 0
    digest: str = ""


def inspect_pdf(path: str | Path) -> PdfStatus:
    """检查 PDF 是否是可交付产物：存在、非空、有 ``%PDF`` 头、可解析且有页面。

    旧实现只查“文件存在”，旧 PDF、被覆盖成文本的文件、零页文档都能冒充本轮
    成功产物。这里用内容 + 页数做硬校验；pypdf 不可用时退化为头部检查。
    """
    pdf = Path(path)
    try:
        size = pdf.stat().st_size
    except OSError:
        return PdfStatus(False, "missing")
    if size <= 0:
        return PdfStatus(False, "empty", size=0)
    try:
        with pdf.open("rb") as handle:
            head = handle.read(5)
            handle.seek(0)
            digest = hashlib.file_digest(handle, "sha256").hexdigest()
    except OSError:
        return PdfStatus(False, "unreadable", size=size)
    if not head.startswith(b"%PDF"):
        return PdfStatus(False, "not-pdf", size=size, digest=digest)

    try:
        from pypdf import PdfReader
    except ImportError:
        # 没有解析库时只能退化为头部检查：不把 PDF 判死，但也不宣称页数。
        return PdfStatus(True, "ok", pages=None, size=size, digest=digest)
    try:
        pages = len(PdfReader(str(pdf)).pages)
    except Exception:  # noqa: BLE001 - 解析库的任何异常都等价于“文件已损坏”
        return PdfStatus(False, "corrupt", size=size, digest=digest)
    if pages <= 0:
        return PdfStatus(False, "no-pages", pages=0, size=size, digest=digest)
    return PdfStatus(True, "ok", pages=pages, size=size, digest=digest)


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
                os.startfile(local_path)  # type: ignore[attr-defined]
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
        except Exception as e:
            self.logger.error(_("打开文件失败: ") + f"{pdf_name} -->{e}")

    # ------------------------------------------------------------------ 修复

    @staticmethod
    def _referenced_pdfs(root: Path, fls_path: Path | None) -> set[Path] | None:
        """从 ``.fls`` 的 INPUT 行取真实被引用的 PDF 集合；没有 .fls 返回 None。"""
        if fls_path is None or not fls_path.exists():
            return None
        pdfs: set[Path] = set()
        root_resolved = root.resolve()
        for raw in iter_fls_inputs(fls_path):
            candidate = Path(raw.replace("\\", "/"))
            if candidate.suffix.lower() != ".pdf" or not candidate.is_file():
                continue
            resolved = candidate.resolve()
            # .fls 可能记录项目外的共享图片；修复会原地覆盖，必须限制在项目根内。
            try:
                resolved.relative_to(root_resolved)
            except ValueError:
                continue
            pdfs.add(resolved)
        return pdfs

    def _repair_one(self, pdf_file: Path) -> bool:
        """把一个 PDF 重写为干净副本；失败时原文件不被触碰。"""
        tmp = pdf_file.with_name(pdf_file.stem + TMP_SUFFIX)
        try:
            if shutil.which("qpdf"):
                # qpdf 能保留书签/元数据，且不会像 pypdf 那样丢表单
                subprocess.run(
                    ["qpdf", "--qdf", "--object-streams=generate", str(pdf_file), str(tmp)],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                )
            else:
                from pypdf import PdfWriter

                # 旧实现逐页 add_page + add_metadata：PDF 的书签/大纲全部丢失。
                # PdfWriter.append 默认 import_outline=True，保留文档结构。
                writer = PdfWriter()
                writer.append(str(pdf_file), import_outline=True)
                if not writer.pages:
                    raise OSError("修复后没有页面")
                with tmp.open("wb") as fh:
                    writer.write(fh)
                    fh.flush()
                    os.fsync(fh.fileno())
            if not tmp.exists() or tmp.stat().st_size == 0:
                raise OSError("修复产物为空")
            tmp.replace(pdf_file)  # 原子替换，原文件要么完整要么不变
            self.logger.info(_("修复成功: ") + str(pdf_file))
            return True
        except Exception as e:
            self.logger.error(_("修复失败（原文件未改动）: ") + f"{pdf_file} --> {e}")
            return False
        finally:
            # 无论成功失败，临时文件都不能留下
            with contextlib.suppress(OSError):
                tmp.unlink(missing_ok=True)

    def pdf_repair(
        self,
        project_name: str,
        root_dir: str,
        excluded_folder: str,
        auxdir: str | None = None,
        targets: list[str] | None = None,
    ) -> bool:
        """修复项目**真实引用**的 PDF，至少一项且全部成功时返回 True。

        旧实现从根目录找 ``.fls``，原生构建的 recorder 在 ``Auxiliary/``，查找
        失败后回退成“全树所有 PDF”——连 ``Build/nested/old.pdf`` 这种输出目录里
        的旧产物也会被重写。现在：
          * recorder 优先取 ``auxdir``，其次根目录；
          * 所有候选按 ``resolve()`` 后的路径判断归属，整个输出目录树一律排除；
          * 没有可信 recorder 时**只列出候选**，不写入任何文件；
          * ``targets`` 允许显式指定文件（``pytexmk -rp a.pdf``）。
        """
        root = Path(root_dir).resolve()
        out_tree = self._under_root(root, excluded_folder)
        main_pdf_name = f"{project_name}.pdf"

        if targets:
            candidates = []
            for raw in targets:
                candidate = (root / raw).resolve()
                if not candidate.is_file() or candidate.suffix.lower() != ".pdf":
                    self.logger.warning(_("跳过非 PDF 或不存在: ") + str(raw))
                    continue
                if not self._inside(candidate, root):
                    self.logger.warning(_("跳过项目外的文件: ") + str(raw))
                    continue
                if candidate.name == main_pdf_name:
                    self.logger.warning(_("跳过主输出 PDF: ") + str(raw))
                    continue
                candidates.append(candidate)
        else:
            fls_path = self._find_recorder(project_name, root, auxdir)
            referenced = self._referenced_pdfs(root, fls_path)
            if referenced is None:
                listing = self._fallback_candidates(root, out_tree, main_pdf_name)
                print(_("未找到可信的 .fls recorder，未执行任何修复。"))
                if listing:
                    print(_("以下 PDF 是潜在候选（只读列出，可用 -rp 显式指定要修复的文件）:"))
                    for path in listing[:20]:
                        print("  [dim]" + str(path) + "[/dim]")
                return False
            candidates = [
                p for p in referenced
                if p.exists()
                and p.name != main_pdf_name
                and not self._inside(p, out_tree)
            ]

        if not candidates:
            print(_("当前路径下没有被引用的 PDF 文件"))
            return False

        print(_("找到 PDF 文件数目: ") + f"[bold cyan]{len(candidates)}[/bold cyan]")
        results = [self._repair_one(pdf_file) for pdf_file in sorted(set(candidates))]
        if all(results) and (not targets or len(candidates) == len(targets)):
            print(_("[bold green]修复 PDF 结束[/bold green]"))
            return True
        return False

    @staticmethod
    def _inside(path: Path, directory: Path) -> bool:
        """``path`` 是否位于 ``directory`` 之内（含目录本身）。"""
        try:
            path.relative_to(directory)
        except ValueError:
            return False
        return True

    def _under_root(self, root: Path, value: str | Path) -> Path:
        """把相对输出目录解析成 root 下的绝对路径（``.`` 表示根目录本身）。"""
        path = Path(value)
        return (path if path.is_absolute() else root / path).resolve()

    def _find_recorder(self, project_name: str, root: Path, auxdir: str | None) -> Path | None:
        """按 native → 根目录的顺序找 ``<jobname>.fls``。"""
        candidates: list[Path] = []
        if auxdir:
            candidates.append(self._under_root(root, auxdir) / f"{project_name}.fls")
        candidates.append(root / f"{project_name}.fls")
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None

    def _fallback_candidates(self, root: Path, out_tree: Path, main_pdf_name: str) -> list[Path]:
        """没有 recorder 时的只读候选清单（不写入）。"""
        result: list[Path] = []
        for path in root.rglob("*.pdf"):
            if not path.is_file() or path.name == main_pdf_name:
                continue
            resolved = path.resolve()
            if not self._inside(resolved, root) or self._inside(resolved, out_tree):
                continue
            if any(part in {".git", ".github"} for part in path.parts):
                continue
            result.append(path)
        return result

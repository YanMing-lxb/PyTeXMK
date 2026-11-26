import logging
import os
import re
import tempfile
import time
from collections.abc import Iterable, Iterator
from pathlib import Path

from pytexmk.language import set_language
from pytexmk.layout import CLEAN_EXCLUDED_DIRS

_ = set_language("file_ops")


def atomic_write_text(path: str | Path, text: str, *, encoding: str = "utf-8") -> None:
    """原子写入文本：同目录临时文件 + fsync + ``Path.replace``。

    配置、草稿标记这类用户文件不能直接 ``write_text``：进程在写入中途被
    终止时，原文件会被截断成半份。这里先写同目录临时文件，成功后再原子
    替换；失败时只留下可删除的临时文件，原文件保持原样。
    """
    target = Path(path)
    tmp = target.with_name(f".{target.name}.tmp-{os.getpid()}-{time.time_ns()}")
    try:
        with tmp.open("w", encoding=encoding, newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        if target.exists():
            try:
                tmp.chmod(target.stat().st_mode)
            except OSError:
                pass
        tmp.replace(target)
    finally:
        tmp.unlink(missing_ok=True)


def iter_matched_files(
    folder: str | Path,
    patterns: Iterable[str | re.Pattern[str]],
    excluded_dirs: frozenset[str] = CLEAN_EXCLUDED_DIRS,
) -> Iterator[Path]:
    """遍历 ``folder`` 下文件名命中任一模式的普通文件。

    干跑与真实删除共用这一份遍历/排除规则；``patterns`` 允许是字符串或
    已编译的 ``re.Pattern``，统一在这里编译一次。
    """
    compiled = [p if isinstance(p, re.Pattern) else re.compile(p) for p in patterns]
    if not compiled:
        return
    for filepath in Path(folder).rglob("*"):
        if any(part in excluded_dirs for part in filepath.parts):
            continue
        if not filepath.is_file():
            continue
        if any(pattern.match(filepath.name) for pattern in compiled):
            yield filepath


class FileMoveRemoveManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def remove_specific_files(self, files: list, folder: str):
        for file in files:
            filepath = Path(folder) / file
            if filepath.exists():
                try:
                    filepath.unlink()
                    self.logger.info(_("删除成功: ") + str(filepath))
                except OSError as e:
                    self.logger.error(_("删除失败: ") + f"{filepath} --> {e}")

    #: `-ca/-Ca` 递归清理时必须跳过的目录（源码/示例/虚拟环境不是辅助产物）
    CLEAN_EXCLUDED_DIRS = CLEAN_EXCLUDED_DIRS

    def remove_matched_files(self, patterns: list[re.Pattern], folder: str):
        """递归删除根目录下命中任一正则的辅助产物。

        0.5 是"每个 pattern 各做一次全树 rglob"（29 个后缀 → 29 次目录遍历），
        这里改为只遍历一次目录，再用模式集合逐文件匹配。
        返回 ``(已删除, 失败项)``，供调用方向 JSON 如实报告结果。
        """
        return self.remove_paths(iter_matched_files(folder, patterns, self.CLEAN_EXCLUDED_DIRS))

    def remove_paths(self, paths: Iterable[str | Path]) -> tuple[list[Path], list[tuple[Path, str]]]:
        """按给定清单删除文件，返回 ``(已删除, [(失败路径, 原因)])``。

        预览与执行必须共用同一份清单（由调用方算好后同时用于两者）：
        旧实现预览与实际删除各自遍历，结果范围可能不一致。
        """
        removed: list[Path] = []
        failed: list[tuple[Path, str]] = []
        for raw in paths:
            filepath = Path(raw)
            try:
                filepath.unlink()
            except FileNotFoundError:
                continue
            except OSError as exc:
                self.logger.error(_("删除失败: ") + f"{filepath} --> {exc}")
                failed.append((filepath, str(exc)))
                continue
            self.logger.info(_("删除成功: ") + str(filepath))
            removed.append(filepath)
        return removed, failed

    def move_specific_files(
        self,
        files: list | None = None,
        src_folder: str | None = None,
        dest_folder: str | None = None,
    ) -> int:
        """按文件名精确搬移：把 src_folder 下的 files 列表中的文件搬到 dest_folder。"""
        moved_count = 0

        src_folder_path = Path(src_folder) if src_folder else Path()
        dest_folder_path = Path(dest_folder) if dest_folder else Path()

        if not src_folder_path.exists():
            # 源目录不存在 ≠ "没有可搬的文件"：静默 mkdir 目标目录只会掩盖上游错误
            # （例如 auxdir 配错），这里记一条 debug 后返回 0。
            self.logger.debug(_("源目录不存在，跳过搬移: ") + str(src_folder_path))
            return 0
        if not dest_folder_path.exists():
            dest_folder_path.mkdir(parents=True, exist_ok=True)

        for file in files or []:
            src_file_path = src_folder_path / file
            dest_file_path = dest_folder_path / file
            if self._replace(src_file_path, dest_file_path, dest_folder):
                moved_count += 1

        return moved_count

    def _replace(self, src: Path, dest: Path, dest_label: str | None) -> bool:
        """把 src 搬到 dest：先搬到目标目录的临时名，再原子替换，返回是否真搬动。

        0.5 是"先 unlink(dest) 再 move"：move 若失败（跨盘/占用/权限），
        目标文件已经没了、源文件也没搬过去，PDF 直接消失。现在先完整搬到
        同目录临时文件，再用 ``Path.replace`` 原子覆盖，失败时把临时文件回滚回
        源路径，任何时刻目标位置都不会出现"空窗"。
        """
        if not src.exists():
            return False
        # src 与 dest 指向同一个文件（outdir 与 auxdir 配置成同一目录、或非原生构建
        # 时 outdir 就是项目根目录）时，**绝不能**先 unlink(dest) 再 move：那会把刚
        # 编译出来的 PDF / SyncTeX 直接删掉，而且只留一条日志。
        try:
            if dest.exists() and src.resolve() == dest.resolve():
                self.logger.debug(_("源与目标为同一文件，跳过搬移: ") + str(src))
                return False
        except OSError:
            pass

        tmp = None
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            fd, name = tempfile.mkstemp(prefix=f".{dest.name}.pytexmk-", suffix=".tmp", dir=dest.parent)
            tmp = Path(name)
            os.close(fd)
            # Path.move 在同盘使用替换，跨盘退化为复制并删除源文件。
            self._move_with_retry(src, tmp)
        except OSError as e:
            if tmp is not None and src.exists():
                try:
                    tmp.unlink(missing_ok=True)
                except OSError:
                    self.logger.warning("临时文件未能清理: %s", tmp)
            self.logger.error(_("移动失败: ") + f"{src} ==> {dest_label} --> {e}")
            return False

        try:
            tmp.replace(dest)
        except OSError as e:
            # 原子替换失败：把临时文件搬回源位置，宁可"没搬"也不能"两边都没有"
            try:
                self._move_with_retry(tmp, src)
            except OSError:
                self.logger.error(_("回滚失败，请手动检查: ") + f"{tmp}")
            self.logger.error(_("移动失败: ") + f"{src} ==> {dest_label} --> {e}")
            return False

        self.logger.info(_("移动成功: ") + f"{src.name} ==> {dest_label}")
        return True

    @staticmethod
    def _move_with_retry(src: Path, dest: Path, attempts: int = 3) -> None:
        """搬移文件，遇到 Windows 文件占用/同步锁时短暂重试。"""
        last_error: OSError | None = None
        for attempt in range(attempts):
            try:
                src.move(dest)
                return
            except OSError as exc:
                last_error = exc
                if attempt < attempts - 1:
                    time.sleep(0.2 * (attempt + 1))
        if last_error is not None:
            raise last_error

    def move_matched_files(self, patterns: list[re.Pattern], src_folder: str, dest_folder: str) -> int:
        """把 src_folder 下文件名命中任一正则的文件搬到 dest_folder，返回搬移个数。

        patterns 既可以是已编译的 re.Pattern（state.aux_regex_files 上游已编译过），
        也可以是字符串；re.compile() 对前者原样返回，因此无需再判断类型。

        源目录不存在时返回 0 而不是抛 FileNotFoundError：首次编译（尚未产生
        Auxiliary/）或用户手工删掉辅助目录时，这里原本会把一条 WinError 3 抛到
        `time_count`，整条流程以退出码 1 崩掉。
        """
        src_folder_path = Path(src_folder)
        dest_folder_path = Path(dest_folder)
        dest_folder_path.mkdir(parents=True, exist_ok=True)
        if not src_folder_path.is_dir():
            self.logger.debug("源目录不存在，跳过搬移: %s", src_folder_path)
            return 0

        compiled_patterns = [re.compile(pattern) for pattern in patterns]
        moved_count = 0
        for file_path in src_folder_path.iterdir():
            if not file_path.is_file():
                continue
            for pattern in compiled_patterns:
                if pattern.match(file_path.name):
                    if self._replace(file_path, dest_folder_path / file_path.name, dest_folder):
                        moved_count += 1
                    break
        return moved_count

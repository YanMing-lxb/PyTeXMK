import logging
import re
from pathlib import Path

from pytexmk.language import set_language

_ = set_language("file_ops")


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

    def remove_matched_files(self, patterns: list[re.Pattern], folder: str):
        for pattern in patterns:
            compiled_pattern = re.compile(pattern)
            for filepath in Path(folder).rglob("*"):
                if ".git" in filepath.parts or ".github" in filepath.parts:
                    continue
                if filepath.is_file() and compiled_pattern.match(filepath.name):
                    try:
                        filepath.unlink()
                        self.logger.info(_("删除成功: ") + str(filepath))
                    except OSError as e:
                        self.logger.error(_("删除失败: ") + f"{filepath} --> {e}")

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

        if not src_folder_path.exists() or not dest_folder_path.exists():
            dest_folder_path.mkdir(parents=True, exist_ok=True)

        for file in files or []:
            src_file_path = src_folder_path / file
            dest_file_path = dest_folder_path / file
            if self._replace(src_file_path, dest_file_path, dest_folder):
                moved_count += 1

        return moved_count

    def _replace(self, src: Path, dest: Path, dest_label: str | None) -> bool:
        """把 src 搬到 dest：覆盖同名旧文件后 rename，返回是否真的搬动了。

        四个搬移方法原本各写一遍「存在则删旧 → rename → 记日志」，出错分支还各有
        细微差别；集中到一处后行为一致，改错也只改一次。
        """
        if not src.exists():
            return False
        if dest.exists():
            try:
                dest.unlink()
            except OSError as e:
                self.logger.error(_("删除失败: ") + f"{dest} --> {e}")
                return False
        try:
            src.rename(dest)
        except OSError as e:
            self.logger.error(_("移动失败: ") + f"{src} ==> {dest_label} --> {e}")
            return False
        self.logger.info(_("移动成功: ") + f"{src.name} ==> {dest_label}")
        return True

    def move_by_extensions(
        self,
        extensions_to_move: list[str],
        root_path: str | None = None,
        aux_dir: str | None = None,
    ) -> int:
        """按后缀批量搬移：把 aux_dir 下匹配后缀的文件搬到项目根目录。"""
        moved_count = 0

        root = Path(root_path) if root_path else Path.cwd()
        aux = Path(aux_dir) if aux_dir else root / "aux"
        if not aux.exists():
            return 0
        dest = root
        dest.mkdir(parents=True, exist_ok=True)
        exts = [e if e.startswith(".") else f".{e}" for e in (extensions_to_move or [])]
        for fpath in aux.iterdir():
            if not fpath.is_file():
                continue
            if exts and fpath.suffix not in exts:
                continue
            if self._replace(fpath, dest / fpath.name, str(dest)):
                moved_count += 1
        return moved_count

    def move_matched_files(self, patterns: list[re.Pattern], src_folder: str, dest_folder: str) -> int:
        """把 src_folder 下文件名命中任一正则的文件搬到 dest_folder，返回搬移个数。

        patterns 既可以是已编译的 re.Pattern（state.aux_regex_files 上游已编译过），
        也可以是字符串；re.compile() 对前者原样返回，因此无需再判断类型。
        """
        dest_folder_path = Path(dest_folder)
        dest_folder_path.mkdir(parents=True, exist_ok=True)

        compiled_patterns = [re.compile(pattern) for pattern in patterns]
        moved_count = 0
        for file_path in Path(src_folder).iterdir():
            if not file_path.is_file():
                continue
            for pattern in compiled_patterns:
                if pattern.match(file_path.name):
                    if self._replace(file_path, dest_folder_path / file_path.name, dest_folder):
                        moved_count += 1
                    break
        return moved_count

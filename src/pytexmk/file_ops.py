import logging
import re
from pathlib import Path

from pytexmk.language import set_language

_ = set_language("file_ops")


class FileMoveRemoveManager:
    """架构 Task3：类名从 Move​Remove​Operation 升级为 FileMoveRemoveManager（语义更清晰，单一职责=文件移动+删除的 manager）。"""
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
        *,
        project_root: str | None = None,
        root_path: str | None = None,
        aux_dir: str | None = None,
        extensions_to_move: list[str] | None = None,
    ) -> int:
        moved_count = 0

        if extensions_to_move is not None:
            root = Path(root_path) if root_path else Path(project_root) if project_root else Path.cwd()
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
                dest_file_path = dest / fpath.name
                if dest_file_path.exists():
                    try:
                        dest_file_path.unlink()
                    except OSError as e:
                        self.logger.error(_("删除失败: ") + f"{dest_file_path} --> {e}")
                        continue
                try:
                    import shutil
                    shutil.move(str(fpath), str(dest_file_path))
                    moved_count += 1
                    self.logger.info(
                        _("移动成功: ") + f"{fpath} ==> {dest}"
                    )
                except OSError as e:
                    self.logger.error(
                        _("移动失败: ") + f"{fpath} ==> {dest} --> {e}"
                    )
            return moved_count

        src_folder_path = Path(src_folder) if src_folder else Path()
        dest_folder_path = Path(dest_folder) if dest_folder else Path()

        if not src_folder_path.exists() or not dest_folder_path.exists():
            dest_folder_path.mkdir(parents=True, exist_ok=True)

        for file in (files or []):
            src_file_path = src_folder_path / file
            dest_file_path = dest_folder_path / file

            if dest_file_path.exists():
                try:
                    dest_file_path.unlink()
                except OSError as e:
                    self.logger.error(_("删除失败: ") + f"{dest_file_path} --> {e}")
                    break

            if src_file_path.exists():
                try:
                    src_file_path.rename(dest_file_path)
                    moved_count += 1
                    self.logger.info(
                        _("移动成功: ") + f"{src_file_path} ==> {dest_folder}"
                    )
                except OSError as e:
                    self.logger.error(
                        _("移动失败: ") + f"{src_file_path} ==> {dest_folder} --> {e}"
                    )

        return moved_count

    def move_matched_files(
        self, patterns: list[re.Pattern], src_folder: str, dest_folder: str
    ):
        src_folder_path = Path(src_folder)
        dest_folder_path = Path(dest_folder)

        dest_folder_path.mkdir(parents=True, exist_ok=True)

        compiled_patterns = [re.compile(pattern) for pattern in patterns]

        for file_path in src_folder_path.iterdir():
            if file_path.is_file():
                for pattern in compiled_patterns:
                    if pattern.match(file_path.name):
                        dest_file_path = dest_folder_path / file_path.name

                        if dest_file_path.exists():
                            try:
                                dest_file_path.unlink()
                            except OSError as e:
                                self.logger.error(
                                    _("删除失败: ") + f"{dest_file_path} --> {e}"
                                )
                                break

                        try:
                            file_path.rename(dest_file_path)
                            self.logger.info(
                                _("移动成功: ") + f"{file_path.name} ==> {dest_folder}"
                            )
                        except OSError as e:
                            self.logger.error(
                                _("移动失败: ")
                                + f"{file_path.name} ==> {dest_folder} --> {e}"
                            )
                        break

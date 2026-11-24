import logging
import re
from collections import defaultdict
from pathlib import Path

from pytexmk.file_ops import atomic_write_text
from pytexmk.language import set_language
from pytexmk.lifecycle import EXIT_ERROR, exit_pytexmk
from pytexmk.subproject_scanner import has_magic
from pytexmk.ui_theme import console

_ = set_language("tex_project")

#: 匹配 ``\documentclass[opts]{class}``（跳过被注释掉的行首命令）。
#: 开/关草稿模式共用同一个模式与同一个替换函数，避免两处正则漂移。
_DOCUMENTCLASS_RE = re.compile(
    r"(?<!%)(?<!% )(?<!%  )\\documentclass(?:\[(?P<opts>[^\]]*)\])?\{(?P<class>[^\}]*)\}"
)


def standardize_name(compiled_program: str) -> str:
    """将小写/混合大小写编译程序名统一为规范标题形式。"""
    standard_names = {
        "xelatex": "XeLaTeX",
        "pdflatex": "PdfLaTeX",
        "lualatex": "LuaLaTeX",
    }
    return standard_names.get(compiled_program.lower(), compiled_program)


class MainFileOperation:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        #: 草稿模式改写过的文件（进程内）；restore_draft 只负责把这些文件里的
        #: draft 选项摘掉，不回写整份快照（快照会覆盖编译期间用户的其它编辑）
        self._draft_modified: set[str] = set()
        #: 跨进程草稿标记：只有 PyTeXMK 自己加过 draft 才写，下次编译据此自愈，
        #: 不会把作者本来就想要的 draft 选项误删。
        self._draft_marker: Path | None = None
        self._draft_atexit_registered = False

    def check_project_name(self, main_files: list, check_project_name: str, suffix: str) -> str:
        path_obj = Path(check_project_name)

        # 放开相对路径，但禁止绝对路径与".."越界
        if path_obj.is_absolute():
            self.logger.error(_("不支持绝对路径: ") + f"[bold cyan]{check_project_name}")
            exit_pytexmk(EXIT_ERROR)
        if ".." in path_obj.parts:
            self.logger.error(_("路径不能越过项目根目录: ") + f"[bold cyan]{check_project_name}")
            exit_pytexmk(EXIT_ERROR)

        base_name = path_obj.stem
        file_extension = path_obj.suffix

        if file_extension and file_extension != suffix:
            self.logger.error(
                _("文件类型非 %(args)s: ") % {"args": suffix} + f"[bold cyan]{check_project_name}{suffix}"
            )
            exit_pytexmk(EXIT_ERROR)

        if base_name in main_files:
            return str(path_obj.with_suffix(""))

        # 带子目录的相对路径：允许直接命中文件本身
        if path_obj.exists():
            return str(path_obj.with_suffix(""))

        self.logger.error(_("未找到主文件 %(args)s") % {"args": f"[bold cyan]{check_project_name}{suffix}[/bold cyan]"})
        exit_pytexmk(EXIT_ERROR)

    def get_suffix_files_in_dir(self, dir: str, suffix: str) -> list:
        suffix_files_in_dir = []
        current_path = Path(dir)
        try:
            for file in current_path.glob(f"*{suffix}"):
                base_name = file.stem
                suffix_files_in_dir.append(base_name)
                self.logger.info(_("搜索到: ") + f"{base_name}{suffix}")

            if suffix_files_in_dir:
                self.logger.info(f"{suffix}" + _("文件数目: ") + str(len(suffix_files_in_dir)))
            else:
                self.logger.error(_("文件不存在于当前路径下, 请检查终端显示路径是否是项目路径"))
                self.logger.warning(_("当前终端路径: ") + str(current_path))
                exit_pytexmk(EXIT_ERROR)
        except OSError as e:
            self.logger.error(_("文件搜索失败: ") + f"{suffix} --> {e}")
        return suffix_files_in_dir

    def find_tex_commands(self, tex_files_in_root: list, *, required: bool = True) -> list:
        """扫描根目录下的候选主文件。

        ``required=False`` 用于 ``-ca/-Ca``：清理辅助产物不应该依赖“能唯一确定
        主文件”，没有 ``\\documentclass`` 或存在多个主文件时返回空清单，
        由调用方按保守所有权规则处理，而不是直接退出。
        """
        main_tex_files = []
        for file_name in tex_files_in_root:
            try:
                if has_magic(Path(file_name).with_suffix(".tex")):
                    main_tex_files.append(file_name)
                    self.logger.info(_("通过特征命令检索到主文件: ") + str(file_name))
            except (OSError, UnicodeDecodeError) as e:
                self.logger.error(_("打开文件失败: ") + f"{file_name}.tex --> {e}")

        if main_tex_files:
            self.logger.info(_("发现主文件数量: ") + str(len(main_tex_files)))
        elif required:
            self.logger.error(_("终端路径下不存在主文件! 请检查终端显示路径是否是项目路径!"))
            self.logger.warning(_("当前终端路径: ") + str(Path.cwd()))
            exit_pytexmk(EXIT_ERROR)
        else:
            self.logger.info(_("未发现主文件；本次只按后缀清理辅助产物"))
        return main_tex_files

    def search_magic_comments(
        self, main_files_in_root: list[str], magic_comment_keys: list[str]
    ) -> dict[str, dict[str, str]]:
        file_magic_comments = defaultdict(dict)

        for file_path in main_files_in_root:
            try:
                file_path_obj = Path(file_path).with_suffix(".tex")
                with file_path_obj.open("r", encoding="utf-8") as file:
                    for line_number, line_content in enumerate(file, start=1):
                        if line_number > 50:
                            break
                        for magic_comment_key in magic_comment_keys:
                            pattern = (
                                rf"(?<!\\)%(?:\s*)!TEX {re.escape(magic_comment_key)}(?:\s*)=(?:\s*)(.*?)(?=\s|%|$)"
                            )
                            match_result = re.search(pattern, line_content, re.IGNORECASE)
                            if match_result:
                                matched_comment_value = match_result.group(1).strip()
                                file_magic_comments[file_path][magic_comment_key] = matched_comment_value
                                break
            except (OSError, UnicodeDecodeError) as e:
                self.logger.error(_("打开文件失败: ") + f"{file_path} --> {e}")
                continue

        all_magic_comments = defaultdict(dict)
        for file_path, comments in file_magic_comments.items():
            for key, value in comments.items():
                all_magic_comments[key][file_path] = value
        return dict(all_magic_comments)

    def get_main_file(
        self,
        default_file: str,
        args_document: str,
        main_files_in_root: list[str],
        all_magic_comments: dict[str, dict[str, str]],
    ) -> str:
        project_name = ""
        current_path = Path.cwd()

        if args_document:
            project_name = args_document
            project_name = self.check_project_name(main_files_in_root, project_name, ".tex")
            console.print(_("通过命令行命令指定待编译主文件为: ") + f"[bold cyan]{project_name}")
            return project_name

        if len(main_files_in_root) == 1:
            project_name = main_files_in_root[0]
            console.print(_("通过根目录下唯一主文件指定待编译主文件为: ") + f"[bold cyan]{project_name}.tex")
            return project_name

        if "root" in all_magic_comments:
            self.logger.info(_("魔法注释 % !TEX root 在当前根目录下主文件中有被定义"))
            if len(all_magic_comments["root"]) == 1:
                file_path, root_value = next(iter(all_magic_comments["root"].items()))
                self.logger.info(_("魔法注释 % !TEX root 只存在于: ") + f"{file_path}.tex")
                check_file = self.check_project_name(main_files_in_root, root_value, ".tex")
                if file_path == check_file:
                    project_name = check_file
                    console.print(_("通过魔法注释 % !TEX root 指定待编译主文件为: ") + f"[bold cyan]{project_name}.tex")
                    return project_name
                else:
                    self.logger.warning(
                        _("魔法注释 % !TEX root 指定的文件名与当前文件名不同, 无法确定主文件: ")
                        + f"[bold red]{check_file}.tex[/bold red], [bold green]{file_path}.tex[/bold green] "
                    )
            elif len(all_magic_comments["root"]) > 1:
                self.logger.warning(
                    _("魔法注释 % !TEX root 在当前根目录下的多个主文件中同时被定义, 无法根据魔法注释确定待编译主文件")
                )

        if not project_name:
            self.logger.info(_("无法根据魔法注释判断出待编译主文件, 尝试根据默认主文件名指定待编译主文件"))
            for file in main_files_in_root:
                if file == default_file:
                    project_name = file
                    console.print(
                        _('通过默认文件名 "%(args)s.tex" 指定待编译主文件为: ') % {"args": default_file}
                        + f"[bold cyan]{project_name}.tex"
                    )
                    return project_name
                else:
                    self.logger.info(_('当前根目录下不存在名为 "%(args)s.tex" 的文件') % {"args": default_file})

        if not project_name:
            self.logger.error(_("无法进行编译, 当前根目录下存在多个主文件: ") + ", ".join(main_files_in_root))
            self.logger.warning(
                _(
                    '请修改待编译主文件名为默认文件名 "%(args)s.tex" 或在文件中加入魔法注释 "%% !TEX root = [待编译主文件名]" 或在终端输入 "pytexmk [待编译主文件名]" 进行编译, 或删除当前根目录下多余的 tex 文件'
                )
                % {"args": default_file}
            )
            self.logger.warning(_("当前根目录是: ") + str(current_path))
            exit_pytexmk(EXIT_ERROR)

        return project_name

    def draft_model(
        self,
        project_name: str,
        enabled: bool,
        auxdir: str | Path = ".",
    ):
        """草稿模式开关：``enabled=True`` 临时加 draft，``False`` 只做崩溃自愈。

        草稿状态不靠调用方两次“开/关”配对维持，只由一个布尔量表达：
          * 开启时记录**被改写的文件**（不整份备份原文），在 ``auxdir`` 写
            ``.pytexmk-draft`` 标记，并注册 ``atexit`` 兜底；
          * 关闭由 ``restore_draft()`` 在当前内容上**精确摘除 draft 选项**
            （编译期间用户对文件的其它修改不会被旧快照覆盖）；
          * ``enabled=False`` 只消费上一次进程崩溃留下的标记：只恢复标记里
            记录的文件，不碰作者自己写的 draft；没有标记就什么都不做。

        旧实现用两个布尔量分工（``draft_run`` 管执行、``draft_judgement`` 管加不加），
        调用方漏传一半就会静默失效，``-dr`` 曾因此整条路径不生效。
        """
        marker = Path(auxdir) / ".pytexmk-draft"

        if not enabled:
            self._recover_from_marker(marker)
            return

        file_path = Path(f"{project_name}.tex")
        self._draft_marker = marker
        try:
            marker.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_text(marker, f"{file_path.resolve()}\n")
        except OSError as exc:
            self.logger.warning(_("写入草稿标记失败，崩溃后可能无法自动恢复: ") + str(exc))

        def _draft_substitution(match: re.Match[str]) -> str:
            options = self._documentclass_options(match["opts"] or "", True)
            opts = f"[{options}]" if options else ""
            return f"\\documentclass{opts}{{{match['class']}}}"

        try:
            with file_path.open("r", encoding="utf-8", newline="") as handle:
                content = handle.read()
            modified_content = _DOCUMENTCLASS_RE.sub(_draft_substitution, content)
            if modified_content == content:
                self.logger.info(_("未匹配到内容, 文件未修改."))
                return
            self._draft_modified.add(str(file_path))
            atomic_write_text(file_path, modified_content)
            self.logger.info(_("启用草稿模式"))
            file_size = file_path.stat().st_size / 1024**2
            self.logger.info(
                _("处理文件: %(args)s, 文件大小: %(size).3f MB") % {"args": file_path.name, "size": file_size}
            )
            if not self._draft_atexit_registered:
                import atexit

                atexit.register(self.restore_draft)
                self._draft_atexit_registered = True

        except FileNotFoundError:
            self.logger.error(_("文件未找到: ") + file_path.name)
        except PermissionError:
            self.logger.error(_("权限错误: 无法读取或写入文件: ") + file_path.name)
        except UnicodeError as exc:
            self.logger.error(
                _("草稿模式需要 UTF-8 源文件（请另存为 UTF-8）: ")
                + f"{file_path.name} --> {exc}"
            )
        except OSError as e:
            self.logger.error(_("更新草稿模式时出错: ") + str(e))
        except re.error as e:
            self.logger.error(_("草稿模式正则匹配出错: ") + str(e))

    def _strip_draft_file(self, file_path: Path) -> bool:
        """在单个文件上摘除 draft；返回 False 表示读/写失败、需要保留重试标记。"""
        if not file_path.exists():
            return True
        try:
            with file_path.open("r", encoding="utf-8", newline="") as handle:
                content = handle.read()
            cleaned = _DOCUMENTCLASS_RE.sub(self._undraft_substitution, content)
            if cleaned != content:
                atomic_write_text(file_path, cleaned)
                self.logger.info(_("关闭草稿模式"))
            return True
        except UnicodeError as exc:
            self.logger.error(
                _("关闭草稿模式失败：源文件不是有效 UTF-8（请另存为 UTF-8）: ")
                + f"{file_path} --> {exc}"
            )
        except OSError as exc:
            self.logger.error(_("关闭草稿模式失败: ") + str(exc))
        return False

    def _recover_from_marker(self, marker: Path) -> None:
        """消费上一次崩溃留下的草稿标记，只恢复标记里记录的文件。

        没有标记就什么都不做：作者自己写在 ``\\documentclass`` 里的 draft
        不能被“自愈”误删。标记在恢复成功/文件不存在时都会删除，避免反复处理。
        """
        if not marker.is_file():
            return
        try:
            name = marker.read_text(encoding="utf-8").strip()
        except (OSError, UnicodeError) as exc:
            self.logger.warning(_("读取草稿标记失败: ") + str(exc))
            return
        if not name:
            marker.unlink(missing_ok=True)
            return
        file_path = Path(name)
        if self._strip_draft_file(file_path):
            marker.unlink(missing_ok=True)

    def restore_draft(self) -> None:
        """在当前源文件内容上摘除 ``draft`` 选项（可重复调用）。

        只改 ``draft`` 一个 token，编译期间用户对文件的其它修改保持不变。
        """
        for name in list(self._draft_modified):
            path = Path(name)
            try:
                if not path.exists():
                    continue
                with path.open("r", encoding="utf-8", newline="") as handle:
                    content = handle.read()
                cleaned = _DOCUMENTCLASS_RE.sub(self._undraft_substitution, content)
                if cleaned != content:
                    atomic_write_text(path, cleaned)
                    self.logger.info(_("关闭草稿模式"))
            except UnicodeError as exc:
                self.logger.error(
                    _("恢复草稿模式失败：源文件不是有效 UTF-8（请手动检查 %(f)s）: %(e)s")
                    % {"f": name, "e": exc}
                )
            except OSError as exc:
                self.logger.error(_("恢复草稿模式失败（请手动检查 %(f)s）: %(e)s") % {"f": name, "e": exc})
            finally:
                self._draft_modified.discard(name)
        if self._draft_marker is not None:
            try:
                self._draft_marker.unlink(missing_ok=True)
            except OSError as exc:
                self.logger.warning(_("删除草稿标记失败: ") + str(exc))

    def _undraft_substitution(self, match: re.Match[str]) -> str:
        """把一个 ``\\documentclass`` 匹配去掉 draft 选项。"""
        options = self._documentclass_options(match["opts"] or "", False)
        opts = f"[{options}]" if options else ""
        return f"\\documentclass{opts}{{{match['class']}}}"

    @staticmethod
    def _documentclass_options(options: str, enable_draft: bool) -> str:
        """按逗号切分 \\documentclass 选项，增/删 draft 后保持其余选项的原有顺序。"""
        current = [opt.strip() for opt in options.split(",") if opt.strip()]
        if enable_draft:
            if "draft" not in current:
                current.append("draft")
        else:
            current = [opt for opt in current if opt != "draft"]
        return ",".join(current)

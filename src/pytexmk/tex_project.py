import logging
import re
from collections import defaultdict
from pathlib import Path

from pytexmk.language import set_language
from pytexmk.lifecycle import EXIT_ERROR, exit_pytexmk
from pytexmk.subproject_scanner import has_magic
from pytexmk.ui_theme import console

_ = set_language("tex_project")


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
        #: 草稿模式改写前的原文备份（进程内）；restore_draft 用它精确回滚
        self._draft_backups: dict[str, str] = {}
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
            return check_project_name.rstrip(suffix) if check_project_name.endswith(suffix) else check_project_name

        # 带子目录的相对路径：允许直接命中文件本身
        if path_obj.exists():
            return str(path_obj).rstrip(suffix) if str(path_obj).endswith(suffix) else str(path_obj)

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
        except re.error as e:
            self.logger.error(_("文件搜索正则错误: ") + f"{suffix} --> {e}")
        return suffix_files_in_dir

    def find_tex_commands(self, tex_files_in_root: list) -> list:
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
        else:
            self.logger.error(_("终端路径下不存在主文件! 请检查终端显示路径是否是项目路径!"))
            self.logger.warning(_("当前终端路径: ") + str(Path.cwd()))
            exit_pytexmk(EXIT_ERROR)
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

    def draft_model(self, project_name: str, draft_run: bool, draft_judgement: bool):
        """草稿模式开关：临时在 ``\\documentclass`` 上加/去 ``draft`` 选项。

        C3：旧实现只在编译成功路径上调用 ``draft_model(..., False)``，一旦编译
        失败（``exit_pytexmk``）或 Ctrl+C，用户仓库里的 ``main.tex`` 就永久带着
        ``draft``。现在：
          * 开启时先把**原文完整备份**在内存里；
          * 注册 ``atexit`` 兜底（连 ``sys.exit`` 路径也能恢复）；
          * 结束时由 ``restore_draft()`` 精确写回原文，而不是再做一次正则反向替换
            （反向替换会丢掉用户在这期间的其它编辑）。
        """
        if not draft_run:
            self.logger.info(_("草稿模式未启用, 跳过处理."))
            return

        if not draft_judgement:
            if self._draft_backups:
                self.restore_draft()
                return
            # 没有本次运行留下的备份（例如上次进程崩在“关闭”之前）：
            # 回退为反向替换，保证 -dr 之后的文件至少还能恢复成无 draft 状态。
            file_path = Path(f"{project_name}.tex")
            pattern = re.compile(r"(?<!%)(?<!% )(?<!%  )\\documentclass(?:\[(?P<opts>[^\]]*)\])?\{(?P<class>[^\}]*)\}")
            try:
                content = file_path.read_text(encoding="utf-8")
                cleaned = pattern.sub(
                    lambda m: (
                        f"\\documentclass[{self._documentclass_options(m['opts'] or '', False)}]{{{m['class']}}}"
                        if self._documentclass_options(m["opts"] or "", False)
                        else f"\\documentclass{{{m['class']}}}"
                    ),
                    content,
                )
                if cleaned != content:
                    file_path.write_text(cleaned, encoding="utf-8")
                    self.logger.info(_("关闭草稿模式"))
            except OSError as exc:
                self.logger.error(_("关闭草稿模式失败: ") + str(exc))
            return

        file_path = Path(f"{project_name}.tex")
        pattern = re.compile(r"(?<!%)(?<!% )(?<!%  )\\documentclass(?:\[(?P<opts>[^\]]*)\])?\{(?P<class>[^\}]*)\}")

        def _draft_substitution(match: re.Match[str]) -> str:
            options = self._documentclass_options(match["opts"] or "", True)
            opts = f"[{options}]" if options else ""
            return f"\\documentclass{opts}{{{match['class']}}}"

        try:
            content = file_path.read_text(encoding="utf-8")
            modified_content = pattern.sub(_draft_substitution, content)
            if modified_content == content:
                self.logger.info(_("未匹配到内容, 文件未修改."))
                return
            self._draft_backups[str(file_path)] = content
            file_path.write_text(modified_content, encoding="utf-8")
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
        except OSError as e:
            self.logger.error(_("更新草稿模式时出错: ") + str(e))
        except re.error as e:
            self.logger.error(_("草稿模式正则匹配出错: ") + str(e))

    def restore_draft(self) -> None:
        """把草稿模式改写的源文件恢复为原始内容（可重复调用）。"""
        for name, original in list(self._draft_backups.items()):
            path = Path(name)
            try:
                if path.exists() and path.read_text(encoding="utf-8") != original:
                    path.write_text(original, encoding="utf-8")
                    self.logger.info(_("关闭草稿模式"))
            except OSError as exc:
                self.logger.error(_("恢复草稿模式失败（请手动检查 %(f)s）: %(e)s") % {"f": name, "e": exc})
            finally:
                self._draft_backups.pop(name, None)

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

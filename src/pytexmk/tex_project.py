import logging
import re
from collections import defaultdict
from pathlib import Path

from rich import print

from pytexmk.language import set_language
from pytexmk.lifecycle import exit_pytexmk

_ = set_language("tex_project")


class MainFileOperation:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def check_project_name(
        self, main_files: list, check_project_name: str, suffix: str
    ) -> str:
        path_obj = Path(check_project_name)
        base_name = path_obj.stem
        file_extension = path_obj.suffix

        if path_obj.parent != Path(""):
            self.logger.error(_("文件名中不能存在路径"))
            exit_pytexmk()

        if file_extension == suffix and base_name in main_files:
            return base_name

        if not file_extension and base_name in main_files:
            return base_name

        self.logger.error(
            _("文件类型非 %(args)s: ") % {"args": suffix}
            + f"[bold cyan]{check_project_name}{suffix}"
        )
        exit_pytexmk()

    def get_suffix_files_in_dir(self, dir: str, suffix: str) -> list:
        suffix_files_in_dir = []
        current_path = Path(dir)
        try:
            for file in current_path.glob(f"*{suffix}"):
                base_name = file.stem
                suffix_files_in_dir.append(base_name)
                self.logger.info(_("搜索到: ") + f"{base_name}{suffix}")

            if suffix_files_in_dir:
                self.logger.info(
                    f"{suffix}" + _("文件数目: ") + str(len(suffix_files_in_dir))
                )
            else:
                self.logger.error(
                    _("文件不存在于当前路径下，请检查终端显示路径是否是项目路径")
                )
                self.logger.warning(_("当前终端路径: ") + str(current_path))
                exit_pytexmk()
        except Exception as e:  # noqa: BLE001
            self.logger.error(_("文件搜索失败: ") + f"{suffix} --> {e}")
        return suffix_files_in_dir

    def find_tex_commands(self, tex_files_in_root: list) -> list:
        main_tex_files = []
        for file_name in tex_files_in_root:
            try:
                with open(
                    Path(file_name).with_suffix(".tex"), "r", encoding="utf-8"
                ) as file:
                    is_main_file = False

                    for i in range(200):
                        line = file.readline()

                        if line.strip().startswith("%") or not line.strip():
                            continue

                        if r"\documentclass" in line or r"\begin{document}" in line:
                            is_main_file = True
                            break

                    if is_main_file:
                        main_tex_files.append(file_name)
                        self.logger.info(
                            _("通过特征命令检索到主文件: ") + str(file_name)
                        )
            except Exception as e:  # noqa: BLE001
                self.logger.error(_("打开文件失败: ") + f"{file_name}.tex --> {e}")

        if main_tex_files:
            self.logger.info(_("发现主文件数量: ") + str(len(main_tex_files)))
        else:
            self.logger.error(
                _("终端路径下不存在主文件!请检查终端显示路径是否是项目路径!")
            )
            self.logger.warning(_("当前终端路径: ") + str(Path.cwd()))
            exit_pytexmk()
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
                            pattern = rf"%(?:\s*)!TEX {re.escape(magic_comment_key)}(?:\s*)=(?:\s*)(.*?)(?=\s|%|$)"
                            match_result = re.search(
                                pattern, line_content, re.IGNORECASE
                            )
                            if match_result:
                                matched_comment_value = match_result.group(1).strip()
                                file_magic_comments[file_path][magic_comment_key] = (
                                    matched_comment_value
                                )
                                break
            except Exception as e:  # noqa: BLE001
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
            project_name = self.check_project_name(
                main_files_in_root, project_name, ".tex"
            )
            print(
                _("通过命令行命令指定待编译主文件为: ") + f"[bold cyan]{project_name}"
            )
            return project_name

        if len(main_files_in_root) == 1:
            project_name = main_files_in_root[0]
            print(
                _("通过根目录下唯一主文件指定待编译主文件为: ")
                + f"[bold cyan]{project_name}.tex"
            )
            return project_name

        if "root" in all_magic_comments:
            self.logger.info(_("魔法注释 % !TEX root 在当前根目录下主文件中有被定义"))
            if len(all_magic_comments["root"]) == 1:
                file_path, root_value = next(
                    iter(all_magic_comments["root"].items())
                )
                self.logger.info(
                    _("魔法注释 % !TEX root 只存在于: ") + f"{file_path}.tex"
                )
                check_file = self.check_project_name(
                    main_files_in_root, root_value, ".tex"
                )
                if file_path == check_file:
                    project_name = check_file
                    print(
                        _("通过魔法注释 % !TEX root 指定待编译主文件为: ")
                        + f"[bold cyan]{project_name}.tex"
                    )
                    return project_name
                else:
                    self.logger.warning(
                        _(
                            "魔法注释 % !TEX root 指定的文件名与当前文件名不同, 无法确定主文件: "
                        )
                        + f"[bold red]{check_file}.tex[/bold red], [bold green]{file_path}.tex[/bold green] "
                    )
            elif len(all_magic_comments["root"]) > 1:
                self.logger.warning(
                    _(
                        "魔法注释 % !TEX root 在当前根目录下的多个主文件中同时被定义, 无法根据魔法注释确定待编译主文件"
                    )
                )

        if not project_name:
            self.logger.info(
                _(
                    "无法根据魔法注释判断出待编译主文件, 尝试根据默认主文件名指定待编译主文件"
                )
            )
            for file in main_files_in_root:
                if file == default_file:
                    project_name = file
                    print(
                        _('通过默认文件名 "%(args)s.tex" 指定待编译主文件为: ')
                        % {"args": default_file}
                        + f"[bold cyan]{project_name}.tex"
                    )
                    return project_name
                else:
                    self.logger.info(
                        _('当前根目录下不存在名为 "%(args)s.tex" 的文件')
                        % {"args": default_file}
                    )

        if not project_name:
            self.logger.error(
                _("无法进行编译, 当前根目录下存在多个主文件: ")
                + ", ".join(main_files_in_root)
            )
            self.logger.warning(
                _(
                    '请修改待编译主文件名为默认文件名 "%(args)s.tex" 或在文件中加入魔法注释 "% !TEX root = [待编译主文件名]" 或在终端输入 "pytexmk [待编译主文件名]" 进行编译, 或删除当前根目录下多余的 tex 文件'
                )
                % {"args": default_file}
            )
            self.logger.warning(_("当前根目录是: ") + str(current_path))
            exit_pytexmk()

        return project_name

    def draft_model(self, project_name: str, draft_run: bool, draft_judgement: bool):
        if not draft_run:
            self.logger.info(_("草稿模式未启用, 跳过处理."))
            return

        file_name = f"{project_name}.tex"
        file_path = Path(file_name)

        pattern = re.compile(
            r"(?<!%)(?<!% )(?<!%  )\\documentclass(?:\[([^\]]*)\])?\{([^\}]*)\}"
        )

        def _replace_draft(match):
            options = match.group(1) or ""
            class_type = match.group(2)

            options = set(options.split(",")) if options else set()
            options.add("draft") if draft_judgement else options.discard("draft")

            options_str = ",".join(options).strip()
            options_str = f"[{options_str}]" if options_str else ""

            return f"\\documentclass{options_str}{{{class_type}}}"

        try:
            content = file_path.read_text(encoding="utf-8")

            modified_content = pattern.sub(_replace_draft, content)

            if modified_content != content:
                file_path.write_text(modified_content, encoding="utf-8")
                self.logger.info(
                    _("启用草稿模式") if draft_judgement else _("关闭草稿模式")
                )
                if draft_judgement:
                    file_size = file_path.stat().st_size / 1024**2
                    self.logger.info(
                        _("处理文件: %(args)s, 文件大小: %(size).3f MB")
                        % {"args": file_name, "size": file_size}
                    )
            else:
                self.logger.info(_("未匹配到内容, 文件未修改."))

        except FileNotFoundError:
            self.logger.error(_("文件未找到: ") + file_name)
        except PermissionError:
            self.logger.error(_("权限错误: 无法读取或写入文件: ") + file_name)
        except Exception as e:  # noqa: BLE001
            self.logger.error(_("更新草稿模式时出错: " + str(e)))

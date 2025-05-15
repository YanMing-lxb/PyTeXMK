'''
 =======================================================================
 ····Y88b···d88P················888b·····d888·d8b·······················
 ·····Y88b·d88P·················8888b···d8888·Y8P·······················
 ······Y88o88P··················88888b·d88888···························
 ·······Y888P··8888b···88888b···888Y88888P888·888·88888b·····d88b·······
 ········888······"88b·888·"88b·888·Y888P·888·888·888·"88b·d88P"88b·····
 ········888···d888888·888··888·888··Y8P··888·888·888··888·888··888·····
 ········888··888··888·888··888·888···"···888·888·888··888·Y88b·888·····
 ········888··"Y888888·888··888·888·······888·888·888··888··"Y88888·····
 ·······························································888·····
 ··························································Y8b·d88P·····
 ···························································"Y88P"······
 =======================================================================

 -----------------------------------------------------------------------
Author       : 焱铭
Date         : 2024-02-29 16:02:37 +0800
LastEditTime : 2025-05-15 19:22:11 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /PyTeXMK/src/pytexmk/additional.py
Description  : 
 -----------------------------------------------------------------------
'''
# -*- coding: utf-8 -*-
import re
import time
import logging
import webbrowser
import subprocess
from rich import print
from pathlib import Path
from rich.theme import Theme
from typing import List, Dict
from rich.console import Console
from collections import defaultdict
from pypdf import PdfReader, PdfWriter

from pytexmk.language import set_language
from pytexmk.auxiliary_fun import exit_pytexmk
from pytexmk.log_parser import LatexLogParser

_ = set_language('additional')

custom_theme = Theme({
    "success": "bold green",
    "warning": "bold yellow",
    "error": "bold red",
    "info": "bold blue",
    "status": "bold cyan",
    "time": "bold magenta"
})
console = Console(theme=custom_theme, legacy_windows=False)

class MySubProcess(object):
    def __init__(self, outdir, auxdir, project_name: str = None, latexdiff: bool = False):
        self.logger = logging.getLogger(__name__)
        self.project_name = project_name
        self.latexdiff = latexdiff
        self.outdir = outdir
        self.auxdir = auxdir
        self.MRO = MoveRemoveOperation()
    def _format_duration(self, seconds: float) -> str:
        """格式化时间显示"""
        if seconds > 60:
            return f"{seconds // 60:.0f}m {seconds % 60:.2f}s"
        return f"{seconds:.4f}s"
    def run_command(self, command: list, out_files:str, aux_files:str, program_name: str = "执行命令") -> bool:
        """
        通用命令执行函数
        :param command: 要执行的命令列表
        :param success_msg: 成功时显示的消息（支持富文本样式）
        :param error_msg: 失败时的错误提示前缀
        :param process_name: 正在进行的操作名称（用于状态提示）
        :return: 执行是否成功
        """
        try:
            console.print(_("[bold]运行命令: [/bold]") + f"[cyan]{' '.join(command)}")
            start_time = time.time()
            
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                encoding='utf-8',
            )
            
            with console.status(f"[status]正在{program_name}..."):  # 动态状态提示
                while True:
                    output = process.stdout.readline()
                    if not output and process.poll() is not None:
                        break
                    if output:
                        console.print(f"[dim]{output.strip()}[/]")

            if process.returncode == 0:
                console.print(
                    f"✓ 运行 {program_name} 成功 "
                    f"[time](耗时: {self._format_duration(time.time()-start_time)})[/]",
                    style="success"
                )

            else:
                raise subprocess.CalledProcessError(process.returncode, command)

        except subprocess.CalledProcessError as e:
            self.logger.error(_("%(args)s 编译失败,请查看日志文件以获取详细信息: ") % {'args': program_name} + f"{self.auxdir}{self.project_name+'.log' if not self.latexdiff else '/'}")

            self.MRO.move_specific_files(aux_files, '.', self.auxdir)
            self.MRO.move_specific_files(out_files, '.', self.outdir)

            if not self.latexdiff:
                log_parser = LatexLogParser()
                log_parser.logparser_cli(self.auxdir, self.project_name)
            exit_pytexmk()


class MoveRemoveOperation(object):

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    # --------------------------------------------------------------------------------
    # 将指定文件从文件夹中清除
    # --------------------------------------------------------------------------------
    def remove_specific_files(self, files: list, folder: str):
        """删除指定文件

        行为逻辑说明:
        - 遍历`files`列表，直接删除`folder`目录中的每个文件。
        - 对于每个文件，使用`Path`对象的`/`操作符构建完整路径。
        - 检查文件是否存在，如果存在，则尝试使用`unlink`方法删除文件。
        - 删除成功时，通过`logger`记录成功信息，格式为：“删除成功: 文件路径”。
        - 如果删除过程中出现`OSError`，则通过`logger`记录错误信息，格式为：“删除失败: 文件路径 --> 错误信息”。

        Parameters
        ----------
        files : list
            要删除的具体文件名列表
        folder : str
            要删除文件的目录路径
        """
        for file in files:
            filepath = Path(folder) / file  # 使用Path对象的/操作符构建路径
            if filepath.exists():
                try:
                    filepath.unlink()  # 使用unlink删除文件
                    self.logger.info(_("删除成功: ") + str(filepath))
                except OSError as e:
                    self.logger.error(_("删除失败: ") + f"{filepath} --> {e}")

    # --------------------------------------------------------------------------------
    # 将正则表达式匹配的文件从文件夹中清除
    # --------------------------------------------------------------------------------
    def remove_matched_files(self, patterns: list[re.Pattern], folder: str):
        """删除匹配正则表达式的文件

        行为逻辑说明:
        - 遍历`patterns`列表，编译每个正则表达式模式。
        - 使用`rglob("*")`递归遍历`folder`目录及其子目录中的所有文件。
        - 如果发现文件路径包含`.git`或`.github`目录，则跳过该文件。
        - 如果文件路径对应的文件名匹配编译后的正则表达式，则尝试删除该文件。
        - 删除成功时，通过`logger.info`记录成功的信息。
        - 如果删除过程中发生`OSError`，则通过`logger.error`记录失败的信息以及错误详情。

        Parameters
        ----------
        patterns : re.Pattern
            要删除的正则表达式模式列表。
        folder : str
            要删除文件的目录路径。
        """
        for pattern in patterns:
            compiled_pattern = re.compile(pattern)
            for filepath in Path(folder).rglob("*"):  # 使用rglob递归遍历所有文件
                if '.git' in filepath.parts or '.github' in filepath.parts:
                    continue  # 跳过这些文件夹
                if filepath.is_file() and compiled_pattern.match(filepath.name):
                    try:
                        filepath.unlink()  # 使用unlink删除文件
                        self.logger.info(_("删除成功: ") + str(filepath))
                    except OSError as e:
                        self.logger.error(_("删除失败: ") + f"{filepath} --> {e}")

    # --------------------------------------------------------------------------------
    # 将指定文件从根目录移动到目标文件夹,如果目标文件存在则覆盖
    # --------------------------------------------------------------------------------
    def move_specific_files(self, files: list, src_folder: str, dest_folder: str):
        """将指定文件从源文件夹移动到目标文件夹

        行为逻辑说明:
        - 检查源文件夹和目标文件夹是否存在
        - 如果源文件夹或目标文件夹不存在，则创建目标文件夹及其所有必要的上级目录
        - 遍历需要移动的文件列表
        - 对于每个文件，构建其在源文件夹和目标文件夹中的完整路径
        - 如果目标文件夹中已存在该文件，则尝试删除该文件
        - 如果删除文件时发生错误，则记录错误信息并中断操作
        - 如果源文件夹中存在该文件，则尝试将文件从源文件夹移动到目标文件夹
        - 如果移动文件成功，则记录成功信息
        - 如果移动文件时发生错误，则记录错误信息

        Parameters
        ----------
        files : list
            需要移动的文件列表
        src_folder : str
            源文件夹路径
        dest_folder : str
            目标文件夹路径
        """
        src_folder_path = Path(src_folder)
        dest_folder_path = Path(dest_folder)

        if not src_folder_path.exists() or not dest_folder_path.exists():
            dest_folder_path.mkdir(parents=True, exist_ok=True)  # 创建目标文件夹 如果 exist_ok=True,当目标文件夹已存在时,mkdir() 不会引发错误，parents=True：递归地创建所有必要的上级目录.

        for file in files:
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
                    self.logger.info(_("移动成功: ") + f"{src_file_path} ==> {dest_folder}")
                except OSError as e:
                    self.logger.error(_("移动失败: ") + f"{src_file_path} ==> {dest_folder} --> {e}")

    # --------------------------------------------------------------------------------
    # 将正则表达式匹配的文件从根目录移动到目标文件夹,如果目标文件存在则覆盖
    # --------------------------------------------------------------------------------
    def move_matched_files(self, patterns: list[re.Pattern], src_folder: str, dest_folder: str):
        """将正则表达式匹配的文件从根目录移动到目标文件夹,如果目标文件存在则覆盖

        行为逻辑说明:
        - 将源文件夹路径和目标文件夹路径分别转换为Path对象。
        - 使用`mkdir`方法创建目标文件夹（如果目标文件夹已存在，则不会引发错误）。
        - 编译正则表达式模式列表以提高匹配性能。
        - 遍历源文件夹中的所有文件。
        - 对于每个文件，检查其是否为文件而非文件夹。
        - 遍历所有正则表达式模式，检查文件名是否与任一模式匹配。
        - 如果文件名匹配某一模式，构建目标文件路径。
        - 检查目标文件路径下是否存在同名文件，如果存在则尝试删除旧文件。
        - 如果旧文件删除失败，记录错误信息并跳过当前文件的移动操作。
        - 如果目标文件路径下不存在同名文件或旧文件已成功删除，尝试将文件移动到目标文件夹。
        - 如果文件移动成功，记录成功信息；如果移动失败，记录错误信息。
        - 一旦文件匹配并移动（或尝试移动）成功后，不再检查其他正则表达式模式。

        Parameters
        ----------
        patterns : list[re.Pattern]
            正则表达式模式列表
        src_folder : str
            源文件夹路径
        dest_folder : str
            目标文件夹路径
        """
        src_folder_path = Path(src_folder)  # 将源文件夹路径转换为Path对象
        dest_folder_path = Path(dest_folder)  # 将目标文件夹路径转换为Path对象

        # 创建目标文件夹
        dest_folder_path.mkdir(parents=True, exist_ok=True)  # exist_ok=True,当目标文件夹已存在时,mkdir() 不会引发错误.

        # 编译正则表达式模式以提高匹配性能
        compiled_patterns = [re.compile(pattern) for pattern in patterns]

        for file_path in src_folder_path.iterdir():  # 遍历源文件夹中的所有文件
            if file_path.is_file():  # 确保是文件而不是文件夹
                for pattern in compiled_patterns:  # 遍历所有正则表达式模式
                    if pattern.match(file_path.name):  # 检查文件名是否匹配正则表达式模式
                        dest_file_path = dest_folder_path / file_path.name  # 构建目标文件路径

                        if dest_file_path.exists():  # 检查目标文件是否存在
                            try:
                                dest_file_path.unlink()  # 删除目标文件
                            except OSError as e:
                                self.logger.error(_("删除失败: ") + f"{dest_file_path} --> {e}")  # 记录删除失败错误信息
                                break  # 跳过当前文件的移动操作

                        try:
                            file_path.rename(dest_file_path)  # 使用pathlib的rename方法移动文件
                            self.logger.info(_("移动成功: ") + f"{file_path.name} ==> {dest_folder}")  # 记录文件移动成功信息
                        except OSError as e:
                            self.logger.error(_("移动失败: ") + f"{file_path.name} ==> {dest_folder} --> {e}")  # 记录文件移动失败错误信息
                        break  # 匹配到一个模式后,不再检查其他模式


class MainFileOperation(object):

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    # --------------------------------------------------------------------------------
    # 定义输入检查函数
    # --------------------------------------------------------------------------------
    def check_project_name(self, main_files: list, check_project_name: str, suffix: str) -> str:
        """检查给定的项目名称是否存在于主文件列表中，并且是否具有指定的后缀。

        行为逻辑说明:
        - 使用 `Path` 对象处理 `check_project_name` 文件路径。
            - 提取文件名（不包括后缀）到 `base_name` 变量。
            - 提取文件后缀到 `file_extension` 变量。
        - 检查路径是否为空：
            - 如果 `check_project_name` 包含路径（`path_obj.parent` 不等于 `Path('')`），则记录错误信息“文件名中不能存在路径”并退出程序。
        - 检查文件名和后缀是否匹配，并且文件名是否在主文件列表中：
            - 如果文件后缀与预期后缀一致并且文件名在 `main_files` 列表中，则返回 `base_name`。
            - 如果文件名在 `main_files` 列表中但没有指定的后缀，则返回 `base_name`。
        - 如果文件名或后缀不匹配：
            - 记录错误信息“文件类型非 .tex: [bold cyan]check_project_name.tex”，并退出程序。

        Parameters
        ----------
        main_files : list
            包含主文件名（不带路径与后缀）的字符串列表。
        check_project_name : str
            用户提供的项目名称，可能包含路径和后缀
        suffix : str
            文件的预期后缀，例如 '.tex'。

        Returns
        -------
        str
            不包括后缀的主文件名
        
        Raises
        ------
        SystemExit
            如果文件名中包含路径，或者文件不存在于当前路径下，或者文件类型不匹配时，程序将记录错误信息并退出。
        """

        path_obj = Path(check_project_name)  # 使用Path对象处理文件路径
        base_name = path_obj.stem  # 提取文件名(不包括后缀)
        file_extension = path_obj.suffix  # 提取文件后缀

        # 检查路径是否为空
        if path_obj.parent != Path(''):  # 如果输入的check_project_name是一个路径不为空的字符串
            self.logger.error(_("文件名中不能存在路径"))
            exit_pytexmk()

        # 检查文件名和后缀是否匹配，并且文件名是否在主文件列表中
        if file_extension == suffix and base_name in main_files:
            return base_name

        # 如果文件名在主文件列表中但没有指定的后缀
        if not file_extension and base_name in main_files:  # 如果输入的文件没有后缀，且存在于 main_files 中
            return base_name

        # 如果文件名或后缀不匹配
        self.logger.error(_("文件类型非 %(args)s: ") % {'args': suffix} + f"[bold cyan]{check_project_name}{suffix}")
        exit_pytexmk()

    # --------------------------------------------------------------------------------
    # 定义 tex 文件检索函数
    # --------------------------------------------------------------------------------
    def get_suffix_files_in_dir(self, dir: str, suffix: str) -> list:
        """获取指定后缀的文件名列表
        行为逻辑说明:
        - 初始化一个空列表`suffix_files_in_dir`，用于存储匹配的文件名。
        - 使用`Path`对象将输入的目录路径转换为可操作的路径对象。
        - 尝试遍历目录下所有以指定后缀结尾的文件：
            - 对于每个匹配的文件，去掉路径，提取文件名（不带后缀），并将其添加到`suffix_files_in_dir`列表中。
            - 使用日志记录器`self.logger`记录找到的每个文件名及其后缀。
        - 遍历完成后检查`suffix_files_in_dir`列表是否为空：
            - 如果不为空，记录匹配的文件总数。
            - 如果为空，记录错误信息和当前路径，并调用`exit_pytexmk()`函数退出程序。
        - 使用`try-except`块捕获并处理在文件搜索过程中可能发生的任何异常，使用日志记录器记录错误信息。
        - 返回匹配后缀的文件名列表。

        Parameters
        ----------
        dir : str
            目标目录路径
        suffix : str
            文件后缀

        Returns
        -------
        list
            匹配后缀的文件名列表
        
        Raises
        ------
        SystemExit
            如果搜索过程中发生异常，会记录错误信息。
            如果没有找到匹配的文件，会记录错误信息并退出程序。
        """
        suffix_files_in_dir = []
        # 获取当前路径
        current_path = Path(dir)  # 转换为Path对象
        try:
            # 遍历目录下所有以指定后缀结尾的文件
            for file in current_path.glob(f'*{suffix}'):
                # 去掉路径,提取文件名和后缀
                base_name = file.stem
                suffix_files_in_dir.append(base_name)
                self.logger.info(_("搜索到: ") + f"{base_name}{suffix}")

            if suffix_files_in_dir:
                self.logger.info(f"{suffix}" + _("文件数目: ") + str(len(suffix_files_in_dir)))
            else:
                self.logger.error(_("文件不存在于当前路径下，请检查终端显示路径是否是项目路径"))
                self.logger.warning(_("当前终端路径: ") + str(current_path))
                exit_pytexmk()
        except Exception as e:
            self.logger.error(_("文件搜索失败: ") + f"{suffix} --> {e}")
        return suffix_files_in_dir

    # --------------------------------------------------------------------------------
    # 定义 tex 文件 \documentclass 和 \begin{document} 检索函数
    # --------------------------------------------------------------------------------
    def find_tex_commands(self, tex_files_in_root: list) -> list:
        """给定的 tex 文件列表中查找包含特定命令（\documentclass 和 \begin{document}）的主 tex 文件

        行为逻辑说明:
        - **初始化主文件列表**：创建一个空列表 `main_tex_files` 用于存储找到的主 tex 文件名。
        - **遍历文件名列表**：对于传入的每个文件名，执行以下操作：
            - **打开文件**：尝试使用 `Path` 对象打开文件（文件名后缀为 `.tex`），并设置编码为 `utf-8`。
            - **检查主文件特征命令**：读取文件的前 200 行，跳过以 `%` 开头的注释行和空行。如果在这些行中找到 `\documentclass` 或 `\begin{document}` 命令，则认为该文件是主文件，并将其文件名添加到 `main_tex_files` 列表中，同时记录日志信息。
        - **异常处理**：如果文件打开或读取过程中发生异常，捕获异常并记录错误信息，包括文件名和错误描述。
        - **记录主文件数量**：遍历完成后，检查 `main_tex_files` 列表是否为空。
            - 如果不为空，记录找到的主文件数量。
            - 如果为空，记录错误信息并警告当前终端路径，随后调用 `exit_pytexmk()` 退出程序。
        - **返回主文件列表**：最后，返回包含主 tex 文件名的 `main_tex_files` 列表。

        Parameters
        ----------
        tex_files_in_root : list
            包含 tex 文件名的字符串列表

        Returns
        -------
        list
            包含主文件名的字符串列表
        Raises
        ------
        SystemExit
            如果文件读取失败，或者文件中没有找到主文件特征命令，会记录错误信息。
        """
        # 初始化主文件列表
        main_tex_files = []
        # 遍历传入的文件名列表
        for file_name in tex_files_in_root:
            try:
                # 使用Path对象打开文件
                with open(Path(file_name).with_suffix('.tex'), 'r', encoding='utf-8') as file:
                    is_main_file = False  # 假设当前文件不是主文件

                    for i in range(200):  # 读取前200行
                        line = file.readline()

                        if line.strip().startswith('%') or not line.strip():  # 读取前200行
                            continue

                        # 检查是否包含主文件特征命令
                        if r"\documentclass" in line or r"\begin{document}" in line:
                            is_main_file = True
                            break

                    # 如果找到主文件特征命令,则将文件名添加到主文件列表中
                    if is_main_file:
                        main_tex_files.append(file_name)
                        self.logger.info(_("通过特征命令检索到主文件: ") + str(file_name))
            except Exception as e:
                # 捕获并记录文件读取错误
                self.logger.error(_("打开文件失败: ") + f"{file_name}.tex --> {e}")

        # 如果有找到主文件,则记录数量
        if main_tex_files:
            self.logger.info(_("发现主文件数量: ") + str(len(main_tex_files)))
        else:
            # 如果没有找到主文件,则记录错误并退出程序
            self.logger.error(_("终端路径下不存在主文件!请检查终端显示路径是否是项目路径!"))
            self.logger.warning(_("当前终端路径: ") + str(Path.cwd()))
            exit_pytexmk()
        # 返回主文件列表
        return main_tex_files

    # --------------------------------------------------------------------------------
    # 定义魔法注释检索函数
    # --------------------------------------------------------------------------------
    def search_magic_comments(self, main_files_in_root: List[str], magic_comment_keys: List[str]) -> Dict[str, Dict[str, str]]:
        """搜索指定TeX文件中的所有魔法注释。

        行为逻辑说明:
        - 使用 `defaultdict(dict)` 初始化 `file_magic_comments`，用于存储每个文件的魔法注释。
        - 遍历 `main_files_in_root` 列表中的每个文件路径。
            - 使用 `Path` 对象打开文件（确保文件路径以 `.tex` 结尾），并设置编码为 `utf-8`。
            - 逐行读取文件内容，最多读取前 50 行。
            - 对于每行内容，遍历 `magic_comment_keys` 列表中的每个关键字。
            - 使用正则表达式匹配魔法注释的关键字和值，忽略大小写。
            - 如果匹配到魔法注释，提取其值并存储在 `file_magic_comments` 中，随后跳出当前关键字的循环，避免在一行中重复匹配同一关键字。
        - 如果文件打开或读取过程中发生异常，捕获异常并记录错误信息，包括文件路径和错误描述，然后继续处理下一个文件。
        - 将 `file_magic_comments` 中的数据结构从 `{file_path: {magic_comment_key: magic_comment_value},...}` 转换为 `{magic_comment_key: {file_path: magic_comment_value},...}`，存储在 `all_magic_comments` 中。
        - 返回 `all_magic_comments`，将 `defaultdict` 转换为普通的字典，便于后续处理。

        Parameters
        ----------
        main_files_in_root : List[str]
            包含TeX文件路径的列表
        magic_comment_keys : List[str]
            包含魔法注释关键字的列表

        Returns
        -------
        Dict[str, Dict[str, str]]
            包含所有魔法注释的字典，格式为 {magic_comment_key: {file_path: magic_comment_value},...}.
        """
        file_magic_comments = defaultdict(dict)
        # 用于存储每个文件的魔法注释 defaultdict 在访问不存在的键时，会自动返回一个默认值，该处返回一个空字典。

        for file_path in main_files_in_root:  # 遍历TeX文件列表
            try:
                file_path_obj = Path(file_path).with_suffix('.tex')  # 使用pathlib创建文件路径对象
                with file_path_obj.open('r', encoding='utf-8') as file:  # 使用pathlib打开文件
                    for line_number, line_content in enumerate(file, start=1):  # 逐行读取文件内容
                        if line_number > 50:  # 如果已经读取了前50行，则停止读取
                            break
                        for magic_comment_key in magic_comment_keys:  # 遍历魔法注释关键字列表
                            # 使用正则表达式匹配魔法注释
                            pattern = rf'%(?:\s*)!TEX {re.escape(magic_comment_key)}(?:\s*)=(?:\s*)(.*?)(?=\s|%|$)'
                            match_result = re.search(pattern, line_content, re.IGNORECASE)
                            # re.IGNORECASE 忽略大小写，即使魔法注释的关键字在文件中以不同的大小写形式出现（例如 !TeX、!tex、!TEX），代码仍然能够正确匹配并提取其值
                            if match_result:  # 如果匹配到魔法注释
                                matched_comment_value = match_result.group(1).strip()  # 提取魔法注释的值
                                file_magic_comments[file_path][magic_comment_key] = matched_comment_value  # 存储魔法注释
                                break  # 跳出当前循环,避免在一行中重复匹配同一关键字
            except Exception as e:
                self.logger.error(_("打开文件失败: ") + f"{file_path} --> {e}")
                continue  # 跳过当前文件,继续处理下一个文件

        # 将数据结构从 {file_path: {magic_comment_key: magic_comment_value},...}
        # 转换为 {magic_comment_key: {file_path: magic_comment_value},...}
        all_magic_comments = defaultdict(dict)
        for file_path, comments in file_magic_comments.items():  # 遍历文件魔法注释字典
            for key, value in comments.items():  # 遍历每个文件的魔法注释
                all_magic_comments[key][file_path] = value  # 存储文件路径和魔法注释值
        return dict(all_magic_comments)  # 返回提取的键值对字典，将 defaultdict 转换为普通的字典，便于后续处理

    # --------------------------------------------------------------------------------
    # 定义魔法注释检索获取主文件函数
    # --------------------------------------------------------------------------------
    def get_main_file(self, default_file: str, args_document: str, main_files_in_root: List[str], all_magic_comments: Dict[str, Dict[str, str]]) -> str:
        """根据提供的信息获取主TeX文件

        行为逻辑说明
        - 检查命令行参数：
            - 如果通过命令行参数指定了主文件名（`args_document`），直接使用该文件名作为主文件并返回。
        - 检查根目录下的唯一文件：
            - 如果当前根目录下存在且只有一个TeX文件（`main_files_in_root`），将该文件作为主文件并返回。
        - 检查魔法注释：
            - 如果根目录下的多个文件中存在`% !TEX root`魔法注释：
                - 如果只有唯一一个这样的注释，则使用该注释指定的文件作为主文件。
                - 如果存在多个`% !TEX root`魔法注释，或者魔法注释指定的文件名与当前文件名不匹配，则记录警告信息，无法确定主文件。
        - 使用默认文件名：
            - 如果通过上述步骤仍未确定主文件，则尝试使用默认文件名（`default_file`）进行匹配。
            - 如果找到匹配的文件名，则将其作为主文件并返回。
            - 如果未找到默认文件名的文件，则记录信息，提示未找到默认文件名的文件。
        - 处理多文件情况：
            - 如果当前根目录下存在多个主文件并且没有找到合适的主文件，则记录错误信息，提示存在多个主文件，无法进行编译。
            - 记录警告信息，建议用户通过修改文件名、添加魔法注释、使用命令行参数或删除多余文件来解决问题。
        - 退出程序。

        Parameters
        ----------
        default_file : str
            默认的主文件名
        args_document : str
            通过命令行参数指定的主文件名
        main_files_in_root : List[str]
            当前根目录下的TeX文件路径列表，已经去除了后缀名
        all_magic_comments : Dict[str, Dict[str, str]]
            包含所有魔法注释的字典，格式为 {magic_comment_key: {file_path: magic_comment_value},...}

        Returns
        -------
        str
            待编译的主文件名
        """
        project_name = ''
        current_path = Path.cwd()  # 使用pathlib库获取当前工作目录的路径

        if args_document:  # 命令行参数中指定了主文件
            project_name = args_document
            project_name = self.check_project_name(main_files_in_root, project_name, '.tex')  # 检查 project_name 是否正确
            print(_("通过命令行命令指定待编译主文件为: ") + f"[bold cyan]{project_name}")
            return project_name

        if len(main_files_in_root) == 1:  # 如果当前根目录下存在且只有一个主文件
            project_name = main_files_in_root[0]
            print(_("通过根目录下唯一主文件指定待编译主文件为: ") + f"[bold cyan]{project_name}.tex")
            return project_name

        if 'root' in all_magic_comments:  # 存在 % TEX root 魔法注释
            self.logger.info(_("魔法注释 % !TEX root 在当前根目录下主文件中有被定义"))
            if len(all_magic_comments['root']) == 1:  # 只有一个 % TEX root 魔法注释
                file_path, root_value = next(iter(all_magic_comments['root'].items()))  # 获取唯一的一个键值对
                self.logger.info(_("魔法注释 % !TEX root 只存在于: ") + f"{file_path}.tex")
                check_file = self.check_project_name(main_files_in_root, root_value, '.tex')  # 检查 magic comments 中指定的 root 文件名是否正确
                if file_path == check_file:  # 如果 magic comments 中指定的 root 文件名与当前文件名相同
                    project_name = check_file  # 使用魔法注释 % !TEX root 指定的文件作为主文件
                    print(_("通过魔法注释 % !TEX root 指定待编译主文件为: ") + f"[bold cyan]{project_name}.tex")
                    return project_name
                else:  # 如果 magic comments 中指定的 root 文件名与当前文件名不同
                    self.logger.warning(_("魔法注释 % !TEX root 指定的文件名与当前文件名不同, 无法确定主文件: ") + f"[bold red]{check_file}.tex[/bold red], [bold green]{file_path}.tex[/bold green] ")
            elif len(all_magic_comments['root']) > 1:  # 当前目录下存在多个主文件, 且多个 tex 文件中同时存在 % TEX root 魔法注释
                self.logger.warning(_("魔法注释 % !TEX root 在当前根目录下的多个主文件中同时被定义, 无法根据魔法注释确定待编译主文件"))

        if not project_name:  # 如果当前根目录下存在多个主文件, 且不存在 % TEX root 魔法注释, 并且待编译主文件还没有找到
            self.logger.info(_("无法根据魔法注释判断出待编译主文件, 尝试根据默认主文件名指定待编译主文件"))
            for file in main_files_in_root:
                if file == default_file:  # 如果存在 default_file.tex 文件
                    project_name = file  # 使用 default_file.tex 文件作为待编译主文件名
                    print(_("通过默认文件名 \"%(args)s.tex\" 指定待编译主文件为: ") % {"args": default_file} + f"[bold cyan]{project_name}.tex")
                    return project_name
                else:
                    self.logger.info(_("当前根目录下不存在名为 \"%(args)s.tex\" 的文件") % {"args": default_file})

        if not project_name:  # 如果当前根目录下不存在主文件且 -d 参数未指定
            self.logger.error(_("无法进行编译, 当前根目录下存在多个主文件: ") + ", ".join(main_files_in_root))
            self.logger.warning(_("请修改待编译主文件名为默认文件名 \"%(args)s.tex\" 或在文件中加入魔法注释 \"% !TEX root = [待编译主文件名]\" 或在终端输入 \"pytexmk [待编译主文件名]\" 进行编译, 或删除当前根目录下多余的 tex 文件") % {"args": default_file})
            self.logger.warning(_("当前根目录是: ") + str(current_path))
            exit_pytexmk()

        return project_name

    # --------------------------------------------------------------------------------
    # 定义草稿模式切换函数
    # --------------------------------------------------------------------------------
    def draft_model(self, project_name: str, draft_run: bool, draft_judgement: bool):
        """更新 LaTeX 文档的草稿模式

        - 构建 LaTeX 文件的完整路径。
        - 定义正则表达式模式以匹配 `\documentclass[args1, args2, ...]{class}` 命令。
        - 根据 `draft_judgement` 的值，决定是在匹配到的 `\documentclass` 命令中添加还是移除 "draft" 选项。
        - 读取 LaTeX 文件的内容，如果文件不存在则记录错误信息。
        - 使用定义的正则表达式模式替换文件内容中的 `\documentclass` 命令，根据 `draft_judgement` 的值判断是否添加或移除 "draft" 选项。
        - 如果文件内容被成功修改，则记录相关信息，并在启用草稿模式时记录文件大小。
        - 如果没有匹配到内容，则记录文件未修改的信息。
        - 如果在读取或写入文件时出现权限错误，则记录错误信息。
        - 捕获并记录所有其他可能的异常。

        Parameters
        ----------
        project_name : str
            LaTeX 项目的文件名，不包括 `.tex` 扩展名。
        draft_run : bool
            是否启用草稿模式。如果为 `True`，则启用草稿模式；否则跳过处理。
        draft_judgement : bool
            是否在 `\documentclass` 命令中添加或移除 "draft" 选项。如果为 `True`，则添加 "draft"；否则移除 "draft".

        """
        if not draft_run:
            self.logger.info(_("草稿模式未启用, 跳过处理."))
            return

        file_name = f"{project_name}.tex"
        file_path = Path(file_name)

        # 定义正则表达式模式来匹配 \documentclass[args1, args2, ...]{class} 命令
        pattern = re.compile(r'(?<!%)(?<!% )(?<!%  )\\documentclass(?:\[([^\]]*)\])?\{([^\}]*)\}')

        # 根据 draft_judgement 的值决定是否添加或移除 "draft,"
        def _replace_draft(match):
            options = match.group(1) or ''
            class_type = match.group(2)

            options = set(options.split(',')) if options else set()  # 转换为 set 类型，如果为空则为空集，否则以,分隔构建成 set
            options.add('draft') if draft_judgement else options.discard('draft')  # 添加或移除 "draft" 选项

            options_str = ','.join(options).strip()  # 转换回字符串，去除空白字符
            options_str = f'[{options_str}]' if options_str else ''  # 加上方括号

            return f'\\documentclass{options_str}{{{class_type}}}'

        try:
            content = file_path.read_text(encoding='utf-8')

            modified_content = pattern.sub(_replace_draft, content)

            if modified_content != content:
                file_path.write_text(modified_content, encoding='utf-8')
                self.logger.info(_("启用草稿模式") if draft_judgement else _("关闭草稿模式"))
                if draft_judgement:
                    file_size = file_path.stat().st_size / 1024**2
                    self.logger.info(_("处理文件: %(args)s, 文件大小: %(size).3f MB") % {"args": file_name, "size": file_size})
            else:
                self.logger.info(_("未匹配到内容, 文件未修改."))

        except FileNotFoundError:
            self.logger.error(_("文件未找到: ") + file_name)
        except PermissionError:
            self.logger.error(_("权限错误: 无法读取或写入文件: ") + file_name)
        except Exception as e:
            self.logger.error(_("更新草稿模式时出错: " + str(e)))


class PdfFileOperation(object):

    def __init__(self, viewer="default"):
        self.logger = logging.getLogger(__name__)
        self.viewer = viewer

    def set_viewer(self, new_viewer):
        self.viewer = new_viewer

    # --------------------------------------------------------------------------------
    # 定义 PDF 预览器选择函数
    # --------------------------------------------------------------------------------
    def _preview_pdf_by_viewer(self, local_path: str):
        """该方法用于通过指定的PDF查看器打开本地PDF文件进行预览

        行为逻辑说明:
        - 方法首先检查 `self.viewer` 是否被设置为 `"default"` 或者是否为空。
            - 如果是，则使用 `webbrowser.open(local_path)` 打开PDF文件，使用的是系统默认的PDF查看器。
            - 同时，记录日志信息："未设置 PDF 查看器,使用默认 PDF 查看器"。
        - 如果 `self.viewer` 已经被设置，并且不等于 `"default"`，则记录日志信息："设置 PDF 查看器: {self.viewer}"。
            - 注意：这里仅记录了日志信息，并没有实际打开PDF文件的逻辑。

        Parameters
        ----------
        local_path : str
            本地PDF文件的路径
        """
        if self.viewer == "default" or not self.viewer:
            self.logger.info(_("未设置 PDF 查看器,使用默认 PDF 查看器"))
            webbrowser.open(local_path)
        elif self.viewer and self.viewer != "default":
            self.logger.info(_("设置 PDF 查看器: ") + f"{self.viewer}")
            # TODO:调用指定外部程序打开文件需要完善

    # --------------------------------------------------------------------------------
    # 定义 PDF 文件预览函数
    # --------------------------------------------------------------------------------
    def pdf_preview(self, project_name: str, outdir: str):
        """预览PDF文件的方法

        行为逻辑说明:
        - 在 `try` 块中执行以下操作：
            - 构建PDF文件名 `pdf_name`，格式为 `{project_name}.pdf`
            - 使用 `pathlib` 拼接PDF文件路径 `pdf_path`，即 `Path(outdir) / pdf_name`
            - 使用 `pathlib` 获取PDF文件的绝对路径，并将其转换为URL格式 `local_path`，即 `f"file://{pdf_path.resolve().as_posix()}"`
            - 记录日志信息："文件路径: {local_path}"
            - 调用 `_preview_pdf_by_viewer` 方法，传入 `local_path` 以通过指定的PDF查看器打开PDF文件
        - 在 `except` 块中捕获并记录任何异常：
            - 记录错误信息："打开文件失败: {pdf_name} --> {e}"
        - 在 `finally` 块中执行的操作：
            - 打印退出信息并调用 `exit_pytexmk` 退出程序
 
        Parameters
        ----------
        project_name : str
            项目名称
        outdir : str
            该项目输出的 PDF 文件所在目录
        """
        try:
            pdf_name = f"{project_name}.pdf"
            # 使用 pathlib 拼接 pdf 文件路径
            pdf_path = Path(outdir) / pdf_name
            # 使用 pathlib 获取 pdf 文件的绝对路径
            local_path = f"file://{pdf_path.resolve().as_posix()}"
            self.logger.info(_("文件路径: ") + f"{local_path}")
            # 使用 webbrowser 打开 pdf 文件
            self._preview_pdf_by_viewer(local_path)
        except Exception as e:
            # 记录打开 README 文件时的错误信息
            self.logger.error(_("打开文件失败: ") + f"{pdf_name} -->{e}")
        finally:
            # 打印退出信息并退出程序
            exit_pytexmk()

    # --------------------------------------------------------------------------------
    # 定义 PDF 文件修复函数
    # --------------------------------------------------------------------------------
    def pdf_repair(self, project_name: str, root_dir: str, excluded_folder: str):
        """ 对每个PDF文件进行打开和关闭操作,以修复可能存在的文件未正确关闭的问题.

        行为逻辑说明:
        - 将输入的 `root_dir` 转换为 `Path` 对象，以便于后续的文件路径操作。
        - 使用 `rglob` 方法遍历 `root_dir` 及其所有子目录中的所有以 `.pdf` 结尾的文件，并收集路径。
            - 在收集路径的过程中，排除路径中包含 `.git` 或 `.github` 的文件。
            - 确保路径是一个文件。
            - 排除与 `project_name` 相同名称的PDF文件。
            - 排除位于 `excluded_folder` 文件夹中的PDF文件。
        - 如果未找到任何PDF文件，打印信息并返回。
        - 打印找到的PDF文件数量。
        - 对于每个找到的PDF文件，尝试读取并重新写入以修复：
            - 使用 `PdfReader` 读取PDF文件。
            - 创建一个新的 `PdfWriter` 对象。
            - 将原始PDF文件的每一页添加到新的PDF writer对象中。
            - 直接将新构建的PDF内容写入原始文件路径，覆盖原有的PDF文件。
            - 如果成功修复，记录日志并打印成功信息。
            - 如果修复过程中出现异常，记录错误日志并打印失败信息。
        - 所有PDF文件修复完成后，打印修复结束信息。


        Parameters
        ----------
        project_name : str
            项目名称,用于排除特定名称的PDF文件
        root_dir : str
            要扫描的根目录
        excluded_folder : str
            要排除的文件夹名称
        """
        # 将根目录转换为Path对象
        root_dir = Path(root_dir)
        # 遍历根目录下的所有文件和文件夹
        pdf_files = [
            path for path in root_dir.rglob('*.pdf')  # 遍历根目录及其所有子目录中的所有以 '.pdf' 结尾的文件
            if '.git' not in path.parts  # 排除路径中包含 '.git' 的文件
            and '.github' not in path.parts  # 排除路径中包含 '.github' 的文件
            and path.is_file()  # 确保路径是一个文件
            and path.name != f'{project_name}.pdf'  # 排除与项目名称相同的 PDF 文件
            and path.parent.name != excluded_folder  # 排除指定的 excluded_folder 文件夹中的 PDF 文件
        ]

        if not pdf_files:
            print(_("当前路径下没有 PDF 文件"))
            return

        print(_("找到 PDF 文件数目: ") + f"[bold cyan]{len(pdf_files)}[/bold cyan]")
        for pdf_file in pdf_files:
            try:
                # 读取并写入 PDF
                reader = PdfReader(pdf_file)
                writer = PdfWriter()

                for page in reader.pages:
                    writer.add_page(page)

                # 直接写入到原始文件以覆盖它
                with open(pdf_file, 'wb') as f:
                    writer.write(f)

                self.logger.info(_("修复成功: ") + str(pdf_file))
            except Exception as e:
                self.logger.error(_("修复失败: ") + f"{pdf_file} --> {e}")
        print(_("[bold green]修复 PDF 结束[/bold green]"))


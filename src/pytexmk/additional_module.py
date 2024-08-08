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
LastEditTime : 2024-08-08 10:42:58 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /PyTeXMK/src/pytexmk/additional_module.py
Description  : 
 -----------------------------------------------------------------------
'''
# -*- coding: utf-8 -*-
import re
import sys
import fitz
import shutil
import logging
import webbrowser
from rich import print
from pathlib import Path

from .language import lang_additional
from .language_module import check_language

lang = check_language()
if lang:
    mrc_lang = lang_additional.mrc_lang_zh
    mfj_lang = lang_additional.mfj_lang_zh
    pfo_lang = lang_additional.pfo_lang_zh
    exit_lang = lang_additional.exit_lang_zh
else:
    mrc_lang = lang_additional.mrc_lang_en
    mfj_lang = lang_additional.mfj_lang_en
    pfo_lang = lang_additional.pfo_lang_en
    exit_lang = lang_additional.exit_lang_en

class MoveRemoveClean(object):

    def __init__(self):
        self.logger = logging.getLogger(__name__)


    # --------------------------------------------------------------------------------
    # 将指定文件从文件夹中清除
    # --------------------------------------------------------------------------------
    def remove_specific_files(self, files, folder):
        """
        删除指定文件。

        参数:
        - files: 要删除的具体文件名列表。
        - folder: 要删除文件的目录路径。

        行为:
        - 遍历files列表，直接删除folder目录中的该文件。
        - 删除成功或失败时，会通过logger记录相应的信息。
        """
        folder_path = Path(folder)  # 将folder转换为Path对象
        for file in files:
            filepath = folder_path / file  # 使用Path对象的/操作符构建路径
            if filepath.exists():
                try:
                    filepath.unlink()  # 使用unlink删除文件
                    self.logger.info(f"{mrc_lang['del-success']}: {filepath}")
                except OSError as e:
                    self.logger.error(f"{mrc_lang['del-failed']}: {filepath} --> {e}")


    # --------------------------------------------------------------------------------
    # 将正则表达式匹配的文件从文件夹中清除
    # --------------------------------------------------------------------------------
    def remove_matched_files(self, patterns, folder):
        """
        删除匹配正则表达式的文件。

        参数:
        - patterns: 要删除的正则表达式模式列表。
        - folder: 要删除文件的目录路径。

        行为:
        - 遍历patterns列表，编译正则表达式，匹配并删除folder目录及其子目录中所有匹配的文件。
        - 在删除文件时，会跳过包含".git"或".github"的目录。
        - 删除成功或失败时，会通过logger记录相应的信息。
        """
        folder_path = Path(folder)  # 将folder转换为Path对象
        for pattern in patterns:
            compiled_pattern = re.compile(pattern)
            for filepath in folder_path.rglob("*"):  # 使用rglob递归遍历所有文件
                if '.git' in filepath.parts or '.github' in filepath.parts:
                    continue  # 跳过这些文件夹
                if filepath.is_file() and compiled_pattern.match(filepath.name):
                    try:
                        filepath.unlink()  # 使用unlink删除文件
                        self.logger.info(f"{mrc_lang['del-success']}: {filepath}")
                    except OSError as e:
                        self.logger.error(f"{mrc_lang['del-failed']}: {filepath} --> {e}")


    # --------------------------------------------------------------------------------
    # 将指定文件从根目录移动到目标文件夹，如果目标文件存在则覆盖
    # --------------------------------------------------------------------------------
    def move_specific_files(self, files, src_folder, dest_folder):
        """
        将指定文件从源文件夹移动到目标文件夹。
     
        参数:
        - files: 需要移动的文件列表。
        - src_folder: 源文件夹路径。
        - dest_folder: 目标文件夹路径。
     
        行为:
        - 检查源文件夹和目标文件夹是否存在。
        - 遍历文件列表，检查每个文件是否存在于源文件夹中。
        - 如果文件已存在于目标文件夹中，则尝试删除该文件。
        - 尝试将文件从源文件夹移动到目标文件夹。
        - 记录移动成功或失败的信息。
        """
        src_folder_path = Path(src_folder)
        dest_folder_path = Path(dest_folder)

        if not src_folder_path.exists():
            return

        if not dest_folder_path.exists():
            dest_folder_path.mkdir(parents=True)  # 如果目标文件夹不存在，则创建它

        for file in files:
            src_file_path = src_folder_path / file
            dest_file_path = dest_folder_path / file

            if dest_file_path.exists():
                try:
                    dest_file_path.unlink()
                except OSError as e:
                    self.logger.error(f"{mrc_lang['del-failed']}: {dest_file_path} --> {e}")
                    continue

            if src_file_path.exists():
                try:
                    shutil.move(str(src_file_path), str(dest_file_path))
                    self.logger.info(f"{mrc_lang['move-success']}: {src_file_path} ==> {dest_folder}")
                except OSError as e:
                    self.logger.error(f"{mrc_lang['move-failed']}: {src_file_path} ==> {dest_folder} --> {e}")


    # --------------------------------------------------------------------------------
    # 将正则表达式匹配的文件从根目录移动到目标文件夹，如果目标文件存在则覆盖
    # --------------------------------------------------------------------------------
    def move_matched_files(self, patterns, src_folder, dest_folder):
        """
        将匹配正则表达式模式的文件从源文件夹移动到目标文件夹。
        如果目标文件夹不存在，则创建它。
        如果目标文件夹中已存在同名文件，则先删除旧文件。
        移动文件时，如果发生错误，则记录错误信息。

        参数:
        - patterns (list): 正则表达式模式列表。
        - src_folder (str): 源文件夹路径。
        - dest_folder (str): 目标文件夹路径。
        """
        src_folder_path = Path(src_folder)  # 将源文件夹路径转换为Path对象
        dest_folder_path = Path(dest_folder)  # 将目标文件夹路径转换为Path对象

        if not dest_folder_path.exists():  # 检查目标文件夹是否存在
            dest_folder_path.mkdir(parents=True)  # 如果目标文件夹不存在，则创建它

        for file_path in src_folder_path.iterdir():  # 遍历源文件夹中的所有文件
            if file_path.is_file():  # 确保是文件而不是文件夹
                for pattern in patterns:  # 遍历所有正则表达式模式
                    if re.match(pattern, file_path.name):  # 检查文件名是否匹配正则表达式模式
                        dest_file_path = dest_folder_path / file_path.name  # 构建目标文件路径

                        if dest_file_path.exists():  # 检查目标文件是否存在
                            try:
                                dest_file_path.unlink()  # 删除目标文件
                            except OSError as e:
                                self.logger.error(f"{mrc_lang['del-failed']}: {dest_file_path} --> {e}")  # 记录删除失败错误信息
                                continue  # 跳过当前文件的移动操作

                        try:
                            shutil.move(str(file_path), str(dest_folder_path))  # 移动文件
                            self.logger.info(f"{mrc_lang['move-success']}: {file_path.name} ==> {dest_folder}")  # 记录文件移动成功信息
                        except OSError as e:
                            self.logger.error(f"{mrc_lang['move-failed']}: {file_path.name} ==> {dest_folder} --> {e}")  # 记录文件移动失败错误信息
                        break  # 匹配到一个模式后，不再检查其他模式



class MainFileJudgment(object):

    def __init__(self):
        self.logger = logging.getLogger(__name__)


    # --------------------------------------------------------------------------------
    # 定义输入检查函数
    # --------------------------------------------------------------------------------
    def check_project_name(self, main_tex_files, check_project_name, suffixes):
        # 使用Path对象处理文件路径
        path_obj = Path(check_project_name)
        base_name = path_obj.stem  # 提取文件名（不包括后缀）
        file_extension = path_obj.suffix  # 提取文件后缀

        if '/' in check_project_name or '\\' in check_project_name:  # 判断是否是没有后缀的路径
            self.logger.error(mfj_lang['cannot-contain-path'])
            exit_pytexmk()
        if file_extension == f'{suffixes}':  # 判断后缀是否是 .tex
            if base_name in main_tex_files:  # 判断文件名是否在 main_tex_files 中
                return base_name
            else:
                self.logger.error(f"{mfj_lang['not-in-root']}: [bold cyan]{check_project_name}{file_extension}[/bold cyan]")
                exit_pytexmk()
        if '.' not in check_project_name:  # 判断输入 check_project_name 中没有 后缀
            if check_project_name in main_tex_files:  # 判断文件名是否在 main_tex_files 中
                return check_project_name
            else:
                self.logger.error(f"{mfj_lang['not-in-root']}: [bold cyan]{check_project_name}{suffixes}[/bold cyan]")
                exit_pytexmk()
        else:
            self.logger.error(f"{mfj_lang['file-not-tex']}: [bold cyan]{check_project_name}[/bold cyan]")
            exit_pytexmk()


    # --------------------------------------------------------------------------------
    # 定义 tex 文件检索函数
    # --------------------------------------------------------------------------------
    def get_suffixes_files_in_dir(self, dir, suffixes):
        suffixes_files_in_dir = []
        try:
            # 获取当前路径
            current_path = Path(dir)  # 转换为Path对象
            # 列出当前路径下所有以suffixes结尾的文件
            for file in current_path.glob(f'*{suffixes}'):
                # 去掉路径，提取文件名和后缀
                base_name = file.stem
                suffixes_files_in_dir.append(base_name)
                self.logger.info(f"{mfj_lang['search-result']}: {base_name}{suffixes}")

            if suffixes_files_in_dir:
                self.logger.info(f"{suffixes} {mfj_lang['file-num']}: {len(suffixes_files_in_dir)}")
            else:
                self.logger.error(f"{suffixes} {mfj_lang['path-error']}")
                self.logger.warning(f"{mfj_lang['terminal-path']}：{current_path}")
                exit_pytexmk()
        except Exception as e:
            self.logger.error(f"{mfj_lang['search-file-error']}: {suffixes} --> {e}")
        return suffixes_files_in_dir    


    # --------------------------------------------------------------------------------
    # 定义 tex 文件 \documentclass 和 \begin{document} 检索函数
    # --------------------------------------------------------------------------------
    def find_tex_commands(self, tex_files_in_root):
        # 初始化主文件列表
        main_tex_files = []
        # 遍历传入的文件名列表
        for file_name in tex_files_in_root:
            try:
                # 使用Path对象打开文件
                with open(Path(file_name).with_suffix('.tex'), 'r', encoding='utf-8') as file:
                    is_main_file = False
                    # 读取前200行
                    for _ in range(200):
                        line = file.readline()
                        # 跳过注释行
                        if line.strip().startswith('%'):
                            continue
                        # 检查是否包含主文件特征命令
                        if r"\documentclass" in line or r"\begin{document}" in line:
                            is_main_file = True
                    # 如果找到主文件特征命令，则将文件名添加到主文件列表中
                    if is_main_file:
                        main_tex_files.append(file_name)
                    self.logger.info(f"{mfj_lang['search-file-feature']}: {file_name}")
            except Exception as e:
                # 捕获并记录文件读取错误
                self.logger.error(f"{mfj_lang['read-file-error']}: {file_name}.tex --> {e}")
                continue
        # 如果有找到主文件，则记录数量
        if main_tex_files:
            self.logger.info(f"{mfj_lang['find-main-file-num']}: {len(main_tex_files)}")
        else:
            # 如果没有找到主文件，则记录错误并退出程序
            self.logger.error(mfj_lang['terminal-path-error'])
            self.logger.warning(f"{mfj_lang['terminal-path']}：{Path.cwd()}")
            exit_pytexmk()
        # 返回主文件列表
        return main_tex_files


    # --------------------------------------------------------------------------------
    # 定义魔法注释检索函数 
    # --------------------------------------------------------------------------------
    def search_magic_comments(self, main_file_in_root, magic_comment_keys):  # 搜索TeX文件中的魔法注释
        """
        搜索指定TeX文件中的魔法注释。

        参数:
        - main_file_in_root (list): 包含TeX文件路径的列表。
        - magic_comment_keys (list): 包含魔法注释关键字的列表。

        返回:
        - dict: 包含所有魔法注释的字典，格式为{magic_comment_key: [(file_path, magic_comment_value),...],...}。

        行为逻辑:
        1. 遍历TeX文件列表，打开每个文件并读取前50行。
        2. 使用正则表达式匹配魔法注释关键字。
        3. 如果匹配到魔法注释，将其存储在字典中。
        4. 将数据结构从{file_path: {magic_comment_key: magic_comment_value},...}转换为{magic_comment_key: [(file_path, magic_comment_value),...],...}。
        5. 返回包含所有魔法注释的字典。
        """
        file_magic_comments = {}  # 用于存储每个文件的魔法注释

        for file_path in main_file_in_root:  # 遍历TeX文件列表
            try:
                file_path_obj = Path(file_path).with_suffix('.tex')  # 使用pathlib创建文件路径对象
                with file_path_obj.open('r', encoding='utf-8') as file:  # 使用pathlib打开文件
                    for line_number, line_content in enumerate(file, start=1):  # 遍历文件的前50行
                        if line_number > 50:  # 只处理前50行
                            break
                        for magic_comment_key in magic_comment_keys:  # 遍历关键字列表
                            # 使用正则表达式匹配魔法注释
                            match_result = re.search(rf'%(?:\s*)!TEX {re.escape(magic_comment_key)}(?:\s*)=(?:\s*)(.*?)(?=\s|%|$)', line_content, re.IGNORECASE)
                            if match_result:  # 如果匹配到魔法注释
                                matched_comment_value = match_result.group(1).strip()  # 提取对应的值
                                if file_path not in file_magic_comments:  # 如果文件路径不在字典中
                                    file_magic_comments[file_path] = {}
                                file_magic_comments[file_path][magic_comment_key] = matched_comment_value  # 存储魔法注释
                                break  # 跳出当前循环，避免重复匹配同一关键字
            except Exception as e:
                self.logger.error(f"{mfj_lang['read-file-error']}: {file_path} --> {e}")
                continue  # 跳过当前文件，继续处理下一个文件

        # 将数据结构从{file_path: {magic_comment_key: magic_comment_value},...}转换为{magic_comment_key: [(file_path, magic_comment_value),...],...}
        all_magic_comments = {}
        for file_path, comments in file_magic_comments.items():  # 遍历文件魔法注释字典
            for key, value in comments.items():  # 遍历每个文件的魔法注释
                if key not in all_magic_comments:  # 如果关键字不在字典中
                    all_magic_comments[key] = []
                all_magic_comments[key].append((file_path, value))  # 存储文件路径和魔法注释值
        return all_magic_comments  # 返回提取的键值对字典



class PdfFileOperation(object):

    def __init__(self):
        self.logger = logging.getLogger(__name__)


    # --------------------------------------------------------------------------------
    # 定义 PDF 文件预览函数
    # --------------------------------------------------------------------------------
    def pdf_preview(self, project_name, outdir):
        try:
            pdf_name = f"{project_name}.pdf"
            # 使用 pathlib 拼接 pdf 文件路径
            pdf_path = Path(outdir) / pdf_name
            print(f"[bold green]{pfo_lang['file-openning']} {pdf_name}")
            # 使用 pathlib 获取 pdf 文件的绝对路径
            local_path = f"file://{pdf_path.resolve().as_posix()}"
            self.logger.info(f'{pfo_lang['file-path']}: {local_path}')
            # 使用 webbrowser 打开 pdf 文件
            webbrowser.open(local_path)
        except Exception as e:
            # 记录打开 README 文件时的错误信息
            self.logger.error(f"{pfo_lang['file-open-error']}: {pdf_name} -->{e}")
        finally:
            # 打印退出信息并退出程序
            exit_pytexmk()


    # --------------------------------------------------------------------------------
    # 定义 PDF 文件修复函数
    # --------------------------------------------------------------------------------
    def pdf_repair(self, project_name, root_dir, excluded_folder):
        """
        清理指定目录下的PDF文件，排除特定文件夹中的文件，并对每个PDF文件进行修复操作。
          
        参数:
        - project_name: 项目名称，用于排除特定名称的PDF文件。
        - root_dir: 要扫描的根目录。
        - excluded_folder: 要排除的文件夹名称。
          
        功能:
        - 遍历指定目录，收集所有子文件夹中的PDF文件路径，排除根目录和特定文件夹中的文件。
        - 对每个PDF文件进行打开和关闭操作，以修复可能存在的文件未正确关闭的问题。
        - 记录处理过程中的错误信息，并显示处理失败的文件名称。
        """
        # 将根目录转换为Path对象
        root_dir = Path(root_dir)
        pdf_files = []
        # 遍历根目录下的所有文件和文件夹
        for path in root_dir.rglob('*'):
            # 跳过.git和.github文件夹
            if '.git' in path.parts or '.github' in path.parts:
                continue
            # 跳过根目录和排除的文件夹
            if path.is_dir() and path.name == excluded_folder:
                continue
            # 仅处理子文件夹中的PDF文件，并排除特定名称的PDF文件
            if path.is_file() and path.suffix == '.pdf' and path.name != f'{project_name}.pdf':
                pdf_files.append(path)
 
        if not pdf_files:
            print(pfo_lang['pdf-not-found'])
            return
 
        print(f"{pfo_lang['pdf-found-num']}: [bold cyan]{len(pdf_files)}[/bold cyan]")
        for pdf_file in pdf_files:
            try:
                # 使用fitz库打开PDF文件
                with fitz.open(pdf_file) as doc:
                    # 生成临时文件路径
                    temp_path = pdf_file.with_suffix('.pdf.temp')
                    # 保存修复后的PDF文件到临时路径
                    doc.save(temp_path, garbage=3, deflate=True, clean=True)
                # 覆盖原有文件
                temp_path.replace(pdf_file)
                self.logger.info(f"{pfo_lang['repair-success']}: {pdf_file}")
            except Exception as e:
                self.logger.error(f"{pfo_lang['repair-failed']}: {pdf_file} --> {e}")
        print(f"[bold green]{pfo_lang['repair-finished']}[/bold green]")



# --------------------------------------------------------------------------------
# 定义 PyTeXMK 退出函数
# --------------------------------------------------------------------------------
def exit_pytexmk():
    print(f'[bold red]{exit_lang["exiting"]}[/bold red]')
    sys.exit() # 退出程序
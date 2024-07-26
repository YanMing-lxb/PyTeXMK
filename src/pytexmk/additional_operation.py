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
LastEditTime : 2024-07-26 19:17:18 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : \PyTeXMK\src\pytexmk\additional_operation.py
Description  : 
 -----------------------------------------------------------------------
'''
# -*- coding: utf-8 -*-
import os
import re
import sys
import fitz
import shutil
import logging
from rich import print
class MoveRemoveClean(object):

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    # --------------------------------------------------------------------------------
    # 将文件从文件夹中清除
    # --------------------------------------------------------------------------------
def remove_files(self, files, folder):
    for file in files:
        # 如果是正则表达式模式，则编译正则表达式
        if file.startswith(".*"):
            pattern = re.compile(file)
            for root, _, filenames in os.walk(folder):
                for filename in filenames:
                    if pattern.match(filename):
                        file_path = os.path.join(root, filename)
                        try:
                            os.remove(file_path)
                            self.logger.info(f"{folder} 中 {filename} 删除成功")
                        except OSError as e:
                            self.logger.error(f"{folder} 中 {filename} 删除失败: {e}")
        else:
            file_path = os.path.join(folder, file)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    self.logger.info(f"{folder} 中 {file} 删除成功")
                except OSError as e:
                    self.logger.error(f"{folder} 中 {file} 删除失败: {e}")


    # --------------------------------------------------------------------------------
    # 将文件从源文件夹移动到根目录，如果根目录存在同名文件则覆盖
    # --------------------------------------------------------------------------------
    def move_to_root(self, files, src_folder):
        """
        将指定文件从源文件夹移动到当前工作目录的根目录。
    
        参数:
        - files: 需要移动的文件列表。
        - src_folder: 源文件夹路径。
    
        行为:
        - 检查源文件夹是否存在。
        - 遍历文件列表，检查每个文件是否存在于源文件夹中。
        - 如果文件已存在于当前工作目录中，则尝试删除该文件。
        - 尝试将文件从源文件夹移动到当前工作目录。
        - 记录移动成功或失败的信息。
        """
        if not os.path.exists(src_folder):
            self.logger.error(f"源文件夹 {src_folder} 不存在")
            return

        for file in files:
            src_file_path = os.path.join(src_folder, file)
            dest_file_path = os.path.join(os.getcwd(), file)
            if os.path.exists(dest_file_path):
                try:
                    os.remove(dest_file_path)
                except OSError as e:
                    self.logger.error(f"{dest_file_path} 未能删除: {e}")
                    continue
            if os.path.exists(src_file_path):
                try:
                    shutil.move(src_file_path, dest_file_path)
                    self.logger.info(f"{src_folder} 中 {file} 移动到 {os.getcwd()}")
                except OSError as e:
                    self.logger.error(f"{src_folder} 中 {file} 移动到 {os.getcwd()} 失败: {e}")


    # --------------------------------------------------------------------------------
    # 将文件从根目录移动到目标文件夹，如果目标文件存在则覆盖
    # --------------------------------------------------------------------------------
    def move_to_folder(self, files, dest_folder):
        """
        将文件列表中的文件移动到指定文件夹。
        如果目标文件夹不存在，则创建它。
        如果目标文件夹中已存在同名文件，则先删除旧文件。
        移动文件时，如果发生错误，则记录错误信息。
    
        参数:
        files (list): 要移动的文件列表。
        dest_folder (str): 目标文件夹路径。
        """
        if not os.path.exists(dest_folder):
            os.makedirs(dest_folder)
    
        for file in files:
            dest_file = os.path.join(dest_folder, file)
    
            if os.path.exists(dest_file):
                try:
                    os.remove(dest_file)
                except OSError as e:
                    self.logger.error(f"{dest_folder} 中旧 {file} 删除失败: {e}")
                    continue # 跳过当前文件的移动操作
            if os.path.exists(file):  # 确保源文件存在
                try:
                    shutil.move(file, dest_folder)
                    self.logger.info(f"{file} 移动到 {dest_folder}")
                except OSError as e:
                    self.logger.error(f"{file} 移动到 {dest_folder} 失败: {e}")


    # --------------------------------------------------------------------------------
    # 定义清理所有 pdf 文件
    # --------------------------------------------------------------------------------
    def clean_pdf(self, project_name, root_dir, excluded_folder):
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
        pdf_files = []
        for root, dirs, files in os.walk(root_dir):
            if excluded_folder in dirs:
                dirs.remove(excluded_folder)  # 不包括名为excluded_folder的文件夹中的pdf文件
            if root == root_dir:  # 如果当前处理的是根目录文件，则跳过
                continue
            for file in files:
                if file.endswith('.pdf') and file != f'{project_name}.pdf':
                    pdf_files.append(os.path.join(root, file))  # 仅清理子文件夹中的pdf文件

        if not pdf_files:
            print("当前路径下未发现PDF文件。")
            return

        print(f"共发现 {len(pdf_files)} 个PDF文件。")
        for pdf_file in pdf_files:
            try:
                with fitz.open(pdf_file) as doc:
                    temp_path = pdf_file + ".temp"
                    doc.save(temp_path, garbage=3, deflate=True, clean=True)
                os.replace(temp_path, pdf_file)  # 覆盖原有文件
                self.logger.info(f"已处理并覆盖文件 {pdf_file}")
            except Exception as e:
                self.logger.error(f"处理出错文件 {pdf_file}: {e}")
        print("所有PDF文件已处理完成。")




class MainFileJudgment(object):

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    # --------------------------------------------------------------------------------
    # 定义输入检查函数
    # --------------------------------------------------------------------------------
    def check_project_name(self, check_project_name):
        # 检查并处理项目名称，返回处理后的项目名称或None
        base_name, file_extension = os.path.splitext(os.path.basename(check_project_name))  # 去掉路径，提取文件名和后缀

        tex_files = self.search_tex_file()  # 检查并获取根目录下所有 .tex 文件
        if '/' in check_project_name or '\\' in check_project_name:  # 判断是否是没有后缀的路径
            self.logger.error("输入文件名中不能包含路径")
            sys.exit(1)
        elif file_extension == '.tex':  # 判断后缀是否是 .tex
            if check_project_name in tex_files:  # 判断文件名是否在 tex_files 中
                return base_name
            else:
                self.logger.error("输入文件名不存在于当前目录下")
                sys.exit(1)
        elif '.' not in check_project_name:  # 判断输入 check_project_name 中没有 后缀
            if f'{check_project_name}.tex' in tex_files:  # 判断文件名是否在 tex_files 中
                return check_project_name
            else:
                self.logger.error("输入文件名不存在于当前目录下")
                sys.exit(1)
        else:
            self.logger.error("输入文件后缀不是.tex")
            sys.exit(1)


    # --------------------------------------------------------------------------------
    # 定义 tex 文件检索函数
    # --------------------------------------------------------------------------------
    def search_tex_file(self):
        try:
            # 获取当前路径并列出所有以.tex结尾的文件
            return [file for file in os.listdir(os.getcwd()) if file.endswith('.tex')]
        except Exception as e:
            self.logger.error(f"搜索TeX文件时出错: {e}")
            return []


    # --------------------------------------------------------------------------------
    # 定义 tex 主文件检索函数
    # -------------------------------------------------------------------------------- 
    def search_main_file(self, tex_files):
        """
        搜索并确定主 .tex 文件的函数
        参数:
        - tex_files: 当前目录下的所有 .tex 文件列表
        返回值:
        - project_name: 确定的主文件名（不包含 .tex 扩展名），如果未找到则返回 None
        """
     
        current_path = os.getcwd()  # 获取当前路径
        
        if not tex_files:
            self.logger.error("终端路径下不存在 .tex 文件！请检查终端显示路径是否是项目路径")
            self.logger.warning(f"当前终端路径是：{current_path}")
            sys.exit(1)
     
        if 'main.tex' in tex_files:
            project_name = 'main'
            print(f"通过默认文件名确认主文件为 {project_name}.tex")
        elif len(tex_files) == 1:
            project_name = os.path.splitext(tex_files[0])[0]
            print(f"通过唯一 TeX 文件名确认主文件为 {project_name}.tex")
        else:
            main_tex_files = []
            for file_name in tex_files:
                try:
                    with open(file_name, 'r', encoding='utf-8') as file:
                        for _ in range(200):
                            line = file.readline()
                            if line.strip().startswith('%'):
                                continue
                            if "\documentclass" in line or r"\begin{document}" in line:
                                main_tex_files.append(file_name)
                except Exception as e:
                    self.logger.error(f"读取文件 {file_name} 时出错: {e}")
                    continue
            if len(main_tex_files) == 1:
                project_name = self.check_project_name(file_name)
                print(f"通过 \\documentclass 或 \\begin{{document}} 命令确认主文件为 {project_name}.tex")
            else:  # 存在多个主文件
                self.logger.error("多个文件中存在 \\documentclass 或 \\begin{{document}} 命令")
                self.logger.warning("请修改主文件名为 main.tex 或在文件中加入魔法注释 “% !TEX root = <主文件名>” 或在终端输入 pytexmk <主文件名> 名进行编译")
                self.logger.warning("主文件一定要放在项目根目录下")
                sys.exit(1)

        return project_name


    # --------------------------------------------------------------------------------
    # 定义魔法注释检索函数 
    # --------------------------------------------------------------------------------
    def search_magic_comments(self, tex_file_list, magic_comment_keys):  # 搜索TeX文件中的魔法注释 # TODO 代码待测试
        extracted_magic_comments = {}  # 创建空字典用于存储结果 # TODO tex_file_list 是当前根目录下的所有.tex 文件列表，而不包括子文件夹中的tex文件，需要调整代码逻辑
        file_magic_comments = {}  # 用于存储每个文件的魔法注释

        for file_path in tex_file_list:  # 遍历TeX文件列表
            try:
                with open(file_path, 'r', encoding='utf-8') as file:  # 打开文件
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
                                self.logger.info(f"文件 {file_path} 第 {line_number} 行找到魔法注释: % !TEX {magic_comment_key} = {matched_comment_value}")
                                break  # 跳出当前循环，避免重复匹配同一关键字
            except Exception as e:
                self.logger.error(f"读取文件 {file_path} 时出错: {e}")
                continue  # 跳过当前文件，继续处理下一个文件

        # 检查重复魔法注释
        all_extracted_comments = {}
        for file_path, comments in file_magic_comments.items():  # 遍历文件魔法注释字典
            for key, value in comments.items():  # 遍历每个文件的魔法注释
                if key not in all_extracted_comments:  # 如果关键字不在字典中
                    all_extracted_comments[key] = []
                all_extracted_comments[key].append((file_path, value))  # 存储文件路径和魔法注释值

        for key, values in all_extracted_comments.items():  # 遍历所有提取的魔法注释
            if len(values) > 1:  # 如果魔法注释在多个文件中重复
                first_file_info = values[0]
                self.logger.warning(f"魔法注释 {key} 在多个文件中重复，以检索到的第一个文件 {first_file_info[0]} 为准: {first_file_info[1]}")
                extracted_magic_comments[key] = first_file_info[1]  # 存储第一个文件的魔法注释
            else:  # 如果魔法注释没有重复
                extracted_magic_comments[key] = values[0][1]  # 存储魔法注释

        return extracted_magic_comments  # 返回提取的键值对字典

    
# 检查 pytexmk 在是否存在更新，并提示用户更新

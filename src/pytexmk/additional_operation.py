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
LastEditTime : 2024-07-24 20:40:43 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : \PyTeXMK\src\pytexmk\additional_operation.py
Description  : 
 -----------------------------------------------------------------------
'''
# -*- coding: utf-8 -*-
import os
import re
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
            if os.path.exists(os.path.join(folder, file)):
                try:
                    os.remove(os.path.join(folder, file))
                    self.logger.info(f"{folder} 中 {file} 删除成功")
                except OSError:
                    self.logger.error(f"{folder} 中 {file} 删除失败")

    # --------------------------------------------------------------------------------
    # 将文件从源文件夹移动到根目录，如果根目录存在同名文件则覆盖
    # --------------------------------------------------------------------------------
    def move_to_root(self, files, src_floder):
        if os.path.exists(src_floder):
            for file in files:
                if os.path.exists(os.path.join(src_floder, file)):
                    if os.path.exists(os.path.join(os.getcwd(), file)):
                        try:
                            os.remove(os.path.join(os.getcwd(), file))
                        except OSError:
                            self.logger.error(f"{os.path.join(os.getcwd(), file)} 未能删除")
                    try:
                        shutil.move(os.path.join(src_floder, file), os.path.join(os.getcwd(), file))
                        self.logger.info(f"{src_floder} 中 {file} 移动到 {os.getcwd()}")
                    except OSError:
                        self.logger.error(f"{src_floder} 中 {file} 移动到 {os.getcwd()} 失败")

    # --------------------------------------------------------------------------------
    # 将文件从根目录移动到目标文件夹，如果目标文件存在则覆盖
    # --------------------------------------------------------------------------------
    def move_to_folder(self, files, dest_folder):
        # 确保目标文件夹存在，如果不存在则创建
        if not os.path.exists(dest_folder):
            os.makedirs(dest_folder)

        for file in files:
            # 构建目标文件的完整路径
            dest_file = os.path.join(dest_folder, os.path.basename(file))

            # 如果目标文件存在，则删除它
            if os.path.exists(dest_file):
                try:
                    os.remove(dest_file)
                except OSError:
                    self.logger.error(f"{dest_folder} 中旧 {file} 删除失败")
                
            # 移动文件
            try:
                shutil.move(file, dest_folder)
                self.logger.info(f"{file} 移动到 {dest_folder}")
            except shutil.Error:
                self.logger.error(f"{file} 移动到 {dest_folder} 失败")
            except FileNotFoundError:
                pass

    # --------------------------------------------------------------------------------
    # 定义清理所有 pdf 文件
    # --------------------------------------------------------------------------------
    def clean_pdf(self, project_name, root_dir, excluded_folder): # TODO 更换功能名称为Repair PDF
        pdf_files = []
        for root, dirs, files in os.walk(root_dir):
            if excluded_folder in dirs:
                dirs.remove(excluded_folder)  # 不包括名为excluded_folder的文件夹中的pdf文件
            if root == root_dir: # 如果当前处理的是根目录文件，则跳过
                continue 
            for file in files:
                if file.endswith('.pdf') and file != f'{project_name}.pdf':
                    pdf_files.append(os.path.join(root, file))  # 仅清理子文件夹中的pdf文件
        
        # 对pdf文件进行打开和关闭操作，解决origin批量导出pdf文件时由于未关闭pdf导致的报错
        if pdf_files: # TODO 显示处理失败的文件名称
            print(f"共发现 {len(pdf_files)} 个PDF文件。")
            for pdf_file in pdf_files:
                try:
                    doc = fitz.open(pdf_file)
                    temp_path = pdf_file + ".temp"
                    doc.save(temp_path, garbage=3, deflate=True, clean=True)
                    doc.close()
                    os.replace(temp_path, pdf_file)  # 覆盖原有文件
                    self.logger.info(f"已处理并覆盖: {pdf_file}")
                except Exception as e:
                    self.logger.error(f"处理出错 {pdf_file}: {e}")
            print("所有PDF文件已处理完成。")
        else:
            print("当前路径下未发现PDF文件。")

class MainFileJudgment(object):

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    # --------------------------------------------------------------------------------
    # 定义输入检查函数
    # --------------------------------------------------------------------------------
    def check_project_name(self, check_project_name):
        base_name, file_extension = os.path.splitext(
            os.path.basename(check_project_name))  # 去掉路径，提取文件名和后缀
        if file_extension == '.tex':  # 判断后缀是否是 .tex
            project_name_return = base_name
        elif '.' not in check_project_name:  # 判断输入 check_project_name 中没有 后缀
            if '/' in check_project_name or '\\' in check_project_name:  # 判断是否是没有后缀的路径
                project_name_return = None
                self.logger.warning("输入文件路径无效")
            else:
                project_name_return = check_project_name
        else:
            project_name_return = None
            self.logger.warning("输入文件后缀不是.tex")

        return project_name_return

    # --------------------------------------------------------------------------------
    # 定义 tex 文件检索函数
    # --------------------------------------------------------------------------------
    def search_tex_file(self):
        current_path = os.getcwd() # 获取当前路径
        # 遍历当前路径下的所有文件
        tex_files = [file for file in os.listdir(current_path) if file.endswith('.tex')]
        return tex_files

    # --------------------------------------------------------------------------------
    # 定义 tex 主文件检索函数
    # -------------------------------------------------------------------------------- 
    def search_main_file(self, tex_files):
        current_path = os.getcwd() # 获取当前路径
        if tex_files:
            # 如果存在多个.tex文件
            if 'main.tex' in tex_files:
                # 存在名为 main.tex的文件
                project_name = 'main'
                print(f"通过默认文件名确认主文件为 {project_name}.tex")
            # 如果只有一个.tex文件，则直接提取文件名并打印
            elif len(tex_files) == 1:
                project_name = os.path.splitext(tex_files[0])[0]
                print(f"通过唯一 TeX 文件名确认主文件为 {project_name}.tex")
            elif len(tex_files) > 1:
                # 存在多个.tex文件，但没有名为main.tex的文件
                for file_path in tex_files:  # 遍历tex文件列表
                    with open(file_path, 'r', encoding='utf-8') as file:  # 打开文件
                        for _ in range(200):  # 遍历文件的前200行
                            line = file.readline()  # 读取一行内容
                            if line.strip().startswith('%'):  # 如果是以 % 开头的行则跳过
                                continue
                            if ("\documentclass" in line or r"\begin{document}" in line):
                                # 找到 \documentclass 或 \begin{document} 指令，提取文件名
                                project_name = self.check_project_name(file_path)
                                print(f"通过 \documentclass 或 \\begin{{document}} 命令确认主文件为 {project_name}.tex")
                                break
            else:
                # 不存在名为main.tex的文件，打印所有找到的.tex文件
                project_name = None
                self.logger.warning("存在多个 .tex 文件，请：修改主文件名为 main.tex 或在文件中加入魔法注释 “% !TEX = <主文件名>” 或在终端输入：pytexmk <主文件名> 名进行编译")
                self.logger.warning("[bold][red]注意：主文件名一定要放在项目根目录下[/red][/bold]")
        else:
            # 不存在.tex文件，打印当前路径并提示
            project_name = None
            self.logger.warning("终端路径下不存在 .tex 文件！请检查终端显示路径是否是项目路径")
            self.logger.warning(f"当前终端路径是：{current_path}")

        return project_name

    # --------------------------------------------------------------------------------
    # 定义魔法注释检索函数 
    # --------------------------------------------------------------------------------
    def search_magic_comments(self, tex_file_list, magic_comment_keys):  # 搜索TeX文件中的魔法注释 # TODO 需要测试这段代码
        extracted_magic_comments = {}  # 创建空字典用于存储结果
        file_magic_comments = {}  # 用于存储每个文件的魔法注释
        if len(tex_file_list):  # 检查TeX文件列表是否为空
            for file_path in tex_file_list:  # 遍历TeX文件列表
                with open(file_path, 'r', encoding='utf-8') as file:  # 打开文件
                    for line_number in range(50):  # 遍历文件的前50行
                        line_content = file.readline()  # 读取一行内容
                        if not line_content:  # 如果行内容为空
                            self.logger.warring(f"文件 {file_path} 前 50 行内容为空")
                            break  # 跳出循环
                        for magic_comment_key in magic_comment_keys:  # 遍历关键字列表
                            # 使用正则表达式匹配魔法注释
                            match_result = re.search(rf'%(?:\s*)!TEX {re.escape(magic_comment_key)}(?:\s*)=(?:\s*)(.*?)(?=\s|%|$)', line_content, re.IGNORECASE)
                            if match_result:  # 如果匹配到魔法注释
                                matched_comment_value = match_result.group(1).strip()  # 提取对应的值
                                if file_path not in file_magic_comments:  # 如果文件路径不在字典中
                                    file_magic_comments[file_path] = {}
                                file_magic_comments[file_path][magic_comment_key] = matched_comment_value  # 存储魔法注释
                                self.logger.info(f"文件 {file_path} 第 {line_number+1} 行找到魔法注释: % !TEX {magic_comment_key} = {matched_comment_value}")
                                break  # 跳出当前循环，避免重复匹配同一关键字
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

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
LastEditTime : 2024-07-19 20:20:43 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : \PyTeXMK\src\pytexmk\additional_operation.py
Description  : 
 -----------------------------------------------------------------------
'''
# -*- coding: utf-8 -*-
import os
import fitz
import shutil
from rich import print
class MoveRemoveClean(object):

    # --------------------------------------------------------------------------------
    # 将文件从文件夹中清除
    # --------------------------------------------------------------------------------
    def remove_files(self, files, folder):
        for file in files:
            if os.path.exists(os.path.join(folder, file)):
                try:
                    os.remove(os.path.join(folder, file))
                    print(f"{folder} 中的 {file} 被删除")
                except OSError:
                    print(f"{folder} 中的 {file} 未能被删除")

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
                            print(f"{os.path.join(os.getcwd(), file)} 未能删除")
                    shutil.move(os.path.join(src_floder, file), os.path.join(os.getcwd(), file))
                    print(f"{src_floder} 中 {file} 移动到 {os.getcwd()}")

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
                    print(f"{dest_folder} 中旧 {file} 未能被删除！")
                
            # 移动文件
            try:
                shutil.move(file, dest_folder)
                print(f"{file} 移动到 {dest_folder}")
            except shutil.Error:
                print(f"{file} 未能移动到 {dest_folder}")
            except FileNotFoundError:
                pass

    # --------------------------------------------------------------------------------
    # 定义清理所有 pdf 文件
    # --------------------------------------------------------------------------------
    def clean_pdf(self, root_dir, excluded_folder):
        pdf_files = []
        for root, dirs, files in os.walk(root_dir):
            if excluded_folder in dirs:
                dirs.remove(excluded_folder)  # 不包括名为excluded_folder的文件夹中的pdf文件
            if root == root_dir: # 如果当前处理的是根目录文件，则跳过
                continue 
            for file in files:
                if file.endswith('.pdf') and file != f'{self.project_name}.pdf':
                    pdf_files.append(os.path.join(root, file))  # 仅清理子文件夹中的pdf文件
        
        # 对pdf文件进行打开和关闭操作，解决origin批量导出pdf文件时由于未关闭pdf导致的报错
        if pdf_files:
            print(f"共发现 {len(pdf_files)} 个PDF文件。")
            for pdf_file in pdf_files:
                try:
                    doc = fitz.open(pdf_file)
                    doc.close()
                    print(f"已处理: {pdf_file}")
                except Exception as e:
                    print(f"处理出错 {pdf_file}: {e}")
            print("所有PDF文件已处理完成。")
        else:
            print("当前路径下未发现PDF文件。")



class MainFileJudgment(object):

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
                print("错误：文件路径无效！")
            else:
                project_name_return = check_project_name
        else:
            project_name_return = None
            print("提示：文件后缀不是.tex")

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
    # TODO: 解决魔法注释关键词大小写敏感问题
    def search_main_file(self, tex_files):
        current_path = os.getcwd() # 获取当前路径
        if tex_files:
            # 如果存在多个.tex文件
            if 'main.tex' in tex_files:
                # 存在名为main.tex的文件
                project_name = 'main'
                print(f"找到 {project_name}.tex 文件！")
            # 如果只有一个.tex文件，则直接提取文件名并打印
            elif len(tex_files) == 1:
                project_name = os.path.splitext(tex_files[0])[0]
                print(f"找到 {project_name}.tex 文件！")
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
                                print(f"通过 \documentclass 或 \\begin{{document}} 指令，找到 {project_name}.tex 文件！")
                                break
            else:
                # 不存在名为main.tex的文件，打印所有找到的.tex文件
                project_name = None
                print("存在多个 .tex 文件，请：修改主文件名为 main.tex 或在文件中加入魔法注释 “% !TEX = <主文件名>” 或在终端输入：pytexmk <主文件名> 名进行编译")
                print("[bold][red]注意：主文件名一定要放在项目根目录下[/red][/bold]")
        else:
            # 不存在.tex文件，打印当前路径并提示
            project_name = None
            print("终端路径下不存在 .tex 文件！请检查终端显示路径是否是项目路径")
            print(f"当前终端路径是：{current_path}")

        return project_name

    # --------------------------------------------------------------------------------
    # 定义魔法注释检索函数
    # --------------------------------------------------------------------------------
    def search_magic_comments(self, tex_files, magic_comments_keys):
        magic_comments = {}  # 创建空字典用于存储结果
        if len(tex_files):
            for file_path in tex_files:  # 遍历tex文件列表
                with open(file_path, 'r', encoding='utf-8') as file:  # 打开文件
                    for _ in range(50):  # 遍历文件的前50行
                        line = file.readline()  # 读取一行内容
                        for magic_comments_key in magic_comments_keys:  # 遍历关键字列表
                            if f"% !TEX {magic_comments_key} =" in line:  # 如果关键字出现在这一行
                                magic_comment = line.split(f"% !TEX {magic_comments_key} = ")[1].strip()  # 提取对应的值
                                magic_comments[magic_comments_key] = magic_comment  # 将键值对存入字典
        return magic_comments  # 返回提取的键值对字典
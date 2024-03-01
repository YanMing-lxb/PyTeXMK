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
Date         : 2024-02-29 14:16:25 +0800
LastEditTime : 2024-03-01 18:35:52 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /PyTeXMK/tests/test.py
Description  : 
 -----------------------------------------------------------------------
'''

import os
import shutil
import subprocess

test_files = [
    "biblatex-test",
    "bibtex-test",
    "contents-figrue-table-test",
    "contents-test",
    "glossaries-test",
    "nomencl-test"
]
test_file_type = ['biblatex', 'bibtex', '图表目录', '目录', 'glossaries', 'nomencl']
command = ['-v', '-h', '-c', '-C']

# 源文件夹路径
source_folder = 'src/pytexmk'
tests_folder = 'tests'

# 目标文件夹路径
destination_folder = 'proj-test'

def copy(source_folder, destination_folder):
    # 确保目标文件夹存在，如果不存在则创建
    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder)

    # 遍历源文件夹中的所有文件
    for filename in os.listdir(source_folder):
        source_file = os.path.join(source_folder, filename)
        destination_file = os.path.join(destination_folder, filename)

        # 判断源文件是否是文件
        if os.path.isfile(source_file):
            # 复制文件到目标文件夹
            shutil.copy(source_file, destination_file)

# 复制文件到目标位置
copy(source_folder, destination_folder)
copy(tests_folder, destination_folder)

# 读取原始文件内容
with open(f"{destination_folder}/__main__.py", "r") as file:
    original_content = file.read()

# 替换 from . 为 from
updated_content = original_content.replace("from .", "from ")

# 写入更新后的内容到同一文件
with open(f"{destination_folder}/__main__.py", "w") as file:
    file.write(updated_content)

# 存储所有要打印的内容
print_output = []

# 开始测试

# 测试 biblatex, bibtex, 图目录表目录目录, 目录, glossaries, nomencl
for i in range(len(test_files)):
    try:
        result = subprocess.run(['python3', '__main__.py', test_files[i]], cwd=destination_folder)
        if result.returncode == 0:
            print_output.append([test_file_type[i], "\033[92m通过\033[0m"])  # 绿色
        else:
            print_output.append([test_file_type[i], "\033[91m未通过\033[0m"])  # 红色
    except Exception as e:
        print_output.append([test_file_type[i], "\033[91m未通过\033[0m"])  # 红色

for i in command:
    try:
        if i == "-c" and "-C":
            subprocess.run(['xelatex', 'main'], cwd=destination_folder)
        subprocess.run(['python3', '__main__.py', i], cwd=destination_folder)
        if result.returncode == 0:
            print_output.append([test_file_type[i], "\033[92m通过\033[0m"])  # 绿色
        else:
            print_output.append([test_file_type[i], "\033[91m未通过\033[0m"])  # 红色
    except Exception as e:
        print_output.append([i, "\033[91m未通过\033[0m"])  # 红色

try:
    subprocess.run(['python3', '__main__.py', '-nq', 'main'], cwd=destination_folder)
    print_output.append(["-nq", "\033[92m通过\033[0m"])  # 绿色
    if result.returncode == 0:
        print_output.append([test_file_type[i], "\033[92m通过\033[0m"])  # 绿色
    else:
        print_output.append([test_file_type[i], "\033[91m未通过\033[0m"])  # 红色
except Exception as e:
    print_output.append(["-nq", "\033[91m未通过\033[0m"])  # 红色

# 打印表头
print("\033[93m{:<20} {:<20} {:<20} {:<20}\033[0m".format("测试项目", "测试状态", "测试项目", "测试状态"))  # 黄色
# 打印表格内容
for i in range(0, len(print_output), 2):
    item1, status1 = print_output[i]
    item2, status2 = print_output[i+1] if i+1 < len(print_output) else ("", "")
    print("{:<20} {:<20} {:<20} {:<20}".format(item1, status1, item2, status2))

# 删除临时文件夹
shutil.rmtree(destination_folder)

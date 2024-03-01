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
LastEditTime : 2024-03-02 01:40:50 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /PyTeXMK/tests/test.py
Description  : 
 -----------------------------------------------------------------------
'''

import os
import shutil
import datetime
import subprocess
from rich.console import Console
from rich.table import Table

start_time = datetime.datetime.now() # 计算开始时间

test_files = [
    "biblatex-test",
    "bibtex-test",
    "contents-figrue-table-test",
    "contents-test",
    "glossaries-test",
    "nomencl-test"
]
test_file_type = ['biblatex', 'bibtex', '图表目录', '目录', 'glossaries', 'nomencl']
command = ['-nq', '-v', '-h', '-c', '-C']

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
            print_output.append([test_file_type[i], "[green]通过"])  # 绿色
        else:
            print_output.append([test_file_type[i], "[red]未通过"])  # 红色
    except Exception as e:
        print_output.append([test_file_type[i], "[red]未通过"])  # 红色

for i in range(len(command)):
    try:
        if command[i] == "-nq":
            result = subprocess.run(['python3', '__main__.py', '-nq', 'main'], cwd=destination_folder)
            print_output.append(["-nq", "[green]通过"])  # 绿色
            if result.returncode == 0:
                print_output.append([command[i], "[green]通过"])  # 绿色
            else:
                print_output.append([command[i], "[red]未通过"])  
        elif command[i] == "-c" and "-C":
            subprocess.run(['xelatex', "-shell-escape", "-file-line-error", "-halt-on-error", "-interaction=batchmode", 'main'], cwd=destination_folder)
            result = subprocess.run(['python3', '__main__.py', command[i]], cwd=destination_folder)
            if result.returncode == 0:
                print_output.append([command[i], "[green]通过"])  # 绿色
            else:
                print_output.append([command[i], "[red]未通过"])  # 红色
        else:
            result = subprocess.run(['python3', '__main__.py', command[i]], cwd=destination_folder)
            if result.returncode == 0:
                print_output.append([command[i], "[green]通过"])  # 绿色
            else:
                print_output.append([command[i], "[red]未通过"])  # 红色
    except Exception as e:
        print_output.append([i, "[red]未通过"])  # 红色

# subprocess.run(['python3', '__main__.py', '-C'], cwd=destination_folder)
# 创建Console对象
console = Console()

# 创建Table对象
table = Table(title="测试项目和状态")

# 添加表头
table.add_column("测试项目", style="cyan", no_wrap=True)
table.add_column("测试状态", justify = "center", style="magenta", no_wrap=True)
table.add_column("测试项目", style="cyan", no_wrap=True)
table.add_column("测试状态", justify = "center", style="magenta", no_wrap=True)

for i in range(0, len(print_output), 2):
    row1 = print_output[i]
    row2 = print_output[i+1] if i+1 < len(print_output) else ["", ""]
    table.add_row(row1[0], row1[1], row2[0], row2[1])

# 打印表格
console.print(table)

# 删除临时文件夹
shutil.rmtree(destination_folder)

end_time = datetime.datetime.now() # 计算开始时间
run_time = end_time - start_time
hours, remainder = divmod(run_time.seconds, 3600)
minutes, seconds = divmod(remainder, 60)
milliseconds = run_time.microseconds // 1000  # 获取毫秒部分
print("\n" + "=" * 80)
print(f"测试时长为：{hours} 小时 {minutes} 分 {seconds} 秒 {milliseconds} 毫秒 ({run_time.total_seconds():.3f} s total)\n")
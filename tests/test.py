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
LastEditTime : 2024-02-29 20:57:21 +0800
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
source_folder =  'src/pytexmk'
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



# 开始测试

# 测试 biblatex, bibtex, 图目录表目录目录, 目录, glossaries, nomencl
for i in range(len(test_files)):
    try:
        subprocess.run(['python3', '__main__.py', test_files[i]], cwd=destination_folder)
        print(f'{test_file_type[i]} 测试通过！')
    except Exception as e:
        print(f'{test_file_type[i]} 测试没通过！发生错误：{e}')
    finally:
        print('')

for i in command:
    try:
        if i == "-c" and "-C":
            subprocess.run(['xelatex', 'main'], cwd= destination_folder)
        subprocess.run(['python3', '__main__.py', i], cwd= destination_folder)
        print(f'{i} 测试通过！')
    except Exception as e:
        print(f'{i} 测试没通过！发生错误：{e}')
    finally:
        print('')
    
try:
    subprocess.run(['python3', '__main__.py', '-nq', 'main'], cwd= destination_folder)
    print('-nq 测试通过！')
except Exception as e:
    print('-nq 测试没通过！发生错误：{e}')
finally:
    print('')


shutil.rmtree(destination_folder)

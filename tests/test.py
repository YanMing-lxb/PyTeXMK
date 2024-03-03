import os
import shutil
import datetime
import subprocess
from rich.console import Console
from rich.table import Table

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

# 修改函数为可运行函数
def file_modify(destination_folder):
    # 读取原始文件内容
    with open(f"{destination_folder}/__main__.py", "r", encoding='utf-8') as file:
        original_content = file.read()

    # 替换 from . 为 from
    updated_content = original_content.replace("from .", "from ")

    # 写入更新后的内容到同一文件
    with open(f"{destination_folder}/__main__.py", "w") as file:
        file.write(updated_content)

# 测试函数
def test(test_files, test_file_type, command, destination_folder):
    # 存储所有要打印的内容
    print_output = []
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
    # 测试 pytexmk 参数
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
    return print_output

def remove(path):
    if os.path.exists(path):
        shutil.rmtree(path)  # 删除整个文件夹
        print("删除临时测试文件夹")
    os.mkdir(path)  # 创建空的 path 文件夹

def print_table(data):
    console = Console() # 创建Console对象

    table = Table(title="测试项目和状态") # 创建Table对象

    # 添加表头
    table.add_column("测试项目", style="cyan", no_wrap=True)
    table.add_column("测试状态", justify = "center", style="magenta", no_wrap=True)
    table.add_column("测试项目", style="cyan", no_wrap=True)
    table.add_column("测试状态", justify = "center", style="magenta", no_wrap=True)

    for i in range(0, len(data), 2):
        row1 = data[i]
        row2 = data[i+1] if i+1 < len(data) else ["", ""]
        table.add_row(row1[0], row1[1], row2[0], row2[1])

    console.print(table) # 打印表格

# --------------------------------------------------------------------------------
# 测试目标
# --------------------------------------------------------------------------------
test_files = [
    "biblatex-test",
    "bibtex-test",
    "contents-figrue-table-test",
    "contents-test",
    "glossaries-test",
    "nomencl-test",
    "makeidx-test"
]
test_file_type = ['biblatex', 'bibtex', '图表目录', '目录', 'glossaries', 'nomencl', "makeidx"]
command = ['-nq', '-v', '-h', '-c', '-C']

source_folder = 'src/pytexmk' # 源文件夹路径
tests_folder = 'tests' # 测试文件路径
destination_folder = 'test-temp' # 目标文件夹路径

# --------------------------------------------------------------------------------
# 运行测试流程
# --------------------------------------------------------------------------------
start_time = datetime.datetime.now() # 计算开始时间
remove(destination_folder) # 删除临时测试文件夹
copy(source_folder, destination_folder) # 复制测试对象到目标位置
copy(tests_folder, destination_folder) # 复制测试文件到目标位置
file_modify(destination_folder) # 修改测试对象使其可运行
data = test(test_files, test_file_type, command, destination_folder)
remove(destination_folder) # 删除临时测试文件夹
print_table(data)
# subprocess.run(['python3', '__main__.py', '-C'], cwd=destination_folder)

# --------------------------------------------------------------------------------
# 打印统计s
# --------------------------------------------------------------------------------
end_time = datetime.datetime.now() # 计算结束时间
run_time = end_time - start_time
hours, remainder = divmod(run_time.seconds, 3600)
minutes, seconds = divmod(remainder, 60)
milliseconds = run_time.microseconds // 1000  # 获取毫秒部分
print("\n" + "=" * 80)
print(f"测试时长为：{hours} 小时 {minutes} 分 {seconds} 秒 {milliseconds} 毫秒 ({run_time.total_seconds():.3f} s total)\n")
import shutil
import datetime
import argparse
import subprocess
from rich.console import Console
from rich.table import Table
from pathlib import Path  # 导入pathlib库

def copy(source_folder, destination_folder):
    source_folder = Path(source_folder)  # 将字符串路径转换为Path对象
    destination_folder = Path(destination_folder)  # 将字符串路径转换为Path对象

    # 确保目标文件夹存在，如果不存在则创建
    destination_folder.mkdir(parents=True, exist_ok=True)

    # 遍历源文件夹中的所有文件
    for source_file in source_folder.iterdir():
        destination_file = destination_folder / source_file.name  # 构建目标文件的Path对象
        print(f"复制文件 {source_file} 到 {destination_file}")
        # 判断源文件是否是文件
        if source_file.is_file():
            # 复制文件到目标文件夹
            
            shutil.copy(source_file, destination_file)

# 修改函数为可运行函数
def file_modify(destination_folder):
    destination_folder = Path(destination_folder)  # 将字符串路径转换为Path对象

    # 读取原始文件内容
    for file_path in destination_folder.rglob('*.py'):
        with file_path.open('r', encoding='utf-8') as file:
            content = file.read()
        content = content.replace('from .', 'from ')  # 替换 from . 为 from
        with file_path.open('w', encoding='utf-8') as file:
            file.write(content)  # 写入更新后的内容到同一文件

# --------------------------------------------------------------------------------
# 测试函数
# --------------------------------------------------------------------------------
def test(test_files, test_file_type, command, run_command, destination_folder):
    destination_folder = Path(destination_folder)  # 将字符串路径转换为Path对象

    # 存储所有要打印的内容
    print_output = []
    # 测试 biblatex, bibtex, 图目录表目录目录, 目录, glossaries, nomencl
    for i in range(len(test_files)):
        try:
            time_start = datetime.datetime.now()
            result = subprocess.run(run_command + [test_files[i]], cwd=destination_folder)
            time_end = datetime.datetime.now()
            time_run = round((time_end - time_start).total_seconds(), 4)
            if result.returncode == 0:
                print_output.append([test_file_type[i], time_run, "[green]通过"])  # 绿色
            else:
                print_output.append([test_file_type[i], time_run, "[red]未通过"])  # 红色
        except Exception as e:
            print_output.append([test_file_type[i], 0, "[red]未通过"])  # 红色
    # 测试 pytexmk 参数
    for i in range(len(command)):
        try:
            if command[i] == "-nq":
                time_start = datetime.datetime.now()
                result = subprocess.run(run_command + ['-nq', 'main'], cwd=destination_folder)
                time_end = datetime.datetime.now()
                time_run = round((time_end - time_start).total_seconds(), 4)
                if result.returncode == 0:
                    print_output.append([command[i], time_run, "[green]通过"])  # 绿色
                else:
                    print_output.append([command[i], time_run, "[red]未通过"])  
            elif command[i] == "-c" and "-C":
                time_start = datetime.datetime.now()
                subprocess.run(['xelatex', "-shell-escape", "-file-line-error", "-halt-on-error", "-interaction=batchmode", 'main'], cwd=destination_folder)
                result = subprocess.run(run_command + [command[i]], cwd=destination_folder)
                time_end = datetime.datetime.now()
                time_run = round((time_end - time_start).total_seconds(), 4)
                if result.returncode == 0:
                    print_output.append([command[i], time_run, "[green]通过"])  # 绿色
                else:
                    print_output.append([command[i], time_run, "[red]未通过"])  # 红色
            else:
                time_start = datetime.datetime.now()
                result = subprocess.run(run_command + [command[i]], cwd=destination_folder)
                time_end = datetime.datetime.now()
                time_run = round((time_end - time_start).total_seconds(), 4)
                if result.returncode == 0:
                    print_output.append([command[i], time_run, "[green]通过"])  # 绿色
                else:
                    print_output.append([command[i], time_run, "[red]未通过"])  # 红色
        except Exception as e:
            print_output.append([i, 0, "[red]未通过"])  # 红色
    return print_output

# --------------------------------------------------------------------------------
# 清除临时测试文件夹函数
# --------------------------------------------------------------------------------
def remove(path):
    path = Path(path)  # 将字符串路径转换为Path对象
    if path.exists():
        shutil.rmtree(path)  # 删除整个文件夹
        print("删除临时测试文件夹\n")

# --------------------------------------------------------------------------------
# 测试统计表打印函数
# --------------------------------------------------------------------------------
def print_table(data):
    console = Console()  # 创建Console对象

    table = Table(show_header=True, header_style="bold magenta", 
                title="PyTeXMK 测试统计表")

    # 定义列名
    table.add_column("序号", style="yellow", justify="center", no_wrap=True)
    table.add_column("测试项目", style="cyan", justify="left", no_wrap=True)
    table.add_column("测试时长", style="green", justify="left", no_wrap=True)
    table.add_column("状态", justify="center", no_wrap=True)
    table.add_column("序号", style="yellow", justify="center", no_wrap=True)
    table.add_column("测试项目", style="cyan", justify="left")
    table.add_column("测试时长", style="green", justify="left", no_wrap=True)
    table.add_column("状态", justify="center", no_wrap=True)

    # 判断统计项目列数是否是偶数
    length = len(data)/2  # 计算打印表格列数
    row_num = ""
    # 判断统计项目列数是否是偶数
    if length - int(length) < 0.5:
        row_num = int(length)
    else:  # 是偶数则加一
        row_num = int(length) + 1

    # 添加数据到表格
    for i in range(row_num):
        table.add_row(
            str(i+1),
            data[i][0],
            "{:.4f} s".format(data[i][1]),
            data[i][2],
            str(i+1+row_num) if i+row_num <= len(data) else "",
            data[i+row_num][0] if i+row_num < len(data) else "",
            "{:.4f} s".format(data[i+row_num][1]) if i+row_num < len(data) else "",
            data[i+row_num][2] if i+row_num < len(data) else ""
        )

    console.print(table)  # 打印表格

# --------------------------------------------------------------------------------
# 测试目标
# --------------------------------------------------------------------------------
parser = argparse.ArgumentParser(description="辅助测试文件.")
parser.add_argument('-v', '--version', action='version', version='test: v 0.1')
parser.add_argument('-w', '--whl', action='store_true', help="测试 whl 文件")
args = parser.parse_args()

test_files = [
    "biblatex-test",
    "bibtex-test",
    "thebibliography-test",
    "contents-figrue-table-test",
    "contents-test",
    "glossaries-test",
    "nomencl-test",
    "makeidx-test"
]
test_file_type = ['biblatex', 'bibtex', 'thebibliography', '图表目录', '目录', 'glossaries', 'nomencl', "makeidx"]
command = ['-v', '-h', '-nq', '-c', '-C']

source_folder = 'src/pytexmk'  # 将字符串路径转换为Path对象
tests_folder = 'tests'  # 将字符串路径转换为Path对象
destination_folder = 'test-temp'  # 将字符串路径转换为Path对象
run_file = "__main__.py"
run_command = ["python", "__main__.py"]
if args.whl:
    run_command = ["pytexmk"]

# --------------------------------------------------------------------------------
# 运行测试流程
# --------------------------------------------------------------------------------
# start_time = datetime.datetime.now()  # 计算开始时间
# remove(destination_folder)  # 删除临时测试文件夹
copy(source_folder, destination_folder)  # 复制测试对象到目标位置
copy(tests_folder, destination_folder)  # 复制测试文件到目标位置
file_modify(destination_folder)  # 修改测试对象使其可运行
# data = test(test_files, test_file_type, command, run_command, destination_folder)
# remove(destination_folder)  # 删除临时测试文件夹
# print_table(data)
# subprocess.run([run_command, test_file, '-C'], cwd=destination_folder)

# --------------------------------------------------------------------------------
# 打印统计
# --------------------------------------------------------------------------------
# end_time = datetime.datetime.now()  # 计算结束时间
# run_time = end_time - start_time
# hours, remainder = divmod(run_time.seconds, 3600)
# minutes, seconds = divmod(remainder, 60)
# milliseconds = run_time.microseconds // 1000  # 获取毫秒部分
# print("\n" + "=" * 80)
# print(f"测试时长为：{hours} 小时 {minutes} 分 {seconds} 秒 {milliseconds} 毫秒 ({run_time.total_seconds():.3f} s total)\n")
# def your_function():
#     try:
#         command = ['xelatex', "-shell-escape", "-file-line-error", "-halt-on-error", "-interaction=batchmode", 'main.tex']
#         completed_process = subprocess.run(command, check=True, text=True, capture_output=True)
#         print("Process completed successfully!")
#     except subprocess.CalledProcessError as e:
#         # print(f"Error running command: {e}")
#         # print(f"Return code: {e.returncode}")
#         print(f"Output: {e.output}")
#         # print(f"Error running command: {e.stderr}")
#         return

#     print("Done!")

# your_function()
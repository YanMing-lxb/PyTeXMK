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

# --------------------------------------------------------------------------------
# 测试函数
# --------------------------------------------------------------------------------
def test(test_files, test_file_type, command, destination_folder):
    # 存储所有要打印的内容
    print_output = []
    # 测试 biblatex, bibtex, 图目录表目录目录, 目录, glossaries, nomencl
    for i in range(len(test_files)):
        try:
            time_start = datetime.datetime.now()
            result = subprocess.run(['python3', '__main__.py', test_files[i]], cwd=destination_folder)
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
                result = subprocess.run(['python3', '__main__.py', '-nq', 'main'], cwd=destination_folder)
                time_end = datetime.datetime.now()
                time_run = round((time_end - time_start).total_seconds(), 4)
                if result.returncode == 0:
                    print_output.append([command[i], time_run, "[green]通过"])  # 绿色
                else:
                    print_output.append([command[i], time_run, "[red]未通过"])  
            elif command[i] == "-c" and "-C":
                time_start = datetime.datetime.now()
                subprocess.run(['xelatex', "-shell-escape", "-file-line-error", "-halt-on-error", "-interaction=batchmode", 'main'], cwd=destination_folder)
                result = subprocess.run(['python3', '__main__.py', command[i]], cwd=destination_folder)
                time_end = datetime.datetime.now()
                time_run = round((time_end - time_start).total_seconds(), 4)
                if result.returncode == 0:
                    print_output.append([command[i], time_run, "[green]通过"])  # 绿色
                else:
                    print_output.append([command[i], time_run, "[red]未通过"])  # 红色
            else:
                time_start = datetime.datetime.now()
                result = subprocess.run(['python3', '__main__.py', command[i]], cwd=destination_folder)
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
    if os.path.exists(path):
        shutil.rmtree(path)  # 删除整个文件夹
        print("删除临时测试文件夹\n")
    os.mkdir(path)  # 创建空的 path 文件夹

# --------------------------------------------------------------------------------
# 测试统计表打印函数
# --------------------------------------------------------------------------------
def print_table(data):
    console = Console() # 创建Console对象

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
    length = len(data)/2 # 计算打印表格列数
    row_num = None
    # 判断统计项目列数是否是偶数
    if length - int(length) < 0.5:
        row_num = int(length)
    else: # 是偶数则加一
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

    console.print(table) # 打印表格

# --------------------------------------------------------------------------------
# 测试目标
# --------------------------------------------------------------------------------
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
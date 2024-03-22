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
Date         : 2024-03-03 10:34:41 +0800
LastEditTime : 2024-03-22 14:50:06 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /PyTeXMK/src/pytexmk/info_print.py
Description  : 
 -----------------------------------------------------------------------
'''
# -*- coding: utf-8 -*-
import datetime
from rich.console import Console
from rich.table import Table
from rich import box
from rich import print
console = Console() # 创建控制台对象
# --------------------------------------------------------------------------------
# 定义时间统计函数
# --------------------------------------------------------------------------------
def time_count(fun, *args):
    time_start = datetime.datetime.now()
    fun_return = fun(*args)
    time_end = datetime.datetime.now()
    time_run = time_end - time_start

    time_run = round(time_run.total_seconds(), 4)
    return time_run, fun_return

# --------------------------------------------------------------------------------
# 定义信息打印函数
# --------------------------------------------------------------------------------
def print_message(message):
    padding_size = 80 - (len(message) + sum(1 for c in message if not c.isascii()))-4  # 计算左右两侧 X 的数量
    left_padding = int(padding_size / 2)
    right_padding = padding_size - left_padding
    banner = "[not bold]X[/not bold]" * left_padding + f"| {message} |" + "[not bold]X[/not bold]" * right_padding
    console.print("\n\n" + "=" * 80, style="yellow bold")
    console.print(banner, style="red on white bold")
    console.print("=" * 80 + "\n\n", style="yellow bold")
    

# --------------------------------------------------------------------------------
# 定义统计时间打印函数
# --------------------------------------------------------------------------------
def time_print(start_time, name_target_list, time_run_list):
    end_time = datetime.datetime.now() # 计算结束时间
    run_time = end_time - start_time
    hours, remainder = divmod(run_time.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = run_time.microseconds // 1000  # 获取毫秒部分

    number_programmes_run = len(name_target_list)-4
    
    time_compile = sum(time_run_list)
    name_target_list.append('LaTeX 编译时长')
    time_run_list.append(time_compile)

    time_other_operating = float(run_time.total_seconds()) - time_compile
    name_target_list.append('Python 运行时长')
    time_run_list.append(time_other_operating)

    time_pytexmk = float(run_time.total_seconds())
    name_target_list.append('PyTeXMK 运行时长')
    time_run_list.append(time_pytexmk)

    # 创建表格对象
    table = Table(show_header=True, header_style="bold magenta", box=box.ASCII_DOUBLE_HEAD, 
                title="PyTeXMK 运行时长统计表")

    # 定义列名
    table.add_column("序号", justify="center", no_wrap=True)
    table.add_column("运行项目", style="cyan", justify="center", no_wrap=True)
    table.add_column("运行时长", style="green", justify="center", no_wrap=True)
    table.add_column("序号", justify="center", no_wrap=True)
    table.add_column("运行项目", style="cyan", justify="center")
    table.add_column("运行时长", style="green", justify="center", no_wrap=True)

    # 判断统计项目列数是否是偶数
    length = len(name_target_list)/2 # 计算打印表格列数
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
            name_target_list[i],
            "{:.4f} s".format(time_run_list[i]),
            str(i+1+row_num) if i+row_num <= len(name_target_list) else "",
            name_target_list[i+row_num] if i+row_num < len(name_target_list) else "",
            "{:.4f} s".format(time_run_list[i+row_num]) if i+row_num < len(name_target_list) else ""  
        )

    print("\n" + "=" * 80 + "\n")
    console.print(table) # 打印表格

    print(f"PyTeXMK 运行时长：{hours} 小时 {minutes} 分 {seconds} 秒 {milliseconds} 毫秒 ({run_time.total_seconds():.3f} s total)")
    print(f"运行函数：{number_programmes_run} 个")
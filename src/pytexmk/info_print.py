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
LastEditTime : 2024-07-27 19:26:33 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /PyTeXMK/src/pytexmk/info_print.py
Description  : 
 -----------------------------------------------------------------------
'''
# -*- coding: utf-8 -*-
import logging
import datetime
from rich.console import Console
from rich.table import Table
from rich import box
from rich import print
console = Console() # 创建控制台对象
logger = logging.getLogger(__name__) # 创建日志对象

# --------------------------------------------------------------------------------
# 定义时间统计函数
# --------------------------------------------------------------------------------
def time_count(fun, *args):
    """
    计算并返回函数执行时间及函数返回值。
    
    参数:
    - fun: 需要计算执行时间的函数。
    - *args: 传递给函数的参数。
    
    返回:
    - 返回一个元组，包含函数的执行时间和函数的返回值。如果函数执行过程中出现异常，则返回 (None, None)。
    
    行为:
    1. 记录函数开始执行的时间。
    2. 执行函数并记录其返回值。
    3. 记录函数结束执行的时间。
    4. 计算函数执行的总时间，并将其四舍五入到小数点后四位。
    5. 返回函数执行时间和函数的返回值。
    6. 如果在执行函数过程中出现异常，记录错误信息并返回 (None, None)。
    """
    try:
        time_start = datetime.datetime.now()
        fun_return = fun(*args)
        time_end = datetime.datetime.now()
        time_run = (time_end - time_start).total_seconds()
        return round(time_run, 4), fun_return
    except Exception as e:
        logger.error(f"执行函数 {fun.__name__} 时出错: {e}")
        return None, None


# --------------------------------------------------------------------------------
# 定义信息打印函数
# --------------------------------------------------------------------------------
def print_message(message):
    """
    打印带有装饰的消息。
     
    此函数接收一个消息字符串，计算其长度并根据需要添加装饰字符（X），
    然后将消息打印在一个带有边框的横幅中。
     
    参数:
    - message (str): 要打印的消息字符串。
     
    异常:
    - Exception: 如果在打印过程中发生任何异常，将记录错误日志。
    """
    try:
        # 计算左右两侧 X 的数量
        ascii_len = sum(1 for i in message if not i.isascii())
        padding_size = 80 - (len(message) + ascii_len) - 4
        left_padding = padding_size // 2
        right_padding = padding_size - left_padding
        banner = "[not bold]X[/not bold]" * left_padding + f"| {message} |" + "[not bold]X[/not bold]" * right_padding
        console.print("\n\n" + "=" * 80, style="yellow bold")
        console.print(banner, style="red on white bold")
        console.print("=" * 80 + "\n\n", style="yellow bold")
    except Exception as e:
        logger.error(f"执行函数 print_message 时出错: {e}")
    

# --------------------------------------------------------------------------------
# 定义统计时间打印函数
# --------------------------------------------------------------------------------
def time_print(start_time, name_target_list, time_run_list):
    """
    计算并打印PyTeXMK运行时长的统计信息，包括总运行时间、各部分运行时间以及运行函数数量。
    
    参数:
    - start_time (datetime.datetime): PyTeXMK开始运行的时间。
    - name_target_list (list): 包含运行项目名称的列表。
    - time_run_list (list): 包含各运行项目时长的列表。
    
    行为:
    1. 计算结束时间并计算总运行时间。
    2. 将总运行时间分解为小时、分钟、秒和毫秒。
    3. 计算运行函数数量（辅助函数除外）。
    4. 计算LaTeX编译时长、Python运行时长和PyTeXMK总运行时长。
    5. 将统计信息添加到name_target_list和time_run_list中。
    6. 创建并填充表格，显示运行项目的名称和时长。
    7. 打印表格和总运行时间、运行函数数量。
    
    异常处理:
    - 如果在执行过程中发生异常，将错误信息记录到日志中。
    """
    try:
        end_time = datetime.datetime.now()  # 计算结束时间
        run_time = end_time - start_time
        total_seconds = run_time.total_seconds()
        hours, remainder = divmod(int(total_seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        milliseconds = run_time.microseconds // 1000  # 获取毫秒部分
 
        number_programmes_run = len(name_target_list) - 6  # 计算运行函数数量（辅助函数除外）
 
        time_compile = sum(time_run_list)
        time_other_operating = total_seconds - time_compile
        time_pytexmk = total_seconds
 
        # 添加统计信息到列表
        name_target_list.extend(['LaTeX 编译时长', 'Python 运行时长', 'PyTeXMK 运行时长'])
        time_run_list.extend([time_compile, time_other_operating, time_pytexmk])
 
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
            row_data = [
                str(i + 1),
                name_target_list[i],
                "{:.4f} s".format(time_run_list[i])
            ]
            if i + row_num < len(name_target_list):
                row_data.extend([
                    str(i + 1 + row_num),
                    name_target_list[i + row_num],
                    "{:.4f} s".format(time_run_list[i + row_num])
                ])
            else:
                row_data.extend(["", "", ""])
            table.add_row(*row_data)
             
        print("\n" + "=" * 80 + "\n")
        console.print(table) # 打印表格
 
        print(f"PyTeXMK 运行时长：{hours} 小时 {minutes} 分 {seconds} 秒 {milliseconds} 毫秒 ({total_seconds:.3f} s total)")
        print(f"运行函数：{number_programmes_run} 个")
    except Exception as e:
        logger.error(f"执行函数 time_print 时出错: {e}")
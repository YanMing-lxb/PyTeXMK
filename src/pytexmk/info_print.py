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
LastEditTime : 2025-01-29 22:01:12 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /PyTeXMK/src/pytexmk/info_print_module.py
Description  : 
 -----------------------------------------------------------------------
'''
# -*- coding: utf-8 -*-
import logging
import datetime
from rich import box
from rich import print
from rich.text import Text
from rich.table import Table
from rich.console import Console

from pytexmk.language import set_language

console = Console() # 创建控制台对象
logger = logging.getLogger(__name__) # 创建日志对象

_ = set_language('info_print')  # 设置语言

# 总字符串长度
total_len = 78

# --------------------------------------------------------------------------------
# 定义时间统计函数
# --------------------------------------------------------------------------------
def time_count(fun, *args):
    """
    计算并返回函数执行时间及函数返回值.
    
    参数:
    - fun: 需要计算执行时间的函数.
    - *args: 传递给函数的参数.
    
    返回:
    - 返回一个元组,包含函数的执行时间和函数的返回值.如果函数执行过程中出现异常,则返回 (None, None).
    
    行为:
    1. 记录函数开始执行的时间.
    2. 执行函数并记录其返回值.
    3. 记录函数结束执行的时间.
    4. 计算函数执行的总时间,并将其四舍五入到小数点后四位.
    5. 返回函数执行时间和函数的返回值.
    6. 如果在执行函数过程中出现异常,记录错误信息并返回 (None, None).
    """
    try:
        # 获取当前时间作为函数执行的开始时间
        time_start = datetime.datetime.now()
        # 调用传入的函数并传入参数,获取函数返回值
        fun_return = fun(*args)
        # 获取当前时间作为函数执行的结束时间
        time_end = datetime.datetime.now()
        # 计算函数执行的总时间(以秒为单位)
        time_run = (time_end - time_start).total_seconds()
        # 如果函数没有返回值,只返回执行时间
        if fun_return is None:
            return round(time_run, 4)
        # 否则返回函数执行时间和函数返回值,时间保留四位小数
        return round(time_run, 4), fun_return
    except Exception as e:
        # 如果执行函数时出错,记录错误信息并返回None
        logger.error(_('执行函数 %(args)s 时出错: ') % {'args': {fun.__name__}} + str(e))
        return None, None


# --------------------------------------------------------------------------------
# 计算 text 中非ASCII字符的数量
# --------------------------------------------------------------------------------
def get_text_len(text):
    non_ascii_len = sum(1 for i in text if not i.isascii())
    text_len = len(text) + non_ascii_len
    return text_len


# --------------------------------------------------------------------------------
# 定义信息打印函数
# --------------------------------------------------------------------------------
def print_message(message, state):
    """
    打印带有装饰的消息.

    此函数接收一个消息字符串,计算其长度并根据需要添加装饰字符(X),
    然后将消息打印在一个带有边框的横幅中.

    参数:
    - message (str): 要打印的消息字符串.

    异常:
    - Exception: 如果在打印过程中发生任何异常,将记录错误日志.
    """
    if state == "additional":
        in_dec_chars = "X"  # 设置内部装饰字符
        out_dec_chars = "="  # 设置外部装饰字符
        in_dec_chars_style = "red on white"  # 设置内部装饰字符风格
        out_dec_chars_style = "blue bold"  # 设置外部装饰字符风格
        message_style = "red on white bold"  # 设置消息风格
    elif state == "running":
        in_dec_chars = "X"  # 设置内部装饰字符
        out_dec_chars = "="  # 设置外部装饰字符
        in_dec_chars_style = "red on white"  # 设置内部装饰字符风格
        out_dec_chars_style = "yellow bold"  # 设置外部装饰字符风格
        message_style = "red on white bold"  # 设置消息风格
    elif state == "success":
        in_dec_chars = "▓"  # 设置内部装饰字符
        out_dec_chars = "="  # 设置外部装饰字符
        in_dec_chars_style = "red on white"  # 设置内部装饰字符风格
        out_dec_chars_style = "green bold"  # 设置外部装饰字符风格
        message_style = "bold red on white"  # 设置消息风格

    try:
        # 计算左右两侧 X 的数量
        padding_size = total_len - get_text_len(message) - 4  # 计算需要填充的空格数量
        left_padding = padding_size // 2  # 计算左侧填充的X数量
        right_padding = padding_size - left_padding  # 计算右侧填充的X数量
        
        left_banner = in_dec_chars * left_padding
        right_banner = in_dec_chars * right_padding

        banner = f"[{in_dec_chars_style}]{left_banner}[/{in_dec_chars_style}]" + f"[{message_style}]| {message} |[/{message_style}]" + f"[{in_dec_chars_style}]{right_banner}[/{in_dec_chars_style}]"
        
        console.print("\n" + out_dec_chars * total_len, style=f"{out_dec_chars_style}")
        console.print(banner)
        console.print(out_dec_chars * total_len + "\n", style=f"{out_dec_chars_style}")
    except Exception as e:
        logger.error(_('打印模块信息时出错: ') + str(e))  # 记录错误日志
    

# --------------------------------------------------------------------------------
# 定义统计时间打印函数
# --------------------------------------------------------------------------------
def time_print(start_time, runtime_dict):
    """
    计算并打印PyTeXMK运行时长的统计信息,包括总运行时间、各部分运行时间以及运行函数数量.
    
    参数:
    - start_time (datetime.datetime): PyTeXMK开始运行的时间.
    - runtime_dict (dict): 包含运行项目名称和时长的字典.
    
    行为:
    1. 计算结束时间并计算总运行时间.
    2. 将总运行时间分解为小时、分钟、秒和毫秒.
    3. 计算运行函数数量(辅助函数除外).
    4. 计算LaTeX编译时长、Python运行时长和PyTeXMK总运行时长.
    5. 将统计信息添加到runtime_dict中.
    6. 创建并填充表格,显示运行项目的名称和时长.
    7. 打印表格和总运行时间、运行函数数量.
    
    异常处理:
    - 如果在执行过程中发生异常,将错误信息记录到日志中.
    """
    try:
        end_time = datetime.datetime.now()  # 计算结束时间
        run_time = end_time - start_time  # 计算运行时间
        total_seconds = run_time.total_seconds()  # 获取总秒数
        hours, remainder = divmod(int(total_seconds), 3600)  # 计算小时数
        minutes, seconds = divmod(remainder, 60)  # 计算分钟数和秒数
        milliseconds = run_time.microseconds // 1000  # 获取毫秒部分

        time_pytexmk = total_seconds  # 计算PyTeXMK运行时长

        time_LaTeX_list = [value for key, value in runtime_dict.items() if any(include_str in key for include_str in ["PdfLaTeX", "LuaLaTeX", "XeLaTeX", " 编译", "宏包", "运行"])]  # 筛选过程独立成一个变量

        if time_LaTeX_list:  # 如果存在LaTeX编译时长列表
            time_LaTeX = sum(time_LaTeX_list)  # 对筛选后的值求和
            time_python = total_seconds - time_LaTeX  # 计算Python运行时长
            runtime_dict.update({_('LaTeX 编译时长'): time_LaTeX, _('Python 运行时长'): time_python, _('PyTeXMK 运行时长'): time_pytexmk})
        else:  # 如果不存在LaTeX编译时长列表
            time_python = total_seconds  # 计算Python运行时长
            runtime_dict.update({_('Python 运行时长'): time_python, _('PyTeXMK 运行时长'): time_pytexmk}) # 添加统计信息到字典

        # 格式化所有时间
        max_whole_digits = max(len(str(int(value))) for value in runtime_dict.values())  # 获取所有时间中小数点前的最大位数
        formatted_times = {key: f"{value:0{max_whole_digits+5}.4f} s" for key, value in runtime_dict.items()}  # 格式化所有时间位数相同
        runtime_dict.update(formatted_times)  # 更新字典中的时间格式

        number_programmes_run = len(time_LaTeX_list) # 计算运行函数数量(辅助函数除外)

        # 创建表格对象
        table = Table(show_header=True, header_style="bold dark_orange", box=box.ASCII_DOUBLE_HEAD, title=_("PyTeXMK 运行时长统计表"))

        # 定义列名
        table.add_column("No.", justify="center", no_wrap=True)
        table.add_column(Text(_("运行项目"), justify="center"), style="cyan", justify="left", no_wrap=True)
        table.add_column(_("运行时长"), style="green", justify="center", no_wrap=True)
        table.add_column("No.", justify="center", no_wrap=True)
        table.add_column(Text(_("运行项目"), justify="center"), style="cyan", justify="left", no_wrap=True)
        table.add_column(_("运行时长"), style="green", justify="center", no_wrap=True)

        # 计算打印表格列数
        length = len(runtime_dict) / 2
        row_num = None

        # 判断统计项目列数是否是偶数
        if length - int(length) < 0.5:
            row_num = int(length)
        else:  # 是偶数则加一
            row_num = int(length) + 1

        # 获取字典的键列表
        name_target_list = list(runtime_dict.keys())

        # 添加数据到表格
        for i in range(row_num):
            row_data = [
                f"{i + 1:02d}",  # 序号
                name_target_list[i],  # 运行项目名称
                runtime_dict[name_target_list[i]]  # 运行时长
            ]
            if i + row_num < len(name_target_list):
                row_data.extend([
                    f"{i + 1 + row_num:02d}",  # 序号
                    name_target_list[i + row_num],  # 运行项目名称
                    runtime_dict[name_target_list[i + row_num]] # 运行时长
                ])
            else:
                row_data.extend(["", "", ""])
            table.add_row(*row_data)

        print("\n" + "=" * total_len + "\n")  # 打印分隔线
        console.print(table)  # 打印表格

        print(_('PyTeXMK 运行时长: ') + f"{hours} h {minutes} min {seconds} s {milliseconds} ms ({total_seconds:.3f} s total)")  # 打印总运行时长
        print(_('运行 LaTeX 程序数目: ') + f"{number_programmes_run}")  # 打印运行函数数量
    except Exception as e:
        logger.error(_('打印运行时长统计表时出错: ') + str(e))  # 记录错误信息


# --------------------------------------------------------------------------------
# 定义魔法注释说明表格函数
# --------------------------------------------------------------------------------
def magic_comment_desc_table():
    """
    打印README表格.

    参数:
    - magic_comment_desc_dict (dict): 包含README信息的字典.    

    行为:
    1. 创建表格对象.
    2. 定义列名.
    3. 添加数据到表格.
    4. 打印表格.

    异常处理:
    - 如果在执行过程中发生异常,将错误信息记录到日志中.
    """

    magic_comment_desc_dic = {
        '% !TEX program = XeLaTeX': _("指定编译程序: XeLaTeX PdfLaTeX LuaLaTeX"),
        '% !TEX root = main.tex': _("指定待编译主文件名，仅支持根目录下的文件"),
        '% !TEX outdir = out_folder': _("指定编译结果存放位置，仅支持文件夹名称"),
        '% !TEX auxdir = aux_folder': _("指定辅助文件存放位置，仅支持文件夹名称")
        }
    try:
        # 创建表格对象
        table = Table(show_header=True, header_style="bold dark_orange", box=box.ASCII_DOUBLE_HEAD, title=_("魔法注释说明表"))

        # 定义列名
        table.add_column("No.", justify="center", no_wrap=True)
        table.add_column(Text("Magic Comment", justify="center"), style="cyan", justify="left", no_wrap=True)
        table.add_column(Text("Description", justify="center"), style="dark_cyan", justify="left", no_wrap=True)

        # 添加数据到表格
        for i, (key, value) in enumerate(magic_comment_desc_dic.items()):
            table.add_row(f"{i+1}", key, value)

        return table
    except Exception as e:
        logger.error(_('打印魔法注释说明表时出错: ') + str(e))  # 记录错误信息

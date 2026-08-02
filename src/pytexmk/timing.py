import datetime
import logging

from rich import box, print
from rich.table import Table
from rich.text import Text

from pytexmk.language import set_language
from pytexmk.ui_theme import console

logger = logging.getLogger(__name__)

_ = set_language("info_print")

total_len = 78


def time_count(fun, *args, **kwargs):
    try:
        time_start = datetime.datetime.now()  # noqa: DTZ005
        fun_return = fun(*args, **kwargs)
        time_end = datetime.datetime.now()  # noqa: DTZ005
        time_run = (time_end - time_start).total_seconds()
        return round(time_run, 4), fun_return
    except Exception as e:  # noqa: BLE001
        logger.error(
            _("执行函数 %(args)s 时出错: ") % {"args": {fun.__name__}} + str(e)
        )
        return None, None


def get_text_len(text):
    non_ascii_len = sum(1 for i in text if not i.isascii())
    text_len = len(text) + non_ascii_len
    return text_len


def time_print(start_time, runtime_dict):
    try:
        end_time = datetime.datetime.now()  # noqa: DTZ005
        run_time = end_time - start_time
        total_seconds = run_time.total_seconds()
        hours, remainder = divmod(int(total_seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        milliseconds = run_time.microseconds // 1000

        time_pytexmk = total_seconds

        time_LaTeX_list = [
            value
            for key, value in runtime_dict.items()
            if any(
                include_str in key
                for include_str in [
                    "PdfLaTeX",
                    "LuaLaTeX",
                    "XeLaTeX",
                    " 编译",
                    "宏包",
                    "运行",
                ]
            )
        ]

        if time_LaTeX_list:
            time_LaTeX = sum(time_LaTeX_list)
            time_python = total_seconds - time_LaTeX
            runtime_dict.update(
                {
                    _("LaTeX 编译时长"): time_LaTeX,
                    _("Python 运行时长"): time_python,
                    _("PyTeXMK 运行时长"): time_pytexmk,
                }
            )
        else:
            time_python = total_seconds
            runtime_dict.update(
                {_("Python 运行时长"): time_python, _("PyTeXMK 运行时长"): time_pytexmk}
            )

        max_whole_digits = max(
            len(str(int(value))) for value in runtime_dict.values()
        )
        formatted_times = {
            key: f"{value:0{max_whole_digits + 5}.4f} s"
            for key, value in runtime_dict.items()
        }
        runtime_dict.update(formatted_times)

        number_programmes_run = len(time_LaTeX_list)

        table = Table(
            show_header=True,
            header_style="bold dark_orange",
            box=box.ASCII_DOUBLE_HEAD,
            title=_("PyTeXMK 运行时长统计表"),
        )

        table.add_column("No.", justify="center", no_wrap=True)
        table.add_column(
            Text(_("运行项目"), justify="center"),
            style="cyan",
            justify="left",
            no_wrap=True,
        )
        table.add_column(_("运行时长"), style="green", justify="center", no_wrap=True)
        table.add_column("No.", justify="center", no_wrap=True)
        table.add_column(
            Text(_("运行项目"), justify="center"),
            style="cyan",
            justify="left",
            no_wrap=True,
        )
        table.add_column(_("运行时长"), style="green", justify="center", no_wrap=True)

        length = len(runtime_dict) / 2
        row_num = None

        if length - int(length) < 0.5:
            row_num = int(length)
        else:
            row_num = int(length) + 1

        name_target_list = list(runtime_dict.keys())

        for i in range(row_num):
            row_data = [
                f"{i + 1:02d}",
                name_target_list[i],
                runtime_dict[name_target_list[i]],
            ]
            if i + row_num < len(name_target_list):
                row_data.extend(
                    [
                        f"{i + 1 + row_num:02d}",
                        name_target_list[i + row_num],
                        runtime_dict[name_target_list[i + row_num]],
                    ]
                )
            else:
                row_data.extend(["", "", ""])
            table.add_row(*row_data)

        print("\n" + "=" * total_len + "\n")
        console.print(table)

        print(
            _("PyTeXMK 运行时长: ")
            + f"{hours} h {minutes} min {seconds} s {milliseconds} ms ({total_seconds:.3f} s total)"
        )
        print(
            _("运行 LaTeX 程序数目: ") + f"{number_programmes_run}"
        )
    except Exception as e:  # noqa: BLE001
        logger.error(_("打印运行时长统计表时出错: ") + str(e))

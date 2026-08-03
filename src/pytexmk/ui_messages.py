import logging

from rich import box
from rich.table import Table
from rich.text import Text

from pytexmk.language import set_language
from pytexmk.timing import get_text_len, total_len
from pytexmk.ui_theme import console

logger = logging.getLogger(__name__)

_ = set_language("ui_messages")


def print_message(message, state=None):
    if state is None:
        console.print(message)
        return
    if state == "additional":
        in_dec_chars = "X"
        out_dec_chars = "="
        in_dec_chars_style = "red on white"
        out_dec_chars_style = "blue bold"
        message_style = "red on white bold"
    elif state == "running":
        in_dec_chars = "X"
        out_dec_chars = "="
        in_dec_chars_style = "red on white"
        out_dec_chars_style = "yellow bold"
        message_style = "red on white bold"
    elif state == "success":
        in_dec_chars = "▓"
        out_dec_chars = "="
        in_dec_chars_style = "red on white"
        out_dec_chars_style = "green bold"
        message_style = "bold red on white"

    try:
        padding_size = total_len - get_text_len(message) - 4
        left_padding = padding_size // 2
        right_padding = padding_size - left_padding

        left_banner = in_dec_chars * left_padding
        right_banner = in_dec_chars * right_padding

        banner = (
            f"[{in_dec_chars_style}]{left_banner}[/{in_dec_chars_style}]"
            + f"[{message_style}]| {message} |[/{message_style}]"
            + f"[{in_dec_chars_style}]{right_banner}[/{in_dec_chars_style}]"
        )

        console.print("\n" + out_dec_chars * total_len, style=f"{out_dec_chars_style}")
        console.print(banner)
        console.print(out_dec_chars * total_len + "\n", style=f"{out_dec_chars_style}")
    except Exception as e:  # noqa: BLE001
        logger.error(_("打印模块信息时出错: ") + str(e))


def magic_comment_desc_table():
    magic_comment_desc_dic = {
        "% !TEX program = XeLaTeX": _("指定编译程序: XeLaTeX PdfLaTeX LuaLaTeX"),
        "% !TEX root = main.tex": _("指定待编译主文件名，仅支持根目录下的文件"),
        "% !TEX outdir = out_folder": _("指定编译结果存放位置，仅支持文件夹名称"),
        "% !TEX auxdir = aux_folder": _("指定辅助文件存放位置，仅支持文件夹名称"),
    }
    try:
        table = Table(
            show_header=True,
            header_style="bold dark_orange",
            box=box.ASCII_DOUBLE_HEAD,
            title=_("魔法注释说明表"),
        )

        table.add_column("No.", justify="center", no_wrap=True)
        table.add_column(
            Text("Magic Comment", justify="center"),
            style="cyan",
            justify="left",
            no_wrap=True,
        )
        table.add_column(
            Text("Description", justify="center"),
            style="dark_cyan",
            justify="left",
            no_wrap=True,
        )

        for i, (key, value) in enumerate(magic_comment_desc_dic.items()):
            table.add_row(f"{i + 1}", key, value)

        return table
    except Exception as e:  # noqa: BLE001
        logger.error(_("打印魔法注释说明表时出错: ") + str(e))

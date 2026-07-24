"""
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
 ···························································"Y88P"·····
 =======================================================================

 -----------------------------------------------------------------------
Author       : 焱铭
Date         : 2024-02-28 23:11:52 +0800
LastEditTime : 2025-07-23 22:30:00 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /PyTeXMK/src/pytexmk/__main__.py
Description  : PyTeXMK 命令行入口
 -----------------------------------------------------------------------
"""

# -*- coding: utf-8 -*-
import datetime
import sys
import traceback
import webbrowser

# rich 库（美化 CLI 输出）
from rich import print

from pytexmk.additional import MainFileOperation, MoveRemoveOperation, PdfFileOperation

# 辅助功能
from pytexmk.auxiliary_fun import (
    get_app_path,
    setup_console_encoding,
    setup_signal_handlers,
)
from pytexmk.check_version import UpdateChecker
from pytexmk.cli_args import (
    build_cli_args,
    is_tty,
    parse_args,
    standardize_name,
)
from pytexmk.compile import CompileLaTeX
from pytexmk.config import ConfigParser
from pytexmk.console import get_console
from pytexmk.constants import SUFFIXES_AUX, SUFFIXES_OUT
from pytexmk.engine_detect import auto_configure
from pytexmk.exceptions import PyTeXMKError

# 信息输出模块
from pytexmk.info_print import print_message, time_count, time_print
from pytexmk.language import set_language
from pytexmk.log_analysis import LogAnalysis

# 日志与语言配置
from pytexmk.logger_config import setup_logger

# 主要功能模块
from pytexmk.toolchain import ToolchainManager

# 版本信息
from pytexmk.version import __version__
from pytexmk.watcher import PvcMode
from pytexmk.workflow import handle_clean, handle_diff, setup_pdf_preview

UC = UpdateChecker(1, 6)
_ = set_language("__main__")


# --------------------------------------------------------------------------------
# 主程序
# --------------------------------------------------------------------------------
def main():
    start_time = datetime.datetime.now()

    setup_console_encoding()
    setup_signal_handlers()

    MFO = MainFileOperation()
    MRO = MoveRemoveOperation()
    PFO = PdfFileOperation()

    args = parse_args()

    non_interactive = args.non_interactive or not is_tty()
    CP = ConfigParser(interactive=not non_interactive)

    verbose = args.verbose
    logger = setup_logger(verbose)

    print(_("PyTeXMK 版本: %(args)s") % {"args": f"[i bold green]{__version__}[/i bold green]\n"})
    print(_("[bold green]PyTeXMK 开始运行...\n"))

    try:
        _main_internal(args, CP, MFO, MRO, PFO, start_time, logger, non_interactive)
    except PyTeXMKError as e:
        console = get_console()
        console.print(_("\n[bold red]错误: %(message)s[/bold red]") % {"message": e.message})
        sys.exit(e.exit_code)
    except KeyboardInterrupt:
        print(_("\n[bold yellow]用户中断操作[/bold yellow]"))
        sys.exit(130)
    except Exception as e:
        console = get_console()
        console.print(_("\n[bold red]未预期的错误: %(error)s[/bold red]") % {"error": e})
        console.print(_("[yellow]请将以下信息提交到 GitHub Issue 帮助我们改进：[/yellow]"))
        traceback.print_exc()
        sys.exit(1)
    finally:
        UC.check_for_updates()


def _main_internal(args, CP, MFO, MRO, PFO, start_time, logger, non_interactive):
    runtime_dict = {}

    magic_comments_keys = ["program", "root", "outdir", "auxdir", "bib", "index"]

    if args.readme:
        try:
            app_path = get_app_path()
            readme_path = app_path / "data" / "README.html"

            if readme_path.exists():
                print(_("[bold green]正在打开 README 文件..."))
                logger.info(_("README 本地路径: %(args)s") % {"args": f"file://{readme_path.resolve().as_posix()}"})
                webbrowser.open(f"file://{readme_path.resolve().as_posix()}")
            else:
                logger.error(_("README.html 文件未找到: ") + str(readme_path))
                import time

                time.sleep(60)
        except Exception as e:
            logger.error(_("打开 README 文件出错: ") + str(e))
        return

    logger.info("-" * 70)
    tex_files_in_root = MFO.get_suffix_files_in_dir(".", ".tex")
    main_files_in_root = MFO.find_tex_commands(tex_files_in_root)
    all_magic_comments = MFO.search_magic_comments(main_files_in_root, magic_comments_keys)

    logger.info("-" * 70)
    config_dict = CP.init_config_file()

    default_file = "main"
    compiled_program_display = "XeLaTeX"
    non_quiet = False
    outdir = "./Build/"
    auxdir = "./Auxiliary/"
    pdf_preview_file = None
    auto_detect = True
    timeout = 300
    run_count = 2
    shell_escape = True
    synctex = True

    if config_dict:
        # Priority: CLI > magic_comments > config > default
        if config_dict.get("default_file"):
            default_file = config_dict["default_file"]
            logger.info(_("通过配置文件设置默认文件为: ") + f"[bold cyan]{default_file}")
        # Priority: CLI > magic_comments > config > default
        if config_dict.get("compiled_program"):
            compiled_program_display = standardize_name(config_dict["compiled_program"])
            logger.info(_("通过配置文件设置编译器为: ") + f"[bold cyan]{compiled_program_display}")
        # Priority: CLI > magic_comments > config > default
        if config_dict.get("non_quiet") is not None:
            non_quiet = config_dict["non_quiet"]
        elif config_dict.get("quiet_mode") is not None:
            non_quiet = not config_dict["quiet_mode"]
        # Priority: output > folder > default
        if config_dict.get("folder"):
            folder_config = config_dict["folder"]
            if folder_config.get("outdir"):
                outdir = folder_config["outdir"]
            if folder_config.get("auxdir"):
                auxdir = folder_config["auxdir"]
        if config_dict.get("output"):
            output_config = config_dict["output"]
            if output_config.get("outdir"):
                outdir = output_config["outdir"]
            if output_config.get("auxdir"):
                auxdir = output_config["auxdir"]
        # Priority: CLI > magic_comments > config > default
        if config_dict.get("engine"):
            engine_config = config_dict["engine"]
            if engine_config.get("auto_detect") is not None:
                auto_detect = engine_config["auto_detect"]
            if engine_config.get("timeout"):
                timeout = engine_config["timeout"]
        # Priority: CLI > magic_comments > config > default
        if config_dict.get("compilation"):
            comp_config = config_dict["compilation"]
            if comp_config.get("default_run_count"):
                run_count = comp_config["default_run_count"]
            if comp_config.get("shell_escape") is not None:
                shell_escape = comp_config["shell_escape"]
            if comp_config.get("synctex") is not None:
                synctex = comp_config["synctex"]
            if comp_config.get("quiet") is not None:
                non_quiet = not comp_config["quiet"]

    # Priority: CLI > magic_comments > config > default
    if args.non_quiet:
        non_quiet = True
    if args.final_outdir:
        outdir = args.final_outdir
    if args.auxdir:
        auxdir = args.auxdir
    if args.timeout is not None:
        timeout = args.timeout
    if args.run_count is not None:
        run_count = args.run_count
    if args.shell_escape is not None:
        shell_escape = args.shell_escape
    if args.synctex is not None:
        synctex = args.synctex
    if args.auto_enable is not None:
        auto_detect = args.auto_enable

    if non_quiet:
        logger.info(_("非安静模式运行"))

    if args.pdf_preview and args.pdf_preview != "preview after compile" and not args.document:
        pdf_files_in_outdir = MFO.get_suffix_files_in_dir(outdir, ".pdf")
        pdf_preview_file = MFO.check_project_name(pdf_files_in_outdir, args.pdf_preview, ".pdf")
        PFO.pdf_preview(pdf_preview_file, outdir)
        return

    project_name = ""
    magic_comments = {}
    is_diff_mode = (args.LaTeXDiff is not None) or (args.LaTeXDiff_compile is not None)

    if is_diff_mode:
        pass
    elif not args.readme:
        project_name = MFO.get_main_file(default_file, args.document, main_files_in_root, all_magic_comments)

    if all_magic_comments and project_name:
        for key, values in all_magic_comments.items():
            if key == "root":
                continue
            if project_name in values:
                magic_comments[key] = values[project_name]
                logger.info(_("提取魔法注释: ") + f"{project_name}.tex ==> % !TEX {key} = {values[project_name]}")

    if magic_comments.get("outdir"):
        outdir = magic_comments["outdir"]
        print(_("通过魔法注释设置输出目录: ") + f"[bold cyan]{outdir}[/bold cyan]")
    if magic_comments.get("auxdir"):
        auxdir = magic_comments["auxdir"]
        print(_("通过魔法注释设置辅助目录: ") + f"[bold cyan]{auxdir}[/bold cyan]")

    if is_diff_mode:
        handle_diff(
            args,
            config_dict,
            magic_comments,
            MFO,
            MRO,
            PFO,
            main_files_in_root,
            start_time,
            runtime_dict,
            SUFFIXES_OUT,
            SUFFIXES_AUX,
            outdir,
            auxdir,
        )
        if runtime_dict:
            time_print(start_time, runtime_dict)
        return

    if not project_name:
        return

    out_files = [f"{project_name}{suffix}" for suffix in SUFFIXES_OUT]
    aux_files = [f"{project_name}{suffix}" for suffix in SUFFIXES_AUX]

    if args.clean or args.Clean or args.clean_any or args.Clean_any:
        handle_clean(
            args, None, MRO, project_name, outdir, auxdir, SUFFIXES_OUT, SUFFIXES_AUX, start_time, runtime_dict
        )
        return

    if args.pdf_repair:
        runtime_pdf_repair = time_count(PFO.pdf_repair, project_name, ".", outdir)
        runtime_dict[_("修复 PDF 文件")] = runtime_pdf_repair
        if runtime_dict:
            time_print(start_time, runtime_dict)
        return

    toolchain = ToolchainManager()
    toolchain.detect_all()

    cli_args_for_auto = build_cli_args(args)

    if auto_detect:
        auto_config = auto_configure(
            project_name=project_name,
            cli_args=cli_args_for_auto,
            config=config_dict,
            toolchain_manager=toolchain,
            magic_comments=magic_comments if magic_comments else None,
        )
        selected_engine = auto_config["engine"]
        selected_bib = auto_config["bib_tool"]
        selected_index = auto_config["index_tool"]
        if auto_config["outdir"] and not args.final_outdir and not magic_comments.get("outdir"):
            outdir = auto_config["outdir"]
        if auto_config["auxdir"] and not args.auxdir and not magic_comments.get("auxdir"):
            auxdir = auto_config["auxdir"]
    else:
        if args.XeLaTeX:
            selected_engine = "xelatex"
        elif args.PdfLaTeX:
            selected_engine = "pdflatex"
        elif args.LuaLaTeX:
            selected_engine = "lualatex"
        elif args.engine:
            selected_engine = args.engine
        elif magic_comments.get("program"):
            selected_engine = magic_comments["program"].lower()
        elif config_dict.get("compiled_program"):
            selected_engine = config_dict["compiled_program"].lower()
        else:
            selected_engine = "xelatex"

        if args.bib and args.bib != "auto":
            selected_bib = args.bib
        elif magic_comments.get("bib"):
            selected_bib = magic_comments["bib"]
        else:
            selected_bib = None

        if args.index and args.index != "auto":
            selected_index = args.index
        elif magic_comments.get("index"):
            selected_index = magic_comments["index"]
        else:
            selected_index = "makeindex"

    if args.pvc:
        pvc_preview = args.pvc_preview or args.open_pdf or (args.pdf_preview == "preview after compile")

        compiler_kwargs = {
            "program": selected_engine,
            "bibtex_tool": selected_bib,
            "index_tool": selected_index,
            "outdir": outdir,
            "auxdir": auxdir,
            "run_count": run_count,
            "draft": args.draft,
            "quiet": not non_quiet,
            "shell_escape": shell_escape,
            "synctex": synctex,
            "timeout": timeout,
            "auto_detect": auto_detect,
        }

        pvc = PvcMode(
            project_dir=".",
            project_name=project_name,
            compiler_kwargs=compiler_kwargs,
            auto_open_preview=pvc_preview,
        )
        pvc.start()

        if runtime_dict:
            time_print(start_time, runtime_dict)
        return

    print_message(_("开始预处理"), "additional")
    print(_("检测并移动辅助文件到根目录..."))
    runtime_move_aux_root = time_count(MRO.move_specific_files, aux_files, auxdir, ".")
    runtime_dict[_("辅助文件->根目录")] = runtime_move_aux_root

    compiler = CompileLaTeX(
        project_name=project_name,
        program=selected_engine,
        bibtex_tool=selected_bib,
        index_tool=selected_index,
        outdir=outdir,
        auxdir=auxdir,
        run_count=run_count,
        draft=args.draft,
        quiet=not non_quiet,
        shell_escape=shell_escape,
        synctex=synctex,
        timeout=timeout,
        auto_detect=auto_detect,
    )

    compiler.compile_tex()

    print_message(_("日志分析器"), "additional")
    try:
        log_analysis = LogAnalysis(project_name)
        log_analysis.parse_all()
        log_analysis.view_log()
    except Exception as e:
        logger.warning(_("日志分析失败: ") + str(e))

    print_message(_("开始后处理"), "additional")
    print(_("移动结果文件到输出目录..."))
    runtime_move_out_outdir = time_count(MRO.move_specific_files, out_files, ".", outdir)
    runtime_dict[_("结果文件->输出目录")] = runtime_move_out_outdir
    print(_("移动辅助文件到辅助目录..."))
    runtime_move_aux_auxdir = time_count(MRO.move_specific_files, aux_files, ".", auxdir)
    runtime_dict[_("辅助文件->辅助目录")] = runtime_move_aux_auxdir

    setup_pdf_preview(compiler, args, project_name, outdir, PFO)

    if runtime_dict:
        time_print(start_time, runtime_dict)


if __name__ == "__main__":
    main()

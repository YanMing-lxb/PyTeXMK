"""PyTeXMK CLI 分派工作流：从 __main__ 下沉到独立模块。"""


def run_workflow(args):
    import datetime
    import webbrowser

    import pytexlogs
    from rich import print

    from pytexmk.cli.check_version import UpdateChecker

    from ..config import ConfigParser
    from ..file_ops import FileMoveRemoveManager
    from ..language import set_language
    from ..latexdiff import LaTeXDiff_Aux
    from ..lifecycle import exit_pytexmk
    from ..logger_config import setup_logger
    from ..paths import get_app_path
    from ..pdf_tools import PdfFileOperation
    from ..compile_engine import RUN, LaTeXDiffRUN
    from ..tex_project import MainFileOperation
    from ..timing import time_count, time_print
    from ..ui_messages import print_message
    from ..version import __version__

    _ = set_language("cli_workflow")

    from pathlib import Path
    from pytexmk.ui_theme import console

    def standardize_name(compiled_program):
        standard_names = {
            "xelatex": "XeLaTeX",
            "pdflatex": "PdfLaTeX",
            "lualatex": "LuaLaTeX",
        }
        return standard_names.get(compiled_program.lower(), compiled_program)

    start_time = datetime.datetime.now()  # noqa: DTZ005

    MFO = MainFileOperation()
    MRO = FileMoveRemoveManager()
    PFO = PdfFileOperation()
    CP = ConfigParser()

    verbose = False

    default_file = "main"
    compiled_program = "XeLaTeX"
    non_quiet = False

    pdf_preview_status = "preview after compile"
    pdf_viewer = "default"

    outdir = "./Build/"
    auxdir = "./Auxiliary/"

    old_tex_file = "old_file"
    new_tex_file = "new_file"
    diff_tex_file = "LaTeXDiff"

    suffixes_out = [".pdf", ".synctex.gz"]
    suffixes_aux = [
        ".log", ".blg", ".ilg",
        ".aux", ".bbl", ".xml",
        ".toc", ".lof", ".lot",
        ".out", ".bcf", ".idx", ".ind", ".nlo", ".nls", ".ist", ".glo", ".gls",
        ".bak", ".spl", ".ent-x", ".tmp", ".ltx", ".los", ".lol", ".loc",
        ".listing", ".gz", ".userbak", ".nav", ".snm", ".vrb", ".fls", ".xdv",
        ".fdb_latexmk", ".run.xml",
    ]

    magic_comments_keys = ["program", "root", "outdir", "auxdir"]
    project_name = ""
    runtime_dict = {}
    magic_comments = {}

    print(_("PyTeXMK 版本: %(args)s") % {"args": f"[i bold green]{__version__}[/i bold green]\n"})
    print(_("[bold green]PyTeXMK 开始运行...\n"))

    if args.verbose:
        verbose = args.verbose
    logger = setup_logger(verbose)

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
        except Exception as e:  # noqa: BLE001
            logger.error(_("打开 README 文件出错: ") + str(e))
        finally:
            exit_pytexmk()

    logger.info("-" * 70)
    tex_files_in_root = MFO.get_suffix_files_in_dir(".", ".tex")
    main_files_in_root = MFO.find_tex_commands(tex_files_in_root)
    all_magic_comments = MFO.search_magic_comments(main_files_in_root, magic_comments_keys)

    logger.info("-" * 70)
    config_dict = CP.init_config_file()

    if config_dict["default_file"]:
        default_file = config_dict["default_file"]
        logger.info(_("通过配置文件设置默认文件为: ") + f"[bold cyan]{default_file}")
    if config_dict["compiled_program"]:
        compiled_program = standardize_name(config_dict["compiled_program"])
        logger.info(_("通过配置文件设置编译器为: ") + f"[bold cyan]{compiled_program}")
    if config_dict["quiet_mode"]:
        non_quiet = False
        logger.info(_("通过配置文件设置安静模式为: ") + f"[bold cyan]{config_dict['quiet_mode']}")

    if config_dict["folder"]:
        if config_dict["folder"]["outdir"]:
            outdir = config_dict["folder"]["outdir"]
            logger.info(_("通过配置文件设置输出目录为: ") + f"[bold cyan]{outdir}")
        if config_dict["folder"]["auxdir"]:
            auxdir = config_dict["folder"]["auxdir"]
            logger.info(_("通过配置文件设置辅助目录为: ") + f"[bold cyan]{auxdir}")

    if config_dict["pdf"]:
        if config_dict["pdf"]["pdf_preview_status"]:
            pdf_preview_status = config_dict["pdf"]["pdf_preview_status"]
            logger.info(_("通过配置文件设置 PDF 预览为: ") + f"[bold cyan]{pdf_preview_status}")
        if config_dict["pdf"]["pdf_viewer"]:
            pdf_viewer = config_dict["pdf"]["pdf_viewer"]
            PFO.set_viewer(pdf_viewer)
            logger.info(_("通过配置文件设置 PDF 预览器为: ") + f"[bold cyan]{pdf_viewer}")

    if config_dict["index"]:
        if config_dict["index"]["index_style_file"]:
            index_style_file = config_dict["index"]["index_style_file"]
            logger.info(_("通过配置文件设置索引文件名为: ") + f"[bold cyan]{index_style_file}")
        if config_dict["index"]["input_suffix"]:
            input_suffix = config_dict["index"]["input_suffix"]
            logger.info(_("通过配置文件设置索引输入文件后缀为: ") + f"[bold cyan]{input_suffix}")
        if config_dict["index"]["output_suffix"]:
            output_suffix = config_dict["index"]["output_suffix"]
            logger.info(_("通过配置文件设置索引输出文件后缀为: ") + f"[bold cyan]{output_suffix}")

    if config_dict["latexdiff"]:
        if config_dict["latexdiff"]["old_tex_file"]:
            old_tex_file = config_dict["latexdiff"]["old_tex_file"]
            logger.info(_("通过配置文件设置 LaTeXDiff 旧文件为: ") + f"[bold cyan]{old_tex_file}")
        if config_dict["latexdiff"]["new_tex_file"]:
            new_tex_file = config_dict["latexdiff"]["new_tex_file"]
            logger.info(_("通过配置文件设置 LaTeXDiff 新文件为: ") + f"[bold cyan]{new_tex_file}")
        if config_dict["latexdiff"]["diff_tex_file"]:
            diff_tex_file = config_dict["latexdiff"]["diff_tex_file"]
            logger.info(_("通过配置文件设置 LaTeXDiff 对比文件为: ") + f"[bold cyan]{diff_tex_file}")

    logger.info("-" * 70)
    if args.non_quiet:
        non_quiet = args.non_quiet
    if non_quiet:
        logger.info(_("非安静模式运行"))

    pdf_preview_status = args.pdf_preview
    if pdf_preview_status and pdf_preview_status != "preview after compile" and not args.document:
        pdf_files_in_outdir = MFO.get_suffix_files_in_dir(outdir, ".pdf")
        pdf_preview_status = MFO.check_project_name(pdf_files_in_outdir, pdf_preview_status, ".pdf")
        PFO.pdf_preview(pdf_preview_status, outdir)
        exit_pytexmk()

    if args.LaTeXDiff or args.LaTeXDiff_compile or args.LaTeXDiff == [] or args.LaTeXDiff_compile == []:
        if args.LaTeXDiff == [] or args.LaTeXDiff_compile == []:
            print(_("命令行未指定 LaTeXDiff 相关参数"))
            if new_tex_file and old_tex_file:
                print(_("根据配置文件设置 LaTeXDiff 新 TeX 文件为: ") + f"[bold cyan]{new_tex_file}")
                print(_("根据配置文件设置 LaTeXDiff 旧 TeX 文件为: ") + f"[bold cyan]{old_tex_file}")
            else:
                logger.error(_("请指定在命令行或配置文件中指定两个新旧 TeX 文件"))
                exit_pytexmk()

        if args.LaTeXDiff and len(args.LaTeXDiff) != 2 or args.LaTeXDiff_compile and len(args.LaTeXDiff_compile) != 2:
            logger.error(_("请同时指定 LaTeXDiff 所需的新旧 TeX 文件"))
            exit_pytexmk()
        if args.LaTeXDiff and len(args.LaTeXDiff) == 2:
            old_tex_file, new_tex_file = args.LaTeXDiff
        if args.LaTeXDiff_compile and len(args.LaTeXDiff_compile) == 2:
            old_tex_file, new_tex_file = args.LaTeXDiff_compile

        old_tex_file = MFO.check_project_name(main_files_in_root, old_tex_file, ".tex")
        new_tex_file = MFO.check_project_name(main_files_in_root, new_tex_file, ".tex")
    elif not args.readme:
        project_name = MFO.get_main_file(default_file, args.document, main_files_in_root, all_magic_comments)

    if all_magic_comments:
        for key, values in all_magic_comments.items():
            if key == "root":
                continue
            if project_name in values:
                magic_comments[key] = values[project_name]
                logger.info(_("提取魔法注释: ") + f"{project_name}.tex ==> % !TEX {key} = {values[project_name]}")

    if args.XeLaTeX:
        compiled_program = "XeLaTeX"
    elif args.PdfLaTeX:
        compiled_program = "PdfLaTeX"
    elif args.LuaLaTeX:
        compiled_program = "LuaLaTeX"
    elif magic_comments.get("program"):
        compiled_program = standardize_name(magic_comments["program"])
        print(_("通过魔法注释设置程序为: ") + f"[bold cyan]{compiled_program}")

    if magic_comments.get("outdir"):
        outdir = magic_comments["outdir"]
        print(_("通过魔法注释设置输出目录: ") + f"[bold cyan]{outdir}[/bold cyan]")
    if magic_comments.get("auxdir"):
        auxdir = magic_comments["auxdir"]
        print(_("通过魔法注释设置辅助目录: ") + f"[bold cyan]{auxdir}[/bold cyan]")

    out_files = [f"{project_name}{suffix}" for suffix in suffixes_out]
    aux_files = [f"{project_name}{suffix}" for suffix in suffixes_aux]
    aux_regex_files = [f".*\\{suffix}" for suffix in suffixes_aux]

    if args.clean_any:
        runtime_remove_aux_matched_auxdir, _ret = time_count(MRO.remove_matched_files, aux_regex_files, ".")
        runtime_dict[_("清除所有的辅助文件")] = runtime_remove_aux_matched_auxdir
        print(_("[bold green]已完成清除所有带辅助文件后缀的文件的指令"))
        if runtime_dict:
            time_print(start_time, runtime_dict)
        return
    elif args.Clean_any:
        runtime_remove_aux_matched_auxdir, _ret = time_count(MRO.remove_matched_files, aux_regex_files, ".")
        runtime_dict[_("清除所有的辅助文件")] = runtime_remove_aux_matched_auxdir
        runtime_remove_out_outdir, _ret = time_count(MRO.remove_specific_files, out_files, outdir)
        runtime_dict[_("清除文件夹内输出文件")] = runtime_remove_out_outdir
        print(_("[bold green]已完成清除所有带辅助文件后缀的文件和主文件输出文件的指令"))
        if runtime_dict:
            time_print(start_time, runtime_dict)
        return

    if args.LaTeXDiff or args.LaTeXDiff_compile or args.LaTeXDiff == [] or args.LaTeXDiff_compile == []:
        if not old_tex_file or not new_tex_file:
            logger.error(_("请指定在命令行或配置文件中指定两个新旧 TeX 文件"))
            exit_pytexmk()

        if old_tex_file == new_tex_file:
            logger.error(_("不能对同一个文件进行比较, 请检查文件名是否正确"))
            exit_pytexmk()

        print_message(_("LaTeXDiff 预处理"), "additional")

        LDA = LaTeXDiff_Aux(outdir, suffixes_out, suffixes_aux, auxdir)
        if LDA.check_aux_files(old_tex_file):
            logger.info(_("%(args)s 的辅助文件存在") % {"args": old_tex_file})
        else:
            logger.error(_("%(args)s 的辅助文件不存在, 请检查编译") % {"args": old_tex_file})
            exit_pytexmk()
        if LDA.check_aux_files(new_tex_file):
            logger.info(_("%(args)s 的辅助文件存在") % {"args": new_tex_file})
        else:
            logger.error(_("%(args)s 的辅助文件不存在, 请检查编译") % {"args": new_tex_file})
            exit_pytexmk()

        old_tex_file_flatten = LDA.flatten_Latex(old_tex_file)
        new_tex_file_flatten = LDA.flatten_Latex(new_tex_file)
        runtime_move_matched_files, _ret = time_count(MRO.move_matched_files, aux_regex_files, auxdir, ".")
        runtime_dict[_("全辅助文件->根目录")] = runtime_move_matched_files
        latex_diff_style = input(
            _(
                "请输入 LaTeXDiff 的显示风格：\n"
                "  1 - 显示参考文献/符号说明的修改\n"
                "  2 - 不显示参考文献/符号说明的修改\n"
                "请选择 (1 或者 2): "
            )
        )

        try:
            print_message(_("LaTeXDiff 运行"), "running")
            aux_suffixes_exit = []
            if latex_diff_style == "1":
                for aux_suffix in [".bbl", ".nls", ".gls", ".idx"]:
                    aux_file_exit = LDA.aux_files_both_exist(old_tex_file, new_tex_file, aux_suffix)
                    aux_suffixes_exit.append(aux_file_exit) if aux_file_exit else None
                for aux_suffix in aux_suffixes_exit:
                    runtime_compile_LaTeXDiff, _ret = time_count(
                        LDA.compile_LaTeXDiff, old_tex_file, new_tex_file, diff_tex_file, aux_suffix
                    )

            runtime_compile_LaTeXDiff, _ret = time_count(
                LDA.compile_LaTeXDiff, old_tex_file_flatten, new_tex_file_flatten, diff_tex_file, ".tex"
            )
            runtime_dict[_("LaTeXDiff 运行")] = runtime_compile_LaTeXDiff

            print_message(_("LaTeXDiff 后处理"), "additional")
            print(_("删除 Flatten 后的文件..."))
            runtime_remove_flatten_root, _ret = time_count(
                MRO.remove_specific_files, [f"{old_tex_file_flatten}.tex", f"{new_tex_file_flatten}.tex"], "."
            )
            runtime_dict[_("清除文件夹内输出文件")] = runtime_remove_flatten_root

            if args.LaTeXDiff_compile or args.LaTeXDiff_compile == []:
                out_files = [f"{diff_tex_file}{suffix}" for suffix in suffixes_out]
                print_message(_("开始预处理命令"), "additional")
                if latex_diff_style == "1":
                    LaTeXDiffRUN(
                        runtime_dict, diff_tex_file, compiled_program, out_files, aux_files,
                        outdir, auxdir, non_quiet, args.draft,
                    )
                elif latex_diff_style == "2":
                    RUN(
                        runtime_dict, diff_tex_file, compiled_program, out_files, aux_files,
                        outdir, auxdir, non_quiet, args.draft,
                    )
                else:
                    logger.error(
                        _(
                            "请输入正确的选项 (1 或者 2)\n"
                            "  1 - 显示参考文献/符号说明的修改\n"
                            "  2 - 不显示参考文献/符号说明的修改"
                        )
                    )
                print_message(_("开始后处理"), "additional")

                print(_("移动结果文件到输出目录..."))
                runtime_move_out_outdir, _ret = time_count(MRO.move_specific_files, out_files, ".", outdir)
                runtime_dict[_("结果文件->输出目录")] = runtime_move_out_outdir
        except Exception as e:  # noqa: BLE001
            logger.error(_("LaTeXDiff 编译出错: ") + str(e))
            exit_pytexmk()
        finally:
            runtime_move_matched_files, _ret = time_count(MRO.move_matched_files, aux_regex_files, ".", auxdir)
            runtime_dict[_("辅助文件->辅助目录")] = runtime_move_matched_files

    elif project_name:
        if args.clean:
            runtime_remove_aux_auxdir, _ret = time_count(MRO.remove_specific_files, aux_files, auxdir)
            runtime_dict[_("清除文件夹内辅助文件")] = runtime_remove_aux_auxdir
            runtime_remove_aux_root, _ret = time_count(MRO.remove_specific_files, aux_files, ".")
            runtime_dict[_("清除根目录内辅助文件")] = runtime_remove_aux_root
            print(_("[bold green]已完成清除所有主文件的辅助文件的指令"))
        elif args.Clean:
            runtime_remove_aux_auxdir, _ret = time_count(MRO.remove_specific_files, aux_files, auxdir)
            runtime_dict[_("清除文件夹内辅助文件")] = runtime_remove_aux_auxdir
            runtime_remove_aux_root, _ret = time_count(MRO.remove_specific_files, aux_files, ".")
            runtime_dict[_("清除根目录内辅助文件")] = runtime_remove_aux_root
            runtime_remove_out_outdir, _ret = time_count(MRO.remove_specific_files, out_files, outdir)
            runtime_dict[_("清除文件夹内输出文件")] = runtime_remove_out_outdir
            print(_("[bold green]已完成清除所有主文件的辅助文件和输出文件的指令"))
        elif args.pdf_repair:
            runtime_pdf_repair, _ret = time_count(PFO.pdf_repair, project_name, ".", outdir)
            runtime_dict[_("修复 PDF 文件")] = runtime_pdf_repair
        else:
            print_message(_("开始预处理"), "additional")
            runtime_move_aux_root, aux_moved_count = time_count(MRO.move_specific_files, aux_files, auxdir, ".")
            runtime_dict[_("辅助文件->根目录")] = runtime_move_aux_root

            aux_exist_count = sum(1 for f in aux_files if Path(f).exists())
            if aux_exist_count == 0:
                console.print("[green]" + _("未检测到已有辅助文件，进行初始化") + "[/green]")
            else:
                console.print("[green]" + _("已检测到 %(n)s 个已有辅助文件") % {"n": aux_exist_count} + "[/green]")

            if aux_moved_count == 0:
                console.print("[green]" + _("没有检测到可迁移的辅助文件") + "[/green]")
            else:
                console.print("[yellow]" + _("已移动 %(n)s 个辅助文件到项目根目录") % {"n": aux_moved_count} + "[/yellow]")

            RUN(
                runtime_dict, project_name, compiled_program, out_files, aux_files,
                outdir, auxdir, non_quiet, args.draft,
            )

            print_message(_("开始后处理"), "additional")

            print("[yellow]" + _("移动结果文件到输出目录...") + "[/yellow]")
            runtime_move_out_outdir, _ret = time_count(MRO.move_specific_files, out_files, ".", outdir)
            runtime_dict[_("结果文件->输出目录")] = runtime_move_out_outdir

            print("[yellow]" + _("移动辅助文件到辅助目录...") + "[/yellow]")
            runtime_move_aux_auxdir, _ret = time_count(MRO.move_specific_files, aux_files, ".", auxdir)
            runtime_dict[_("辅助文件->辅助目录")] = runtime_move_aux_auxdir

            pytexlogs.run_log_pipeline(
                project_name, auxdir, root_file=project_name,
                pytexmk_version=__version__,
                ref_tracker_translate_fn=set_language("log_parser"),
            )

    if pdf_preview_status == "preview after compile":
        PFO.pdf_preview(project_name, outdir)
        exit_pytexmk()

    if runtime_dict:
        time_print(start_time, runtime_dict)

    UC = UpdateChecker(1, 6)
    UC.check_for_updates()

"""PyTeXMK CLI 上下文解析：子项目定位、配置合并与魔法注释覆盖。"""

import os

from rich import print

from ..config import ConfigParser
from ..language import set_language
from ..lifecycle import EXIT_PROJECT_NOT_FOUND, exit_pytexmk
from ..tex_project import standardize_name
from .cli_state import (
    MAGIC_COMMENT_KEYS,
    PREVIEW_AFTER_COMPILE,
    SUFFIXES_AUX,
    SUFFIXES_OUT,
    WorkflowState,
)

_ = set_language("cli_workflow")


def build(args, cp: ConfigParser, logger) -> WorkflowState:
    """定位本次运行上下文，并完成「配置文件」这一层的参数合并。

    依次完成：子项目解析 → 进入工作根目录 → 扫描主文件与魔法注释 →
    合并配置文件参数 → 合并命令行参数 → （可选）单次 PDF 预览后退出。
    """
    from ..context import ContextResolver, ProjectNotFoundError

    state = WorkflowState(args=args, logger=logger)

    try:
        ctx = ContextResolver(cp).resolve(args)
    except ProjectNotFoundError as e:
        logger.error(_("未找到子项目: ") + f"[bold cyan]{e.args[0]}[/bold cyan]")
        logger.warning(_("请先运行 pytexmk -ls 同步子项目清单, 或检查根配置 \\[subprojects\\] 段"))
        exit_pytexmk(EXIT_PROJECT_NOT_FOUND)

    state.config_dict = ctx.config
    if ctx.subproject and args.verbose:
        logger.info(_("子项目调用: 忽略子项目目录下的本地 .pytexmkrc, 以根配置为准"))

    # 进入工作根目录：用户终端 cwd 不变，编译流程在子项目/根目录内执行
    os.chdir(ctx.work_root)

    logger.info("-" * 70)
    tex_files_in_root = state.mfo.get_suffix_files_in_dir(".", ".tex")
    state.main_files_in_root = state.mfo.find_tex_commands(tex_files_in_root)
    state.all_magic_comments = state.mfo.search_magic_comments(state.main_files_in_root, MAGIC_COMMENT_KEYS)

    _apply_config_file(state)

    logger.info("-" * 70)
    if args.non_quiet:
        state.non_quiet = args.non_quiet
    if state.non_quiet:
        logger.info(_("非安静模式运行"))

    _apply_pdf_preview(state)
    return state


def resolve_target(args, state: WorkflowState) -> None:
    """决定本次要处理的目标：LaTeXDiff 新旧文件对，或待编译的主文件名。"""
    if state.is_latexdiff:
        _resolve_latexdiff_target(state)
    else:
        state.project_name = state.mfo.get_main_file(
            state.default_file, args.document, state.main_files_in_root, state.all_magic_comments
        )


def apply_magic_comments(state: WorkflowState) -> None:
    """用魔法注释覆盖程序与目录设置，并派生出本次运行的文件清单。"""
    logger = state.logger

    if state.all_magic_comments:
        for key, values in state.all_magic_comments.items():
            if key == "root":
                continue
            if state.project_name in values:
                state.magic_comments[key] = values[state.project_name]
                logger.info(
                    _("提取魔法注释: ") + f"{state.project_name}.tex ==> % !TEX {key} = {values[state.project_name]}"
                )

    if state.args.XeLaTeX:
        state.compiled_program = "XeLaTeX"
    elif state.args.PdfLaTeX:
        state.compiled_program = "PdfLaTeX"
    elif state.args.LuaLaTeX:
        state.compiled_program = "LuaLaTeX"
    elif state.magic_comments.get("program"):
        state.compiled_program = standardize_name(state.magic_comments["program"])
        print(_("通过魔法注释设置程序为: ") + f"[bold cyan]{state.compiled_program}")

    if state.magic_comments.get("outdir"):
        state.outdir = state.magic_comments["outdir"]
        print(_("通过魔法注释设置输出目录: ") + f"[bold cyan]{state.outdir}[/bold cyan]")
    if state.magic_comments.get("auxdir"):
        state.auxdir = state.magic_comments["auxdir"]
        print(_("通过魔法注释设置辅助目录: ") + f"[bold cyan]{state.auxdir}[/bold cyan]")

    state.out_files = [f"{state.project_name}{suffix}" for suffix in SUFFIXES_OUT]
    state.aux_files = [f"{state.project_name}{suffix}" for suffix in SUFFIXES_AUX]
    state.aux_regex_files = [f".*\\{suffix}" for suffix in SUFFIXES_AUX]


def _apply_config_file(state: WorkflowState) -> None:
    """把配置文件中的取值合并进运行时参数（优先级：内置默认值 < 配置文件）。"""
    logger = state.logger
    config_dict = state.config_dict

    if config_dict["default_file"]:
        state.default_file = config_dict["default_file"]
        logger.info(_("通过配置文件设置默认文件为: ") + f"[bold cyan]{state.default_file}")
    if config_dict["compiled_program"]:
        state.compiled_program = standardize_name(config_dict["compiled_program"])
        logger.info(_("通过配置文件设置编译器为: ") + f"[bold cyan]{state.compiled_program}")
    if config_dict["quiet_mode"]:
        state.non_quiet = False
        logger.info(_("通过配置文件设置安静模式为: ") + f"[bold cyan]{config_dict['quiet_mode']}")

    if config_dict["folder"]:
        if config_dict["folder"]["outdir"]:
            state.outdir = config_dict["folder"]["outdir"]
            logger.info(_("通过配置文件设置输出目录为: ") + f"[bold cyan]{state.outdir}")
        if config_dict["folder"]["auxdir"]:
            state.auxdir = config_dict["folder"]["auxdir"]
            logger.info(_("通过配置文件设置辅助目录为: ") + f"[bold cyan]{state.auxdir}")

    if config_dict["pdf"]:
        if config_dict["pdf"]["pdf_preview_status"]:
            state.preview_after_compile = True
            logger.info(
                _("通过配置文件设置 PDF 预览为: ") + f"[bold cyan]{config_dict['pdf']['pdf_preview_status']}"
            )
        if config_dict["pdf"]["pdf_viewer"]:
            state.pfo.set_viewer(config_dict["pdf"]["pdf_viewer"])
            logger.info(_("通过配置文件设置 PDF 预览器为: ") + f"[bold cyan]{config_dict['pdf']['pdf_viewer']}")

    # [index] 段参数（index_style_file / input_suffix / output_suffix）暂未接入运行时：
    # glossaries 输入后缀由 .aux 动态解析多值，单一后缀语义不成立；
    # 其余索引系统后缀由 detection._INDEX_REGISTRY 硬编码统一管理。
    # 若未来需要让用户可覆盖，应接通到 _INDEX_REGISTRY 的规则元数据而非在此处读取。
    if config_dict["latexdiff"]:
        if config_dict["latexdiff"]["old_tex_file"]:
            state.old_tex_file = config_dict["latexdiff"]["old_tex_file"]
            logger.info(_("通过配置文件设置 LaTeXDiff 旧文件为: ") + f"[bold cyan]{state.old_tex_file}")
        if config_dict["latexdiff"]["new_tex_file"]:
            state.new_tex_file = config_dict["latexdiff"]["new_tex_file"]
            logger.info(_("通过配置文件设置 LaTeXDiff 新文件为: ") + f"[bold cyan]{state.new_tex_file}")
        if config_dict["latexdiff"]["diff_tex_file"]:
            state.diff_tex_file = config_dict["latexdiff"]["diff_tex_file"]
            logger.info(_("通过配置文件设置 LaTeXDiff 对比文件为: ") + f"[bold cyan]{state.diff_tex_file}")


def _apply_pdf_preview(state: WorkflowState) -> None:
    """合并命令行 -pv 语义：给出文件名则预览该文件后退出，否则标记编译后预览。"""
    args = state.args
    if args.pdf_preview is None:
        return

    # 命令行显式给出 -pv，以命令行为准；-pv FILE 只做一次预览，不触发编译后预览
    state.preview_after_compile = False
    if args.pdf_preview == PREVIEW_AFTER_COMPILE:
        state.preview_after_compile = True
        return
    if not args.pdf_preview or args.document:
        return

    pdf_files_in_outdir = state.mfo.get_suffix_files_in_dir(state.outdir, ".pdf")
    target = state.mfo.check_project_name(pdf_files_in_outdir, args.pdf_preview, ".pdf")
    state.pfo.pdf_preview(target, state.outdir)
    exit_pytexmk()


def _resolve_latexdiff_target(state: WorkflowState) -> None:
    """校验并解析 LaTeXDiff 的两个待比较 TeX 文件（命令行优先，其次配置文件）。"""
    args, logger = state.args, state.logger

    if args.LaTeXDiff == [] or args.LaTeXDiff_compile == []:
        print(_("命令行未指定 LaTeXDiff 相关参数"))
        if state.new_tex_file and state.old_tex_file:
            print(_("根据配置文件设置 LaTeXDiff 新 TeX 文件为: ") + f"[bold cyan]{state.new_tex_file}")
            print(_("根据配置文件设置 LaTeXDiff 旧 TeX 文件为: ") + f"[bold cyan]{state.old_tex_file}")
        else:
            logger.error(_("请指定在命令行或配置文件中指定两个新旧 TeX 文件"))
            exit_pytexmk()

    if args.LaTeXDiff and len(args.LaTeXDiff) != 2 or args.LaTeXDiff_compile and len(args.LaTeXDiff_compile) != 2:
        logger.error(_("请同时指定 LaTeXDiff 所需的新旧 TeX 文件"))
        exit_pytexmk()
    if args.LaTeXDiff and len(args.LaTeXDiff) == 2:
        state.old_tex_file, state.new_tex_file = args.LaTeXDiff
    if args.LaTeXDiff_compile and len(args.LaTeXDiff_compile) == 2:
        state.old_tex_file, state.new_tex_file = args.LaTeXDiff_compile

    state.old_tex_file = state.mfo.check_project_name(state.main_files_in_root, state.old_tex_file, ".tex")
    state.new_tex_file = state.mfo.check_project_name(state.main_files_in_root, state.new_tex_file, ".tex")

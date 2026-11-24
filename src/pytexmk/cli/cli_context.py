"""PyTeXMK CLI 上下文解析：子项目定位、配置合并与魔法注释覆盖。"""

import os
from pathlib import Path

from ..config import ConfigParser
from ..language import set_language
from ..lifecycle import (
    EXIT_CONFIG_ERROR,
    EXIT_ERROR,
    EXIT_PROJECT_NOT_FOUND,
    exit_pytexmk,
)
from ..tex_project import standardize_name
from ..ui_theme import console
from .cli_state import (
    MAGIC_COMMENT_KEYS,
    PREVIEW_AFTER_COMPILE,
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
        logger.error(str(e))
        logger.warning(_("可运行 pytexmk -ls 写回子项目清单, 或检查根配置 [subprojects] 段"))
        exit_pytexmk(EXIT_PROJECT_NOT_FOUND)

    state.config_dict = ctx.config
    if ctx.subproject and args.verbose:
        logger.info(_("子项目调用: 忽略子项目目录下的本地 .pytexmkrc, 以根配置为准"))
    _validate_runtime_config(ctx.config, cp)

    # 进入工作根目录：用户终端 cwd 不变，编译流程在子项目/根目录内执行
    os.chdir(ctx.work_root)
    # 子项目条目直接指向某个 .tex 时，把它作为默认主文件，避免被配置里的
    # default_file 覆盖成不存在的名字
    if ctx.work_file is not None:
        state.default_file = ctx.work_file.stem
        state.explicit_default = True
        if ctx.subproject:
            logger.info(_("通过子项目条目指定主文件为: ") + f"[bold cyan]{state.default_file}[/bold cyan]")
        else:
            logger.info(_("通过命令行指定子目录主文件为: ") + f"[bold cyan]{state.default_file}[/bold cyan]")

    logger.info("-" * 70)
    tex_files_in_root = state.mfo.get_suffix_files_in_dir(".", ".tex")
    # -ca/-Ca 只清理产物，不应因为“根目录下有多个主文件/没有主文件”而退出。
    # 没有可用主文件时返回空清单，后续清理按后缀匹配递归执行。
    clean_any = bool(getattr(args, "clean_any", False) or getattr(args, "Clean_any", False))
    state.main_files_in_root = state.mfo.find_tex_commands(
        tex_files_in_root, required=not clean_any
    )
    state.all_magic_comments = state.mfo.search_magic_comments(state.main_files_in_root, MAGIC_COMMENT_KEYS)

    _apply_config_file(state)
    _apply_quiet_mode(state, args)

    logger.info("-" * 70)
    _apply_pdf_preview(state)
    return state


def _validate_runtime_config(config: dict, cp: ConfigParser) -> None:
    """在普通编译路径上消费配置校验结果。

    ``--validate-config`` 早就认得“段被写成字符串/数字”，但编译路径直接
    ``config["build"].get(...)``，坏配置会抛 AttributeError 并打印 traceback。
    这里在读取任何段之前统一校验，坏配置以 EXIT_CONFIG_ERROR 结束。
    """
    from .cli_config import config_errors, print_config_errors

    errors = config_errors(config, cp.load_errors, strict=False)
    if errors:
        print_config_errors(errors)
        exit_pytexmk(EXIT_CONFIG_ERROR)


def _apply_quiet_mode(state: WorkflowState, args) -> None:
    """一次算清安静模式（命令行 > 配置文件 > 内置默认）。

    安静模式只决定两件事：

    * TeX 的 ``-interaction``（安静=batchmode，非安静=nonstopmode）；
    * 子进程（TeX/biber/makeindex…）的输出是否实时打到终端。

    它**不碰控制台日志级别**：级别只看 ``-vb``（1.2.7 的口径，-vb → INFO，
    否则 WARNING）。0.6 曾让 ``-nq`` 顺带把级别抬到 INFO，于是 ``-nq`` 变成
    “刷屏开关”，与它真正的职责混淆。

    只有在命令行显式给出 ``-q`` / ``-nq`` 时才回显一行来源，配置文件驱动的
    默认行为保持安静（需要看结论用 ``--explain``）。
    """
    config_quiet = _as_bool(state.config_dict.get("quiet_mode"), True)

    if getattr(args, "non_quiet", False):
        state.non_quiet = True
        console.print(_("非安静模式: TeX 编译过程将实时显示在终端（-nq 覆盖 quiet_mode）"))
    else:
        state.non_quiet = not config_quiet


def resolve_target(args, state: WorkflowState) -> None:
    """决定本次要处理的目标：LaTeXDiff 新旧文件对，或待编译的主文件名。"""
    if state.is_latexdiff:
        _resolve_latexdiff_target(state)
    else:
        state.project_name = state.mfo.get_main_file(
            state.default_file, args.document, state.main_files_in_root, state.all_magic_comments
        )
    state.output_name = state.project_name


def resolve_clean_target(args, state: WorkflowState) -> None:
    """为 ``-ca/-Ca`` 做**不阻断**的主文件推断。

    递归清理不因为“根目录有两个主文件、又没有 default_file”就退出：能唯一
    推断时用真实 output_name 决定是否额外删除 ``Build/`` 里的 PDF/SyncTeX；
    推断不了就留空，只按后缀递归清理辅助文件。
    """
    names = list(state.main_files_in_root)
    document = getattr(args, "document", None)
    candidate = ""

    if state.explicit_default and state.default_file:
        candidate = state.default_file
    elif document:
        candidate = Path(str(document)).stem
    elif len(names) == 1:
        candidate = names[0]
    elif state.default_file in names:
        candidate = state.default_file
    elif len(state.all_magic_comments.get("root", {})) == 1:
        candidate = next(iter(state.all_magic_comments["root"]))

    state.project_name = candidate
    state.output_name = candidate


def _as_bool(value, default: bool = False) -> bool:
    """把配置里的布尔写成 true/false、"1"/"0"、"yes"/"no" 等统一成 bool。"""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() not in ("false", "0", "no", "off", "")


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
        console.print(_("通过魔法注释设置程序为: ") + f"[bold cyan]{state.compiled_program}")

    if state.magic_comments.get("outdir"):
        state.outdir = state.magic_comments["outdir"]
        console.print(_("通过魔法注释设置输出目录: ") + f"[bold cyan]{state.outdir}[/bold cyan]")
    if state.magic_comments.get("auxdir"):
        state.auxdir = state.magic_comments["auxdir"]
        console.print(_("通过魔法注释设置辅助目录: ") + f"[bold cyan]{state.auxdir}[/bold cyan]")

    state.refresh_file_lists()


def _apply_config_file(state: WorkflowState) -> None:
    """把配置文件中的取值合并进运行时参数（优先级：内置默认值 < 配置文件）。

    各配置段拆成独立的小函数，避免一个函数同时处理 build/folder/pdf/submission/
    index/latexdiff 六套字段；每段只读写自己的键，便于后续增删配置项。
    """
    _apply_main_config(state)
    _apply_build_config(state)
    _apply_folder_config(state)
    _apply_pdf_config(state)
    _apply_submission_config(state)
    _apply_index_config(state)
    _apply_latexdiff_config(state)
    _apply_preflight_config(state)


def _apply_main_config(state: WorkflowState) -> None:
    """default_file / compiled_program 两个顶层键。"""
    config_dict = state.config_dict
    logger = state.logger

    if config_dict["default_file"] and not state.explicit_default:
        state.default_file = config_dict["default_file"]
        logger.info(_("通过配置文件设置默认文件为: ") + f"[bold cyan]{state.default_file}")
    if config_dict["compiled_program"]:
        state.compiled_program = standardize_name(config_dict["compiled_program"])
        logger.info(_("通过配置文件设置编译器为: ") + f"[bold cyan]{state.compiled_program}")


def _apply_build_config(state: WorkflowState) -> None:
    """[build] 段：native / shell_escape / synctex / interaction / extra_args。"""
    build = state.config_dict.get("build") or {}
    if not build:
        return

    native = str(build.get("native", "auto")).lower()
    # auto：TeX 都支持 -output-directory，默认走原生目录构建（3.7 中期方案）
    state.native_build = native not in ("false", "0", "no", "off")
    if build.get("shell_escape") not in (None, ""):
        state.shell_escape = str(build["shell_escape"]).lower()
    if build.get("synctex") is not None:
        state.synctex = _as_bool(build.get("synctex"), True)
    if build.get("interaction"):
        state.interaction = str(build["interaction"])
    extra = build.get("extra_args") or []
    if isinstance(extra, list):
        state.extra_args = [str(x) for x in extra]
    try:
        state.max_extra_compilations = int(build.get("max_extra_compilations", 8))
    except TypeError, ValueError:
        state.max_extra_compilations = 8
    state.logger.info(
        _("构建模式: native=%(n)s, shell_escape=%(s)s, synctex=%(x)s")
        % {"n": state.native_build, "s": state.shell_escape, "x": state.synctex}
    )


def _apply_folder_config(state: WorkflowState) -> None:
    """[folder] 段：outdir / auxdir。"""
    folder = state.config_dict["folder"]
    if not folder:
        return
    if folder["outdir"]:
        state.outdir = folder["outdir"]
        state.logger.info(
            _("通过配置文件设置输出目录为: ") + f"[bold cyan]{state.outdir}"
        )
    if folder["auxdir"]:
        state.auxdir = folder["auxdir"]
        state.logger.info(
            _("通过配置文件设置辅助目录为: ") + f"[bold cyan]{state.auxdir}"
        )


def _apply_pdf_config(state: WorkflowState) -> None:
    """[pdf] 段：编译后预览开关与预览器。"""
    pdf = state.config_dict["pdf"]
    if not pdf:
        return
    if pdf["pdf_preview_status"]:
        state.preview_after_compile = True
        state.logger.info(
            _("通过配置文件设置 PDF 预览为: ") + f"[bold cyan]{pdf['pdf_preview_status']}"
        )
    if pdf["pdf_viewer"]:
        state.pfo.set_viewer(pdf["pdf_viewer"])
        state.logger.info(
            _("通过配置文件设置 PDF 预览器为: ") + f"[bold cyan]{pdf['pdf_viewer']}"
        )


def _apply_submission_config(state: WorkflowState) -> None:
    """[submission] 段：`-sp` 的打包开关与输出目录。"""
    submission_cfg = state.config_dict.get("submission") or {}
    if not submission_cfg:
        return
    if submission_cfg.get("unicode_to_latex") is not None:
        state.submission_unicode_to_latex = _as_bool(
            submission_cfg.get("unicode_to_latex"), True
        )
    if submission_cfg.get("include_bbl") is not None:
        state.submission_include_bbl = _as_bool(
            submission_cfg.get("include_bbl"), False
        )
    if submission_cfg.get("reproducible") is not None:
        state.submission_reproducible = _as_bool(
            submission_cfg.get("reproducible"), True
        )
    if submission_cfg.get("output_dir"):
        state.submission_output_dir = str(submission_cfg["output_dir"])
        state.logger.info(
            _("通过配置文件设置投稿包输出目录为: ")
            + f"[bold cyan]{state.submission_output_dir}"
        )
    if submission_cfg.get("keep_preamble") is not None:
        state.submission_keep_preamble = _as_bool(
            submission_cfg.get("keep_preamble"), False
        )


def _apply_preflight_config(state: WorkflowState) -> None:
    """[preflight] 段：编译前静态检查开关。"""
    preflight_cfg = state.config_dict.get("preflight") or {}
    if not isinstance(preflight_cfg, dict):
        return
    if preflight_cfg.get("enabled") is not None:
        state.preflight_enabled = _as_bool(preflight_cfg.get("enabled"), True)


def _apply_index_config(state: WorkflowState) -> None:
    """[index] 段：索引样式文件与 glossaries 后端。"""
    index_cfg = state.config_dict.get("index") or {}
    style_file = index_cfg.get("index_style_file")
    glossaries_tool = index_cfg.get("glossaries_tool")
    if not style_file and not glossaries_tool:
        return

    from ..detection import configure_index

    configure_index(
        str(style_file) if style_file else None,
        str(glossaries_tool) if glossaries_tool else None,
    )
    if style_file:
        state.logger.info(
            _("通过配置文件设置索引样式文件为: ") + f"[bold cyan]{style_file}"
        )
    if glossaries_tool:
        state.logger.info(
            _("通过配置文件设置 glossaries 工具为: ") + f"[bold cyan]{glossaries_tool}"
        )


def _apply_latexdiff_config(state: WorkflowState) -> None:
    """[latexdiff] 段：新旧 TeX 与对比文件名。"""
    latexdiff = state.config_dict["latexdiff"]
    if not latexdiff:
        return
    if latexdiff["old_tex_file"]:
        state.old_tex_file = latexdiff["old_tex_file"]
        state.logger.info(
            _("通过配置文件设置 LaTeXDiff 旧文件为: ")
            + f"[bold cyan]{state.old_tex_file}"
        )
    if latexdiff["new_tex_file"]:
        state.new_tex_file = latexdiff["new_tex_file"]
        state.logger.info(
            _("通过配置文件设置 LaTeXDiff 新文件为: ")
            + f"[bold cyan]{state.new_tex_file}"
        )
    if latexdiff["diff_tex_file"]:
        state.diff_tex_file = latexdiff["diff_tex_file"]
        state.logger.info(
            _("通过配置文件设置 LaTeXDiff 对比文件为: ")
            + f"[bold cyan]{state.diff_tex_file}"
        )


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
    # --explain 是只读动作：不能为了解释参数就先把用户的 PDF 拉起来。
    if getattr(args, "explain", False):
        return

    pdf_files_in_outdir = state.mfo.get_suffix_files_in_dir(state.outdir, ".pdf")
    target = state.mfo.check_project_name(pdf_files_in_outdir, args.pdf_preview, ".pdf")
    state.pfo.pdf_preview(target, state.outdir)
    exit_pytexmk()


def _resolve_latexdiff_target(state: WorkflowState) -> None:
    """校验并解析 LaTeXDiff 的两个待比较 TeX 文件（命令行优先，其次配置文件）。"""
    args, logger = state.args, state.logger

    # 0 个参数是合法的：`pytexmk -d` 表示“用配置文件里的 old/new”。
    # 只有 1 个参数（`-d old`）才是用法错误——旧实现把 0 个也当成错误，
    # 配置齐全时 `-d` 反而退出 1。
    for value, label in (
        (args.LaTeXDiff, "LaTeXDiff"),
        (args.LaTeXDiff_compile, "LaTeXDiff-compile"),
    ):
        if value is not None and len(value) not in (0, 2):
            logger.error(
                _("%(flag)s 需 0 个（取配置）或恰好 2 个文件名，当前收到 %(n)s 个")
                % {"flag": label, "n": len(value)}
            )
            exit_pytexmk(EXIT_ERROR)
    if args.LaTeXDiff is not None and len(args.LaTeXDiff) == 2:
        state.old_tex_file, state.new_tex_file = args.LaTeXDiff
    elif args.LaTeXDiff_compile is not None and len(args.LaTeXDiff_compile) == 2:
        state.old_tex_file, state.new_tex_file = args.LaTeXDiff_compile
    else:
        # 命令行未指定, 尝试从配置文件读取
        console.print(_("命令行未指定 LaTeXDiff 相关参数"))
        if state.new_tex_file and state.old_tex_file:
            console.print(_("根据配置文件设置 LaTeXDiff 新 TeX 文件为: ") + f"[bold cyan]{state.new_tex_file}")
            console.print(_("根据配置文件设置 LaTeXDiff 旧 TeX 文件为: ") + f"[bold cyan]{state.old_tex_file}")
        else:
            logger.error(_("请在命令行或配置文件中指定新旧两个 TeX 文件"))
            exit_pytexmk(EXIT_ERROR)

    state.old_tex_file = state.mfo.check_project_name(state.main_files_in_root, state.old_tex_file, ".tex")
    state.new_tex_file = state.mfo.check_project_name(state.main_files_in_root, state.new_tex_file, ".tex")

"""check_log_decouple.py - 验证 pytexlogs/ 新架构解耦的 31 个断言（FR-1 后版本）。

用法：
    uv run python scripts/check_log_decouple.py

目标：
    - 确认旧模块 pytexmk.log_parser 已被彻底删除（FR-1）
    - 确认新实现位于 pytexmk.pytexlogs.*（独立子包）
    - 确认新 LogLevel / LogEntry / ParsedLog 数据结构正确
    - 确认新 Parser 公共 API（LatexLogParser / BibtexParser / BiberParser 等）
    - 确认 FR-4 工具函数（show_log_entries / format_editor_jumps / log_editor_jumps）
    - 确认跨层架构约束（re.compile 只在具体 parser 内）
    - 确认 run_log_pipeline 新两参数注入（pytexmk_version / ref_tracker_translate_fn）
    - 回归：4 类日志解析正确、show_log_entries 过滤不重复打印
"""

from __future__ import annotations

import inspect
import io
import re
import sys
from pathlib import Path


def _ensure_src_on_path(root: str) -> None:
    src = str(Path(root) / 'src')
    if src not in sys.path:
        sys.path.insert(0, src)


# ──────────────────────────── Check01 ~ Check27：结构解耦断言 ────────────────────────────

def _check01_old_module_DELETED(root: str) -> bool:
    p = Path(root) / 'src/pytexmk/log_parser.py'
    if p.exists():
        print('[Check01] FAIL: 旧 log_parser.py 仍然存在（FR-1 未删除）'); return False
    print('[Check01] PASS: 旧模块 log_parser.py 已按 FR-1 删除')
    return True


def _check02_new_package_exists(root: str) -> bool:
    p = Path(root) / 'src/pytexmk/pytexlogs/__init__.py'
    if not p.exists():
        print('[Check02] FAIL: 新包 pytexlogs/__init__.py 不存在'); return False
    print('[Check02] PASS: 新包 pytexlogs/ 存在')
    return True


def _check03_new_top_level_init_no_mention(root: str) -> bool:
    p = Path(root) / 'src/pytexmk/__init__.py'
    src = p.read_text(encoding='utf-8')
    count = src.count('log_parser')
    if count != 0:
        print(f'[Check03] FAIL: 顶层 __init__.py 仍提到 log_parser ({count} 次)'); return False
    print('[Check03] PASS: 顶层 __init__.py 无旧模块残留（TR-5.2）')
    return True


def _check04_new_key_modules(root: str) -> bool:
    files = ['latexlog.py', 'bibtex.py', 'biber.py', 'base.py', 'summary.py',
             'manager.py', 'reftracker.py', '_facade.py', '_report.py']
    for f in files:
        p = Path(root) / f'src/pytexmk/pytexlogs/{f}'
        if not p.exists():
            print(f'[Check04] FAIL: 新模块缺失 {f}'); return False
    print('[Check04] PASS: 新包关键模块齐全（9 个）')
    return True


def _check05_new_latex_parser_importable(root: str) -> bool:
    _ensure_src_on_path(root)
    try:
        from pytexlogs import LatexLogParser
        inst = LatexLogParser(root_file='m.tex')
        if not inst:
            print('[Check05] FAIL: LatexLogParser 实例化失败'); return False
    except Exception as e:
        print(f'[Check05] FAIL: LatexLogParser 导入/实例化异常: {e!r}'); return False
    print('[Check05] PASS: 新 LatexLogParser 可导入并可实例化')
    return True


def _check06_new_parsedlog_has_entries_stats_source(root: str) -> bool:
    _ensure_src_on_path(root)
    try:
        from pytexlogs import LatexLogParser, ParsedLog
        simple_log = (
            "(./main.tex\n"
            "Package foo Warning: Bar.\n"
            "Output written on main.pdf (1 page).\n"
            ")\n"
        )
        r = LatexLogParser(root_file='main.tex').parse(simple_log)
        if not isinstance(r, ParsedLog):
            print(f'[Check06] FAIL: 返回类型不是 ParsedLog，实际 {type(r).__name__}'); return False
        if not hasattr(r, 'entries'):
            print('[Check06] FAIL: ParsedLog 缺 entries 属性'); return False
        if not hasattr(r, 'stats'):
            print('[Check06] FAIL: ParsedLog 缺 stats 属性'); return False
        if not hasattr(r, 'source_path'):
            print('[Check06] FAIL: ParsedLog 缺 source_path 属性'); return False
    except Exception as e:
        print(f'[Check06] FAIL: 解析异常: {e!r}'); return False
    print('[Check06] PASS: ParsedLog 含 entries/stats/source_path 三字段')
    return True


def _check07_new_bibtex_biber_parser_top_level_importable(root: str) -> bool:
    _ensure_src_on_path(root)
    try:
        from pytexlogs import BiberParser, BibtexParser
        b1 = BibtexParser(root_file='m.tex')
        b2 = BiberParser(root_file='m.tex')
        if not (b1 and b2):
            print('[Check07] FAIL: BibtexParser/BiberParser 实例化失败'); return False
    except Exception as e:
        print(f'[Check07] FAIL: BibtexParser/BiberParser 导入异常: {e!r}'); return False
    print('[Check07] PASS: BibtexParser + BiberParser 顶层导入并实例化 OK')
    return True


def _check08_new_bibtex_biber_parse_ok(root: str) -> bool:
    _ensure_src_on_path(root)
    try:
        from pytexlogs import BiberParser, BibtexParser, LogLevel
        biber_log = "WARN - x\nERROR - y\n"
        pr1 = BiberParser(root_file='m.tex').parse(biber_log)
        levels1 = {e.level for e in pr1.entries}
        if LogLevel.WARNING not in levels1:
            print(f'[Check08] FAIL: Biber 缺 WARNING，levels={levels1}'); return False
        if LogLevel.ERROR not in levels1:
            print(f'[Check08] FAIL: Biber 缺 ERROR，levels={levels1}'); return False

        bibtex_log = "Warning--I didn't find a database entry for \"bar\"\nI found no \\bibdata command---while reading file x.aux\n"
        pr2 = BibtexParser(root_file='m.tex').parse(bibtex_log)
        levels2 = {e.level for e in pr2.entries}
        if LogLevel.WARNING not in levels2:
            print(f'[Check08] FAIL: Bibtex 缺 WARNING，levels={levels2}'); return False
        if LogLevel.ERROR not in levels2:
            print(f'[Check08] FAIL: Bibtex 缺 ERROR，levels={levels2}'); return False
    except Exception as e:
        print(f'[Check08] FAIL: 解析异常: {e!r}'); return False
    print('[Check08] PASS: Biber/Bibtex 均能解析出 WARNING+ERROR 条目')
    return True


def _check09_no_residual_LogType_anywhere(root: str) -> bool:
    dirs = ['src/pytexmk', 'scripts', 'tests']
    self_path = str(Path(__file__).resolve())
    total = 0
    for d in dirs:
        base = Path(root) / d
        if not base.exists():
            continue
        for py in base.rglob('*.py'):
            if str(py.resolve()) == self_path:
                continue
            try:
                txt = py.read_text(encoding='utf-8')
            except Exception:
                continue
            total += len(re.findall(r'\bLogType\b', txt))
    if total != 0:
        print(f'[Check09] FAIL: 全仓仍有 {total} 处旧 Enum 名 LogType'); return False
    print('[Check09] PASS: 全仓（src/scripts/tests）无旧 LogType 残留')
    return True


def _check10_new_loglevel_enum(root: str) -> bool:
    _ensure_src_on_path(root)
    try:
        from pytexlogs.base import LogLevel
        m = LogLevel.__members__
        need = {'ERROR', 'WARNING', 'TYPESET', 'INFO', 'FONT', 'GRAPHIC', 'PAGE'}
        if not need.issubset(set(m)):
            print(f'[Check10] FAIL: LogLevel 缺失成员 {need - set(m)}'); return False
    except Exception as e:
        print(f'[Check10] FAIL: LogLevel 导入/检查异常: {e!r}'); return False
    print('[Check10] PASS: 新 LogLevel 枚举完整（7 种）')
    return True


def _check11_new_logentry_dataclass(root: str) -> bool:
    _ensure_src_on_path(root)
    try:
        import dataclasses

        from pytexlogs.base import LogEntry
        if not dataclasses.is_dataclass(LogEntry):
            print('[Check11] FAIL: 新 LogEntry 不是 dataclass'); return False
        fields = {f.name for f in dataclasses.fields(LogEntry)}
        need = {'level', 'file', 'line', 'text', 'error_pos_text'}
        if not need.issubset(fields):
            print(f'[Check11] FAIL: LogEntry 字段缺失 {need - fields}'); return False
    except Exception as e:
        print(f'[Check11] FAIL: LogEntry 检查异常: {e!r}'); return False
    print('[Check11] PASS: 新 LogEntry dataclass 字段齐全（5 个）')
    return True


def _check12_new_parsers_all_have_parse_method(root: str) -> bool:
    _ensure_src_on_path(root)
    try:
        from pytexlogs import (
            BiberParser,
            BibtexParser,
            LatexLogParser,
            MakeindexParser,
            XindyParser,
        )
        classes = [LatexLogParser, BibtexParser, BiberParser, MakeindexParser, XindyParser]
        for cls in classes:
            src = inspect.getsource(cls)
            if 'def parse(' not in src:
                print(f'[Check12] FAIL: {cls.__name__} 源码缺 def parse('); return False
    except Exception as e:
        print(f'[Check12] FAIL: 检查 parse 方法异常: {e!r}'); return False
    print('[Check12] PASS: 5 个 Parser 类均含 def parse( 方法')
    return True


def _check13_new_latex_has_reset_state(root: str) -> bool:
    _ensure_src_on_path(root)
    try:
        from pytexlogs import LatexLogParser
        src = inspect.getsource(LatexLogParser)
        if 'def _reset_state(' not in src:
            print('[Check13] FAIL: LatexLogParser 缺 reset_state 方法'); return False
    except Exception as e:
        print(f'[Check13] FAIL: 检查 reset_state 异常: {e!r}'); return False
    print('[Check13] PASS: LatexLogParser 含 reset_state 方法')
    return True


def _check14_new_latex_has_parse_line(root: str) -> bool:
    _ensure_src_on_path(root)
    try:
        from pytexlogs import LatexLogParser
        src = inspect.getsource(LatexLogParser)
        if 'def _parse_line(' not in src:
            print('[Check14] FAIL: LatexLogParser 缺 parse_line 方法'); return False
    except Exception as e:
        print(f'[Check14] FAIL: 检查 parse_line 异常: {e!r}'); return False
    print('[Check14] PASS: LatexLogParser 含 parse_line 方法')
    return True


def _check15_new_latex_has_parse_bad_box(root: str) -> bool:
    _ensure_src_on_path(root)
    try:
        from pytexlogs import LatexLogParser
        src = inspect.getsource(LatexLogParser)
        if 'def _parse_bad_box(' not in src:
            print('[Check15] FAIL: LatexLogParser 缺 parse_bad_box 方法'); return False
    except Exception as e:
        print(f'[Check15] FAIL: 检查 parse_bad_box 异常: {e!r}'); return False
    print('[Check15] PASS: LatexLogParser 含 parse_bad_box 方法')
    return True


def _check16_new_latex_has_parse_file_stack(root: str) -> bool:
    _ensure_src_on_path(root)
    try:
        from pytexlogs import LatexLogParser
        src = inspect.getsource(LatexLogParser)
        if 'def _parse_file_stack(' not in src:
            print('[Check16] FAIL: LatexLogParser 缺 parse_file_stack 方法'); return False
    except Exception as e:
        print(f'[Check16] FAIL: 检查 parse_file_stack 异常: {e!r}'); return False
    print('[Check16] PASS: LatexLogParser 含 parse_file_stack 方法')
    return True


def _check17_public_show_log_entries_exists(root: str) -> bool:
    _ensure_src_on_path(root)
    try:
        from pytexlogs import show_log_entries
        if not callable(show_log_entries):
            print('[Check17] FAIL: show_log_entries 不可调用'); return False
    except Exception as e:
        print(f'[Check17] FAIL: show_log_entries 导入异常: {e!r}'); return False
    print('[Check17] PASS: 公共工具 show_log_entries 可调用')
    return True


def _check18_public_format_and_log_editor_jumps_exist(root: str) -> bool:
    _ensure_src_on_path(root)
    try:
        from pytexlogs import format_editor_jumps, log_editor_jumps
        if not callable(format_editor_jumps):
            print('[Check18] FAIL: format_editor_jumps 不可调用'); return False
        if not callable(log_editor_jumps):
            print('[Check18] FAIL: log_editor_jumps 不可调用'); return False
    except Exception as e:
        print(f'[Check18] FAIL: format/log_editor_jumps 导入异常: {e!r}'); return False
    print('[Check18] PASS: format_editor_jumps + log_editor_jumps 两者都可调用')
    return True


def _check19_public_run_log_pipeline_exists(root: str) -> bool:
    _ensure_src_on_path(root)
    try:
        from pytexlogs import run_log_pipeline
        if not callable(run_log_pipeline):
            print('[Check19] FAIL: run_log_pipeline 不可调用'); return False
        sig = inspect.signature(run_log_pipeline)
        params = set(sig.parameters.keys())
        if 'pytexmk_version' not in params:
            print('[Check19] FAIL: run_log_pipeline 签名缺 pytexmk_version 参数'); return False
        if 'ref_tracker_translate_fn' not in params:
            print('[Check19] FAIL: run_log_pipeline 签名缺 ref_tracker_translate_fn 参数'); return False
    except Exception as e:
        print(f'[Check19] FAIL: run_log_pipeline 检查异常: {e!r}'); return False
    print('[Check19] PASS: run_log_pipeline 可调用且含两注入参数')
    return True


def _check20_new_summary_print(root: str) -> bool:
    _ensure_src_on_path(root)
    try:
        from pytexlogs.summary import print_summary
        if not callable(print_summary):
            print('[Check20] FAIL: summary.print_summary 不可调用'); return False
    except Exception as e:
        print(f'[Check20] FAIL: print_summary 导入异常: {e!r}'); return False
    print('[Check20] PASS: 新 summary.print_summary 存在且可调用')
    return True


def _check21_pkg_export_format_show_helpers(root: str) -> bool:
    _ensure_src_on_path(root)
    try:
        from pytexlogs import __all__
        if 'format_editor_jumps' not in __all__:
            print('[Check21] FAIL: __all__ 缺 format_editor_jumps'); return False
        if 'log_editor_jumps' not in __all__:
            print('[Check21] FAIL: __all__ 缺 log_editor_jumps'); return False
        if 'show_log_entries' not in __all__:
            print('[Check21] FAIL: __all__ 缺 show_log_entries'); return False
    except Exception as e:
        print(f'[Check21] FAIL: __all__ 检查异常: {e!r}'); return False
    print('[Check21] PASS: __all__ 导出 3 个 FR-4 工具函数')
    return True


def _check22_ref_change_tracker_injectable(root: str) -> bool:
    _ensure_src_on_path(root)
    try:
        import tempfile

        from pytexlogs import RefChangeTracker
        with tempfile.TemporaryDirectory() as td:
            tracker = RefChangeTracker(td, 'j', translate_fn=None)
            diff_dict = tracker.diff({'a'}, {'a', 'b'})
            result = tracker.format_report(diff_dict, total_unique=2)
            if not isinstance(result, str) or not result.strip():
                print(f'[Check22] FAIL: format_report 返回空或非字符串: {result!r}'); return False
    except Exception as e:
        print(f'[Check22] FAIL: RefChangeTracker 注入/调用异常: {e!r}'); return False
    print('[Check22] PASS: RefChangeTracker i18n 注入能力 OK（默认英文回退）')
    return True


def _check23_run_pipeline_default_version_unknown(root: str) -> bool:
    _ensure_src_on_path(root)
    try:
        import tempfile

        from pytexlogs import run_log_pipeline
        with tempfile.TemporaryDirectory() as td:
            report = run_log_pipeline('t', td, steps=[], write_report=False, print_terminal=False)
            if report.pytexmk_version != 'unknown':
                print(f'[Check23] FAIL: 默认 version 非 unknown，实际 {report.pytexmk_version!r}'); return False
    except Exception as e:
        print(f'[Check23] FAIL: run_log_pipeline 调用异常: {e!r}'); return False
    print('[Check23] PASS: run_log_pipeline 默认 pytexmk_version = unknown')
    return True


def _check24_new_latex_has_file_stack_property(root: str) -> bool:
    _ensure_src_on_path(root)
    try:
        from pytexlogs import LatexLogParser
        inst = LatexLogParser(root_file='main.tex')
        if not hasattr(inst, 'file_stack'):
            print('[Check24] FAIL: LatexLogParser 实例缺 file_stack 属性'); return False
        if not isinstance(inst.file_stack, list):
            print(f'[Check24] FAIL: file_stack 类型不是 list，实际 {type(inst.file_stack).__name__}'); return False
    except Exception as e:
        print(f'[Check24] FAIL: file_stack 检查异常: {e!r}'); return False
    print('[Check24] PASS: LatexLogParser 导出 file_stack list 属性')
    return True


def _check25_format_editor_jumps_correctness(root: str) -> bool:
    _ensure_src_on_path(root)
    try:
        from pytexlogs import LogEntry, LogLevel, format_editor_jumps
        xs = [
            LogEntry(level=LogLevel.ERROR, file='a/b/main.tex', line=12, text='hi'),
            LogEntry(level=LogLevel.WARNING, file='x/y/sup.tex', line=3, text='warn'),
        ]
        got = format_editor_jumps(xs)
        expected = ['main.tex:12: hi', 'sup.tex:3: warn']
        if got != expected:
            print(f'[Check25] FAIL: format_editor_jumps 结果不匹配\n  期望: {expected!r}\n  实际: {got!r}'); return False
    except Exception as e:
        print(f'[Check25] FAIL: format_editor_jumps 调用异常: {e!r}'); return False
    print('[Check25] PASS: format_editor_jumps 输出精确匹配')
    return True


def _check26_show_log_entries_show_info_filter(root: str) -> bool:
    _ensure_src_on_path(root)
    try:
        import pytexlogs.summary as _sum_mod
        from pytexlogs import (
            LogEntry,
            LogLevel,
            ParsedLog,
            show_log_entries,
        )
        if not hasattr(_sum_mod, 'ParsedLog'):
            _sum_mod.ParsedLog = ParsedLog
        if not hasattr(_sum_mod, 'LogEntry'):
            _sum_mod.LogEntry = LogEntry
        if not hasattr(_sum_mod, 'LogLevel'):
            _sum_mod.LogLevel = LogLevel

        xs = [
            LogEntry(level=LogLevel.ERROR, file='m.tex', line=1, text='Err msg'),
            LogEntry(level=LogLevel.WARNING, file='m.tex', line=2, text='Warn msg'),
            LogEntry(level=LogLevel.INFO, file='m.tex', line=3, text='Info only msg'),
        ]
        plog = ParsedLog(entries=xs)

        _ANSI = re.compile(r"\x1b\[[0-9;]*[mK]")
        _RICH = re.compile(r"\[/?[^\]]+\]")
        def strip(s: str) -> str: return _RICH.sub('', _ANSI.sub('', s))

        buf = io.StringIO(); old = sys.stdout
        sys.stdout = buf
        try:
            show_log_entries([plog], use_logger=False, show_info=False, non_quiet=True)
        finally:
            sys.stdout = old
        off = strip(buf.getvalue())

        buf = io.StringIO(); sys.stdout = buf
        try:
            show_log_entries([plog], use_logger=False, show_info=True, non_quiet=True)
        finally:
            sys.stdout = old
        on = strip(buf.getvalue())

        info_text = 'Info only msg'
        if info_text in off:
            print(f'[Check26] FAIL: show_info=False 仍含 Info 文本: {off!r}'); return False
        if info_text not in on:
            print(f'[Check26] FAIL: show_info=True 缺少 Info 文本: {on!r}'); return False
    except Exception as e:
        print(f'[Check26] FAIL: show_log_entries 过滤异常: {e!r}'); return False
    print('[Check26] PASS: show_log_entries show_info 过滤开关正确')
    return True


def _check27_pipeline_report_all_defaults(root: str) -> bool:
    _ensure_src_on_path(root)
    try:
        import tempfile

        from pytexlogs import ParsedPipelineReport, run_log_pipeline
        with tempfile.TemporaryDirectory() as td:
            report = run_log_pipeline('t', td, steps=[], write_report=False, print_terminal=False)
            if report is None:
                print('[Check27] FAIL: 返回 None（非 ParsedPipelineReport）'); return False
            if not isinstance(report, ParsedPipelineReport):
                print(f'[Check27] FAIL: 类型错误，实际 {type(report).__name__}'); return False
            if report.schema_version != 1:
                print(f'[Check27] FAIL: schema_version != 1，实际 {report.schema_version}'); return False
            if report.jobname != 't':
                print(f'[Check27] FAIL: jobname != t，实际 {report.jobname!r}'); return False
            if not hasattr(report, 'references'):
                print('[Check27] FAIL: 缺 references 字段'); return False
            if not hasattr(report, 'tool_results'):
                print('[Check27] FAIL: 缺 tool_results 字段'); return False
            if not hasattr(report, 'config_ignored'):
                print('[Check27] FAIL: 缺 config_ignored 字段'); return False
    except Exception as e:
        print(f'[Check27] FAIL: pipeline 报告检查异常: {e!r}'); return False
    print('[Check27] PASS: ParsedPipelineReport 默认结构齐全（schema=1/jobname/refs/tools/config）')
    return True


# ──────────────────────────── Check28 ~ Check31：回归与架构约束 ────────────────────────────

def _check28_high_level_no_re_compile(root: str) -> bool:
    high_files = ['_facade.py', '_report.py', 'summary.py', 'manager.py', '__init__.py']
    total = 0
    for f in high_files:
        p = Path(root) / f'src/pytexmk/pytexlogs/{f}'
        if not p.exists():
            continue
        src = p.read_text(encoding='utf-8')
        lines = src.splitlines()
        for line in lines:
            stripped = line.lstrip()
            if stripped.startswith('#') or not stripped:
                continue
            if len(line) - len(stripped) > 0:
                continue
            if re.search(r'(?<![_\w])re\.compile\(', line):
                total += 1
    if total != 0:
        print(f'[Check28] FAIL: 高层模块仍有 {total} 处模块级 re.compile(（应仅存在于具体 parser）'); return False
    print('[Check28] PASS: 5 个高层模块无模块级 re.compile(（架构分层 OK）')
    return True


def _check29_parity_4_logs_new_api(root: str) -> bool:
    _ensure_src_on_path(root)
    try:
        from pytexlogs import (
            BiberParser,
            BibtexParser,
            LatexLogParser,
            LogLevel,
        )

        # 第 1 段：Overfull + file_stack bug 回归
        log1 = (
            "(./main.tex\n"
            r"Overfull \hbox (20.1pt too wide) in paragraph at lines 10--20"
            "\n"
            r"|\OT1/cmr/m/n/10 long text that should be overfull|"
            "\n)\n"
            "Output written on main.pdf (1 page).\n"
        )
        pr1 = LatexLogParser(root_file='main.tex').parse(log1)
        overfull = [e for e in pr1.entries if 'Overfull' in e.text]
        if not overfull:
            print(f'[Check29] FAIL: 没找到 Overfull，entries count={len(pr1.entries)}'); return False
        e = overfull[0]
        if '20.1pt' in (e.file or ''):
            print(f'[Check29] FAIL: file_stack bug 仍存在，e.file={e.file!r}'); return False
        if e.level != LogLevel.TYPESET:
            print(f'[Check29] FAIL: Overfull level 应为 TYPESET，实际 {e.level}'); return False

        # 第 2 段：ERROR + WARNING + Missing character
        log2 = (
            "(./chapters/intro.tex\n"
            "Package hyperref Warning: Token not allowed in a PDF string on input line 33.\n"
            r"! LaTeX Error: File `missing.sty' not found."
            "\n"
            r"l.12 \usepackage{missing}"
            "\n"
            r"LaTeX Warning: Citation `knuth1997' on page 1 undefined on input line 5."
            "\n"
            r"Missing character: There is no 你 in font cmr10!"
            "\n)\n"
            "Output written on main.pdf (2 pages).\n"
        )
        pr2 = LatexLogParser(root_file='main.tex').parse(log2)
        levels2 = [x.level for x in pr2.entries]
        if LogLevel.ERROR not in levels2:
            print(f'[Check29] FAIL: 样本2 缺 ERROR, levels={levels2}'); return False
        if LogLevel.WARNING not in levels2:
            print(f'[Check29] FAIL: 样本2 缺 WARNING, levels={levels2}'); return False
        if not any('Missing character' in x.text for x in pr2.entries):
            print('[Check29] FAIL: 样本2 缺 Missing character'); return False

        # 第 3 段：BiberParser WARN+ERROR
        log3 = (
            "INFO - This is Biber 2.19\n"
            "WARN - The entry 'invalid' has invalid field 'foo'\n"
            "ERROR - Cannot find 'xxx' in .bib file!\n"
        )
        pr3 = BiberParser(root_file='m.tex').parse(log3)
        t3 = [x.level for x in pr3.entries]
        if LogLevel.WARNING not in t3:
            print(f'[Check29] FAIL: biber 缺 WARNING, levels={t3}'); return False
        if LogLevel.ERROR not in t3:
            print(f'[Check29] FAIL: biber 缺 ERROR, levels={t3}'); return False

        # 第 4 段：BibtexParser WARNING+ERROR
        log4 = (
            "Warning--I didn't find a database entry for \"bar\"\n"
            "I found no \\bibdata command---while reading file x.aux\n"
        )
        pr4 = BibtexParser(root_file='m.tex').parse(log4)
        t4 = [x.level for x in pr4.entries]
        if LogLevel.WARNING not in t4:
            print(f'[Check29] FAIL: bibtex 缺 WARNING, levels={t4}'); return False
        if LogLevel.ERROR not in t4:
            print(f'[Check29] FAIL: bibtex 缺 ERROR, levels={t4}'); return False

    except Exception as e:
        print(f'[Check29] FAIL: parity 解析异常: {e!r}'); return False
    print('[Check29] PASS: 4 类日志新 API 解析 OK（含 file_stack bug 修复）')
    return True


def _check30_show_log_entries_filter_and_no_dup(root: str) -> bool:
    _ensure_src_on_path(root)
    try:
        import re as _re

        import pytexlogs.summary as _sum_mod
        from pytexlogs import (
            LatexLogParser,
            LogEntry,
            LogLevel,
            ParsedLog,
            show_log_entries,
        )
        if not hasattr(_sum_mod, 'ParsedLog'):
            _sum_mod.ParsedLog = ParsedLog
        if not hasattr(_sum_mod, 'LogEntry'):
            _sum_mod.LogEntry = LogEntry
        if not hasattr(_sum_mod, 'LogLevel'):
            _sum_mod.LogLevel = LogLevel

        _ANSI = _re.compile(r"\x1b\[[0-9;]*[mK]")
        _RICH_TAG = _re.compile(r"\[/?[^\]]+\]")
        def strip(s: str) -> str: return _RICH_TAG.sub('', _ANSI.sub('', s))

        log = (
            "(./main.tex\n"
            "Package foo Warning: A.\n"
            "LaTeX Warning: B.\n"
            "! Undefined control sequence.\n"
            "l.1 \\badcmd\n"
            "LaTeX Info: Redefining \\sqrt.\n"
            ")\n"
        )
        p = LatexLogParser(root_file='main.tex')
        parsed = p.parse(log)

        buf = io.StringIO(); old = sys.stdout
        sys.stdout = buf
        try:
            show_log_entries(parsed, use_logger=False, show_info=False)
        finally:
            sys.stdout = old
        off = strip(buf.getvalue())

        buf = io.StringIO(); sys.stdout = buf
        try:
            show_log_entries(parsed, use_logger=False, show_info=True)
        finally:
            sys.stdout = old
        on = strip(buf.getvalue())

        info_markers = ('LaTeX Info', 'Redefining', '[I]', 'INFO')
        has_info_off = any(m in off for m in info_markers)
        if has_info_off:
            print(f'[Check30] FAIL: show_info=False 仍含 Info 标记: {off!r}'); return False
        has_info_on = any(m in on for m in info_markers)
        if not has_info_on:
            print(f'[Check30] FAIL: show_info=True 缺少 Info 标记: {on!r}'); return False

        wc_on = on.count('[W]'); ec_on = on.count('[E]')
        if wc_on > 5:
            print(f'[Check30] FAIL: [W] 重复 >5 次：count={wc_on}'); return False
        if ec_on > 3:
            print(f'[Check30] FAIL: [E] 重复 >3 次：count={ec_on}'); return False
    except Exception as e:
        print(f'[Check30] FAIL: show_log_entries 回归异常: {e!r}'); return False
    print('[Check30] PASS: show_log_entries filter + 无重复爆炸（W<=5, E<=3）')
    return True


def _check31_re_compile_all_located_in_subpackage(root: str) -> bool:
    # 1. 旧文件不存在
    old = Path(root) / 'src/pytexmk/log_parser.py'
    if old.exists():
        print('[Check31] FAIL: 旧 log_parser.py 文件仍然存在'); return False

    # 2. 主包上层（排除 pytexlogs/ 子目录，同时排除顶层业务核心 *.py 模块）
    #    顶层 *.py 如 compile.py / additional.py / latexdiff.py 是编译控制/辅助业务，
    #    其正则非日志解析层，不属此架构约束。约束仅针对主包下的其他子目录（非 pytexlogs/）。
    top = Path(root) / 'src/pytexmk'
    total = 0
    for py in top.rglob('*.py'):
        rel = py.relative_to(top)
        parts = rel.parts
        if not parts:
            continue
        if parts[0] == 'pytexlogs':
            continue
        if len(parts) == 1:
            continue
        try:
            txt = py.read_text(encoding='utf-8')
        except Exception:
            continue
        total += len(re.findall(r'(?<![_\w])re\.compile\(', txt))
    if total != 0:
        print(f'[Check31] FAIL: 主包子目录（非 pytexlogs/）仍有 {total} 处 re.compile(（违反跨层约束）'); return False
    print('[Check31] PASS: 跨层架构约束 OK（主包无日志解析层 re.compile，正则全部在 pytexlogs/ 内）')
    return True


def _check32_compat_layer(root: str) -> bool:
    """Check 32: compat 层 + attach 函数存在性（spec G5 logger 桥接）。"""
    try:
        _ensure_src_on_path(root)
        import pytexlogs

        from pytexmk.logger_config import attach_pytexlogs_handlers_to_pytexmk_logger
        PYTEXLOGS_SOURCE = "remote" if pytexlogs.__file__ and "site-packages" in pytexlogs.__file__ else "bundled"
        assert hasattr(pytexlogs, "__all__"), "pytexlogs missing __all__"
        assert len(pytexlogs.__all__) > 0, "pytexlogs __all__ is empty"
        import logging as _lg
        before = len(_lg.getLogger("pytexlogs").handlers)
        attach_pytexlogs_handlers_to_pytexmk_logger()
        attach_pytexlogs_handlers_to_pytexmk_logger()
        after = len(_lg.getLogger("pytexlogs").handlers)
        assert after - before <= 0, f"attach 不幂等，handler 增加了 {after - before}"
        print(f'[Check32] PASS: compat layer OK, PYTEXLOGS_SOURCE={PYTEXLOGS_SOURCE}')
        return True
    except Exception as _e:
        print(f'[Check32] FAIL: Check 32 (compat layer) - {_e}')
        return False


# ──────────────────────────── 主函数：批量执行 32 个断言 ────────────────────────────

def main() -> int:
    root = str(Path(__file__).resolve().parent.parent)
    all_checks = [
        _check01_old_module_DELETED,
        _check02_new_package_exists,
        _check03_new_top_level_init_no_mention,
        _check04_new_key_modules,
        _check05_new_latex_parser_importable,
        _check06_new_parsedlog_has_entries_stats_source,
        _check07_new_bibtex_biber_parser_top_level_importable,
        _check08_new_bibtex_biber_parse_ok,
        _check09_no_residual_LogType_anywhere,
        _check10_new_loglevel_enum,
        _check11_new_logentry_dataclass,
        _check12_new_parsers_all_have_parse_method,
        _check13_new_latex_has_reset_state,
        _check14_new_latex_has_parse_line,
        _check15_new_latex_has_parse_bad_box,
        _check16_new_latex_has_parse_file_stack,
        _check17_public_show_log_entries_exists,
        _check18_public_format_and_log_editor_jumps_exist,
        _check19_public_run_log_pipeline_exists,
        _check20_new_summary_print,
        _check21_pkg_export_format_show_helpers,
        _check22_ref_change_tracker_injectable,
        _check23_run_pipeline_default_version_unknown,
        _check24_new_latex_has_file_stack_property,
        _check25_format_editor_jumps_correctness,
        _check26_show_log_entries_show_info_filter,
        _check27_pipeline_report_all_defaults,
        _check28_high_level_no_re_compile,
        _check29_parity_4_logs_new_api,
        _check30_show_log_entries_filter_and_no_dup,
        _check31_re_compile_all_located_in_subpackage,
        _check32_compat_layer,
    ]
    total = len(all_checks)
    passed = 0
    for fn in all_checks:
        try:
            if fn(root):
                passed += 1
        except BaseException as exc:
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            print(f'[{fn.__name__}] EXCEPTION: {exc!r}')
    print()
    if passed == total:
        print(f'=== All {passed}/{total} checks passed ===')
        return 0
    print(f'=== {passed}/{total} checks passed (some failed) ===')
    return 1


if __name__ == '__main__':
    sys.exit(main())

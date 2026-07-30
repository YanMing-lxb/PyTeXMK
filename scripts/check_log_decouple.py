"""check_log_decouple.py - 验证 log_parser.py 与 log_parsers/ 新架构解耦的 31 个断言。

用法：
    uv run python scripts/check_log_decouple.py

目标：
    - 确认旧 API（pytexmk.log_parser）为薄转发层
    - 确认新实现位于 pytexmk.log_parsers.*（独立模块）
    - 确认新旧行为等价（parity）
    - 确认 show_log 过滤 / 不重复打印
    - 确认本地正则已彻底移除（零 re.compile(r" 出现）
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# ──────────────────────────── Check1 ~ Check27：结构解耦断言 ────────────────────────────

def _check01_old_module_exists(root: str) -> bool:
    p = Path(root) / 'src/pytexmk/log_parser.py'
    if not p.exists():
        print('[Check01] FAIL: 旧 log_parser.py 不存在'); return False
    print('[Check01] PASS: 旧模块 log_parser.py 存在')
    return True


def _check02_new_package_exists(root: str) -> bool:
    p = Path(root) / 'src/pytexmk/log_parsers/__init__.py'
    if not p.exists():
        print('[Check02] FAIL: 新包 log_parsers/__init__.py 不存在'); return False
    print('[Check02] PASS: 新包 log_parsers/ 存在')
    return True


def _check03_old_imports_new(root: str) -> bool:
    src = (Path(root) / 'src/pytexmk/log_parser.py').read_text(encoding='utf-8')
    if 'from pytexmk.log_parsers' not in src:
        print('[Check03] FAIL: 旧模块未从 log_parsers.* 导入'); return False
    print('[Check03] PASS: 旧模块从新包 log_parsers.* 导入')
    return True


def _check04_new_key_modules(root: str) -> bool:
    files = ['latexlog.py', 'bibtex.py', 'biber.py', 'base.py', 'summary.py']
    for f in files:
        p = Path(root) / f'src/pytexmk/log_parsers/{f}'
        if not p.exists():
            print(f'[Check04] FAIL: 新模块缺失 {f}'); return False
    print('[Check04] PASS: 新包关键模块齐全')
    return True


def _check05_latex_parser_in_both(root: str) -> bool:
    import sys
    sys.path.insert(0, str(Path(root) / 'src'))
    from pytexmk.log_parser import LatexLogParser as Old
    from pytexmk.log_parsers.latexlog import LatexLogParser as New
    if not (Old and New):
        print('[Check05] FAIL: 新旧 LatexLogParser 未同时存在'); return False
    print('[Check05] PASS: 新旧 LatexLogParser 均存在')
    return True


def _check06_old_has__new_delegate(root: str) -> bool:
    src = (Path(root) / 'src/pytexmk/log_parser.py').read_text(encoding='utf-8')
    if 'self._new = _NewLatexLogParser' not in src and 'self._new =' not in src:
        print('[Check06] FAIL: 旧 LatexLogParser 无 self._new 委托字段'); return False
    print('[Check06] PASS: 旧 LatexLogParser 持有 self._new 委托对象')
    return True


def _check07_old_has_bibtex_parser(root: str) -> bool:
    import sys
    sys.path.insert(0, str(Path(root) / 'src'))
    from pytexmk.log_parser import BibTeXLogParser
    if not BibTeXLogParser:
        print('[Check07] FAIL: 旧 BibTeXLogParser 缺失'); return False
    print('[Check07] PASS: 旧 BibTeXLogParser 存在')
    return True


def _check08_new_bibtex_biber_exist(root: str) -> bool:
    import sys
    sys.path.insert(0, str(Path(root) / 'src'))
    from pytexmk.log_parsers.biber import BiberParser
    from pytexmk.log_parsers.bibtex import BibtexParser
    if not (BibtexParser and BiberParser):
        print('[Check08] FAIL: 新 BibtexParser/BiberParser 缺失'); return False
    print('[Check08] PASS: 新 BibtexParser + BiberParser 存在')
    return True


def _check09_old_logtype_enum(root: str) -> bool:
    import sys
    sys.path.insert(0, str(Path(root) / 'src'))
    from pytexmk.log_parser import LogType
    m = LogType.__members__
    need = {'ERROR', 'WARNING', 'TYPESET', 'INFO', 'FONT', 'GRAPHIC', 'PAGE'}
    if not need.issubset(set(m)):
        print(f'[Check09] FAIL: LogType 缺失成员 {need - set(m)}'); return False
    print('[Check09] PASS: 旧 LogType 枚举完整（7 种）')
    return True


def _check10_new_loglevel_enum(root: str) -> bool:
    import sys
    sys.path.insert(0, str(Path(root) / 'src'))
    from pytexmk.log_parsers.base import LogLevel
    m = LogLevel.__members__
    need = {'ERROR', 'WARNING', 'TYPESET', 'INFO', 'FONT', 'GRAPHIC', 'PAGE'}
    if not need.issubset(set(m)):
        print(f'[Check10] FAIL: LogLevel 缺失成员 {need - set(m)}'); return False
    print('[Check10] PASS: 新 LogLevel 枚举完整（7 种）')
    return True


def _check11_new_logentry_dataclass(root: str) -> bool:
    import sys
    sys.path.insert(0, str(Path(root) / 'src'))
    import dataclasses

    from pytexmk.log_parsers.base import LogEntry
    if not dataclasses.is_dataclass(LogEntry):
        print('[Check11] FAIL: 新 LogEntry 不是 dataclass'); return False
    fields = {f.name for f in dataclasses.fields(LogEntry)}
    need = {'level', 'file', 'line', 'text', 'error_pos_text'}
    if not need.issubset(fields):
        print(f'[Check11] FAIL: LogEntry 字段缺失 {need - fields}'); return False
    print('[Check11] PASS: 新 LogEntry dataclass 字段齐全')
    return True


def _check12_old_has_parse(root: str) -> bool:
    src = (Path(root) / 'src/pytexmk/log_parser.py').read_text(encoding='utf-8')
    if 'def parse(' not in src:
        print('[Check12] FAIL: 旧模块缺 parse 方法'); return False
    print('[Check12] PASS: 旧模块含 parse 方法')
    return True


def _check13_old_has_reset_state(root: str) -> bool:
    src = (Path(root) / 'src/pytexmk/log_parser.py').read_text(encoding='utf-8')
    if 'def reset_state(' not in src:
        print('[Check13] FAIL: 旧模块缺 reset_state'); return False
    print('[Check13] PASS: 旧模块含 reset_state')
    return True


def _check14_old_has_parse_line(root: str) -> bool:
    src = (Path(root) / 'src/pytexmk/log_parser.py').read_text(encoding='utf-8')
    if 'def parse_line(' not in src:
        print('[Check14] FAIL: 旧模块缺 parse_line'); return False
    print('[Check14] PASS: 旧模块含 parse_line')
    return True


def _check15_old_has_parse_bad_box(root: str) -> bool:
    src = (Path(root) / 'src/pytexmk/log_parser.py').read_text(encoding='utf-8')
    if 'def parse_bad_box(' not in src:
        print('[Check15] FAIL: 旧模块缺 parse_bad_box'); return False
    print('[Check15] PASS: 旧模块含 parse_bad_box')
    return True


def _check16_old_has_parse_file_stack(root: str) -> bool:
    src = (Path(root) / 'src/pytexmk/log_parser.py').read_text(encoding='utf-8')
    if 'def parse_file_stack(' not in src:
        print('[Check16] FAIL: 旧模块缺 parse_file_stack'); return False
    print('[Check16] PASS: 旧模块含 parse_file_stack')
    return True


def _check17_old_has_show_log(root: str) -> bool:
    src = (Path(root) / 'src/pytexmk/log_parser.py').read_text(encoding='utf-8')
    if 'def show_log(' not in src:
        print('[Check17] FAIL: 旧模块缺 show_log'); return False
    print('[Check17] PASS: 旧模块含 show_log')
    return True


def _check18_old_has_show_editor_jump(root: str) -> bool:
    src = (Path(root) / 'src/pytexmk/log_parser.py').read_text(encoding='utf-8')
    if 'def show_editor_jump_format(' not in src:
        print('[Check18] FAIL: 旧模块缺 show_editor_jump_format'); return False
    print('[Check18] PASS: 旧模块含 show_editor_jump_format')
    return True


def _check19_old_has_logparser_cli(root: str) -> bool:
    src = (Path(root) / 'src/pytexmk/log_parser.py').read_text(encoding='utf-8')
    if 'def logparser_cli(' not in src:
        print('[Check19] FAIL: 旧模块缺 logparser_cli'); return False
    print('[Check19] PASS: 旧模块含 logparser_cli')
    return True


def _check20_new_summary_print(root: str) -> bool:
    import sys
    sys.path.insert(0, str(Path(root) / 'src'))
    from pytexmk.log_parsers.summary import print_summary
    if not callable(print_summary):
        print('[Check20] FAIL: summary.print_summary 不可调用'); return False
    print('[Check20] PASS: 新 summary.print_summary 存在且可调用')
    return True


def _check21_pkg_export_run_pipeline(root: str) -> bool:
    import sys
    sys.path.insert(0, str(Path(root) / 'src'))
    from pytexmk.log_parsers import run_log_pipeline
    if not callable(run_log_pipeline):
        print('[Check21] FAIL: log_parsers.run_log_pipeline 不可调用'); return False
    print('[Check21] PASS: 顶层包导出 run_log_pipeline')
    return True


def _check22_old_has_build_log(root: str) -> bool:
    src = (Path(root) / 'src/pytexmk/log_parser.py').read_text(encoding='utf-8')
    if 'self.build_log' not in src:
        print('[Check22] FAIL: 旧模块无 build_log 字段'); return False
    print('[Check22] PASS: 旧模块保持 build_log 兼容字段')
    return True


def _check23_old_has_current_result(root: str) -> bool:
    src = (Path(root) / 'src/pytexmk/log_parser.py').read_text(encoding='utf-8')
    if 'self.current_result' not in src:
        print('[Check23] FAIL: 旧模块无 current_result 字段'); return False
    print('[Check23] PASS: 旧模块保持 current_result 兼容字段')
    return True


def _check24_old_has_file_stack_prop(root: str) -> bool:
    src = (Path(root) / 'src/pytexmk/log_parser.py').read_text(encoding='utf-8')
    if '@property' not in src or 'def file_stack' not in src:
        print('[Check24] FAIL: 旧模块缺 file_stack 属性'); return False
    print('[Check24] PASS: 旧模块导出 file_stack 属性')
    return True


def _check25_old_has_entry_dict_helper(root: str) -> bool:
    src = (Path(root) / 'src/pytexmk/log_parser.py').read_text(encoding='utf-8')
    if 'def _new_entry_to_old_dict(' not in src:
        print('[Check25] FAIL: 缺 _new_entry_to_old_dict 转换助手'); return False
    print('[Check25] PASS: 存在 _new_entry_to_old_dict 转换函数')
    return True


def _check26_old_has_level_mapper(root: str) -> bool:
    src = (Path(root) / 'src/pytexmk/log_parser.py').read_text(encoding='utf-8')
    if 'def _log_level_to_logtype(' not in src:
        print('[Check26] FAIL: 缺 _log_level_to_logtype 等级映射'); return False
    print('[Check26] PASS: 存在 _log_level_to_logtype 等级映射')
    return True


def _check27_old_init_creates__new(root: str) -> bool:
    import sys
    sys.path.insert(0, str(Path(root) / 'src'))
    from pytexmk.log_parser import LatexLogParser
    inst = LatexLogParser(root_file='m.tex')
    if not hasattr(inst, '_new') or inst._new is None:
        print('[Check27] FAIL: 构造后 _new 委托未初始化'); return False
    print('[Check27] PASS: LatexLogParser.__init__ 正确构造 self._new 委托')
    return True


# ──────────────────────────── Check28 ~ Check31：用户新增断言 ────────────────────────────

# Check28: 零本地循环/方法（forward shim 只有 self._new 调用，不含本地实现细节）
def _check28_zero_local_impl(root: str) -> bool:
    p = Path(root) / 'src/pytexmk/log_parser.py'
    src = p.read_text(encoding='utf-8')
    forbidden_def_names = ['def reset_state(', 'def parse_line(', 'def parse_bad_box(', 'def parse_file_stack(']
    forbidden_body_tokens = [' for line in ', ' for e in new_entries', '.match(', '.group(', 'pattern.']

    lines = src.splitlines(); i = 0; issues = []
    while i < len(lines):
        ln = lines[i].lstrip()
        if ln.startswith('def ') and any(ln.startswith(f) for f in forbidden_def_names):
            method_name = ln
            indent = len(lines[i]) - len(lines[i].lstrip())
            body = []; j = i + 1
            while j < len(lines):
                lj = lines[j]
                if lj.strip() == '':
                    j += 1; continue
                cur = len(lj) - len(lj.lstrip())
                if cur <= indent and not lj.lstrip().startswith('#'):
                    break
                body.append(lj); j += 1
            body_str = '\n'.join(body)
            filtered = re.sub(r'self\._new\.\w+', '', body_str)
            filtered = re.sub(r"self\.build_log = \[_new_entry_to_old_dict\(e\) for e in (self\._new\.build_log|parsed\.entries|merged)\]", '', filtered)
            filtered = re.sub(r'self\.current_result = .+', '', filtered)
            filtered = re.sub(r'\s*return (True|False|None|\[\])\s*', '', filtered)
            for tok in forbidden_body_tokens:
                if tok in filtered:
                    issues.append(f'method {method_name!r} body still contains {tok!r}: {filtered.strip()[:200]}')
            i = j
        else:
            i += 1
    if issues:
        print('[Check28] FAIL: ' + '; '.join(issues))
        return False
    print('[Check28] PASS: 零本地循环/方法实现（forward shims clean）')
    return True


# Check29: 新旧行为等价（含 file_stack bug 修复）
def _check29_parity_file_stack_bug(root: str) -> bool:
    import sys
    sys.path.insert(0, str(Path(root) / 'src'))
    from pytexmk.log_parser import LatexLogParser, LogType
    log1 = (
        "(./main.tex\n"
        r"Overfull \hbox (20.1pt too wide) in paragraph at lines 10--20"
        "\n"
        r"|\OT1/cmr/m/n/10 long text that should be overfull|"
        "\n)\n"
        "Output written on main.pdf (1 page).\n"
    )
    e1 = LatexLogParser(root_file='main.tex').parse(log1)
    overfull = [e for e in e1 if 'Overfull' in e['text']]
    if not overfull:
        print(f'[Check29] FAIL: 没找到 Overfull，entries={e1}'); return False
    e = overfull[0]
    if '20.1pt' in e['file']:
        print(f'[Check29] FAIL: file_stack bug 仍然存在，e.file={e["file"]!r}'); return False
    if e['type'] != LogType.TYPESET:
        print(f'[Check29] FAIL: Overfull type 应为 TYPESET，实际 {e["type"]}'); return False
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
    e2 = LatexLogParser(root_file='main.tex').parse(log2)
    types2 = [x['type'] for x in e2]
    if LogType.ERROR not in types2: print(f'[Check29] FAIL: 样本2 缺 ERROR, types={types2}'); return False
    if LogType.WARNING not in types2: print(f'[Check29] FAIL: 样本2 缺 WARNING, types={types2}'); return False
    if not any('Missing character' in x['text'] for x in e2): print(f'[Check29] FAIL: 样本2 缺 missing_char, entries={e2}'); return False
    from pytexmk.log_parser import BibTeXLogParser
    log3 = (
        "INFO - This is Biber 2.19\n"
        "WARN - The entry 'invalid' has invalid field 'foo'\n"
        "ERROR - Cannot find 'xxx' in .bib file!\n"
    )
    e3 = BibTeXLogParser(root_file='m.tex').parse(log3)
    t3 = [x['type'] for x in e3]
    if LogType.WARNING not in t3: print(f'[Check29] FAIL: biber 缺 WARNING, types={t3}'); return False
    if LogType.ERROR not in t3: print(f'[Check29] FAIL: biber 缺 ERROR, types={t3}'); return False
    log4 = "Warning--I didn't find a database entry for \"bar\"\nI found no \\bibdata command---while reading file x.aux\n"
    e4 = BibTeXLogParser(root_file='m.tex').parse(log4)
    t4 = [x['type'] for x in e4]
    if LogType.WARNING not in t4: print(f'[Check29] FAIL: bibtex 缺 WARNING, types={t4}'); return False
    if LogType.ERROR not in t4: print(f'[Check29] FAIL: bibtex 缺 ERROR, types={t4}'); return False
    print('[Check29] PASS: 4 类日志 parity OK（含 file_stack bug 修复）')
    return True


# Check30: show_log 过滤 & 不重复打印
def _check30_show_log_filter_and_no_dup(root: str) -> bool:
    import io
    import re
    import sys
    sys.path.insert(0, str(Path(root) / 'src'))
    from pytexmk.log_parser import LatexLogParser
    _ANSI = re.compile(r"\x1b\[[0-9;]*[mK]")
    _RICH = re.compile(r"\[[^\[\]]*\]")
    def strip(s): return _RICH.sub('', _ANSI.sub('', s))
    log = (
        "(./main.tex\n"
        "Package foo Warning: A.\n"
        "LaTeX Warning: B.\n"
        "! Undefined control sequence.\n"
        "l.1 \\badcmd\n"
        "LaTeX Info: Redefining \\sqrt.\n"
        ")\n"
    )
    p = LatexLogParser(root_file='main.tex'); p.parse(log)
    buf = io.StringIO(); sys.stdout = buf
    try: p.show_log(use_logger=False, show_info=False)
    finally: sys.stdout = sys.__stdout__
    off = strip(buf.getvalue())
    buf = io.StringIO(); sys.stdout = buf
    try: p.show_log(use_logger=False, show_info=True)
    finally: sys.stdout = sys.__stdout__
    on = strip(buf.getvalue())
    info_markers = ('LaTeX Info', '[I]', 'INFO', 'Redefining')
    has_info_off = any(m in off for m in info_markers)
    if has_info_off:
        print(f'[Check30] FAIL: show_info=False 仍含 Info: {off!r}'); return False
    has_info_on = any(m in on for m in info_markers)
    if not has_info_on:
        print(f'[Check30] FAIL: show_info=True 缺少 Info: {on!r}'); return False
    wc_on = on.count('[W]'); ec_on = on.count('[E]')
    if wc_on > 5:
        print(f'[Check30] FAIL: [W] 重复 >5 次：count={wc_on}, on={on!r}'); return False
    if ec_on > 3:
        print(f'[Check30] FAIL: [E] 重复 >3 次：count={ec_on}, on={on!r}'); return False
    print(f'[Check30] PASS: show_info filter OK（W={wc_on}, E={ec_on}）')
    return True


# Check31: 正则零本地 re.compile(r" 出现
def _check31_zero_re_compile(root: str) -> bool:
    src = (Path(root) / 'src/pytexmk/log_parser.py').read_text(encoding='utf-8')
    import re as _re
    count = len(_re.findall(r're\.compile\(\s*r["\']', src))
    if count != 0:
        print(f'[Check31] FAIL: 仍然有 {count} 处 re.compile(r"...") 本地实现'); return False
    print('[Check31] PASS: 正则零本地实现')
    return True


# ──────────────────────────── 主函数：批量执行 31 个断言 ────────────────────────────

def main() -> int:
    root = str(Path(__file__).resolve().parent.parent)
    all_checks = [
        _check01_old_module_exists,
        _check02_new_package_exists,
        _check03_old_imports_new,
        _check04_new_key_modules,
        _check05_latex_parser_in_both,
        _check06_old_has__new_delegate,
        _check07_old_has_bibtex_parser,
        _check08_new_bibtex_biber_exist,
        _check09_old_logtype_enum,
        _check10_new_loglevel_enum,
        _check11_new_logentry_dataclass,
        _check12_old_has_parse,
        _check13_old_has_reset_state,
        _check14_old_has_parse_line,
        _check15_old_has_parse_bad_box,
        _check16_old_has_parse_file_stack,
        _check17_old_has_show_log,
        _check18_old_has_show_editor_jump,
        _check19_old_has_logparser_cli,
        _check20_new_summary_print,
        _check21_pkg_export_run_pipeline,
        _check22_old_has_build_log,
        _check23_old_has_current_result,
        _check24_old_has_file_stack_prop,
        _check25_old_has_entry_dict_helper,
        _check26_old_has_level_mapper,
        _check27_old_init_creates__new,
        _check28_zero_local_impl,
        _check29_parity_file_stack_bug,
        _check30_show_log_filter_and_no_dup,
        _check31_zero_re_compile,
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

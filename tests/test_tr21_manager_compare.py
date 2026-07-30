from __future__ import annotations

import logging
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar, Literal

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pytexmk.pytexlogs.asymptote import AsymptoteParser
from pytexmk.pytexlogs.base import (
    BaseLogParser,
    LogEntry,
    LogLevel,
    ParsedLog,
)
from pytexmk.pytexlogs.biber import BiberParser
from pytexmk.pytexlogs.bibtex import BibtexParser
from pytexmk.pytexlogs.glossaries import GlossariesParser
from pytexmk.pytexlogs.latexlog import LatexLogParser
from pytexmk.pytexlogs.makeindex import MakeindexParser
from pytexmk.pytexlogs.minted import MintedParser
from pytexmk.pytexlogs.nomencl import NomenclParser
from pytexmk.pytexlogs.pythontex import PythontexParser
from pytexmk.pytexlogs.xindy import XindyParser

logging.basicConfig(level=logging.CRITICAL)

# ====== OLD MANAGER SNAPSHOT (mock old behavior) ======

@dataclass(slots=True)
class OldToolResultStats:
    entries_count: int = 0
    stats: dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)
class OldToolResult:
    tool_name: str = ""
    category: str = ""
    importance: Literal["high", "medium", "low"] = "low"
    source_path: str = ""
    raw_text: str = ""
    entries: list[LogEntry] = field(default_factory=list)
    stats: OldToolResultStats = field(default_factory=OldToolResultStats)

def _old_parsed_log_to_result(
    parsed: ParsedLog,
    step_name: str,
    old_step_to_category: dict[str, str],
    old_step_to_importance: dict[str, Literal["high", "medium", "low"]],
) -> OldToolResult:
    error_count = sum(1 for e in parsed.entries if e.level == LogLevel.ERROR)
    warning_count = sum(1 for e in parsed.entries if e.level == LogLevel.WARNING)
    merged_stats = dict(parsed.stats)
    merged_stats.setdefault("error", error_count)
    merged_stats.setdefault("warning", warning_count)
    return OldToolResult(
        tool_name=step_name,
        category=old_step_to_category.get(step_name, parsed.category or "custom"),
        importance=old_step_to_importance.get(step_name, parsed.importance or "low"),
        source_path=parsed.source_path,
        raw_text=parsed.raw_text,
        entries=parsed.entries,
        stats=OldToolResultStats(
            entries_count=len(parsed.entries),
            stats=merged_stats,
        ),
    )


class OldLogParserManager:
    _STEP_TO_PARSER: ClassVar[dict[str, type[BaseLogParser]]] = {
        "pdflatex": LatexLogParser,
        "xelatex": LatexLogParser,
        "lualatex": LatexLogParser,
        "latex": LatexLogParser,
        "bibtex": BibtexParser,
        "biber": BiberParser,
        "makeindex": MakeindexParser,
        "upmendex": MakeindexParser,
        "mendex": MakeindexParser,
        "xindy": XindyParser,
        "texindy": XindyParser,
        "makeglossaries": GlossariesParser,
        "glossaries": GlossariesParser,
        "nomencl": NomenclParser,
        "pythontex": PythontexParser,
        "asy": AsymptoteParser,
        "asymptote": AsymptoteParser,
        "minted": MintedParser,
    }

    _STEP_TO_CATEGORY: ClassVar[dict[str, str]] = {
        "pdflatex": "compile",
        "xelatex": "compile",
        "lualatex": "compile",
        "latex": "compile",
        "bibtex": "biblio",
        "biber": "biblio",
        "makeindex": "index",
        "upmendex": "index",
        "mendex": "index",
        "xindy": "index",
        "texindy": "index",
        "makeglossaries": "glossary",
        "glossaries": "glossary",
        "nomencl": "glossary",
        "pythontex": "code",
        "asy": "external",
        "asymptote": "external",
        "minted": "code",
    }

    _STEP_TO_IMPORTANCE: ClassVar[dict[str, Literal["high", "medium", "low"]]] = {
        "pdflatex": "high",
        "xelatex": "high",
        "lualatex": "high",
        "latex": "high",
        "bibtex": "high",
        "biber": "high",
        "makeindex": "medium",
        "upmendex": "medium",
        "mendex": "medium",
        "xindy": "medium",
        "texindy": "medium",
        "makeglossaries": "medium",
        "glossaries": "medium",
        "nomencl": "medium",
        "pythontex": "low",
        "asy": "low",
        "asymptote": "low",
        "minted": "low",
    }

    def discover_log_path(
        self,
        parser_cls: type[BaseLogParser],
        jobname: str,
        auxdir: str | Path,
    ) -> Path | None:
        aux = Path(auxdir)
        if parser_cls is LatexLogParser:
            for suffix in [".log"]:
                p = aux / f"{jobname}{suffix}"
                if p.exists():
                    return p
            return None
        if parser_cls is BibtexParser or parser_cls is BiberParser:
            for suffix in [".blg", ".bcf"]:
                p = aux / f"{jobname}{suffix}"
                if p.exists():
                    return p
            return None
        if parser_cls is MakeindexParser:
            for suffix in [".ilg"]:
                p = aux / f"{jobname}{suffix}"
                if p.exists():
                    return p
            return None
        if parser_cls is XindyParser:
            for suffix in (".glg", ".alg", ".slg", ".ilg"):
                p = aux / f"{jobname}{suffix}"
                if p.exists():
                    return p
            return None
        if parser_cls is GlossariesParser:
            for suffix in (".glg", ".alg", ".slg"):
                p = aux / f"{jobname}{suffix}"
                if p.exists():
                    return p
            return None
        if parser_cls is NomenclParser:
            for suffix in [".nlg"]:
                p = aux / f"{jobname}{suffix}"
                if p.exists():
                    return p
            return None
        if parser_cls is PythontexParser:
            for suffix in [".pytxcode"]:
                p = aux / f"{jobname}{suffix}"
                if p.exists():
                    return p
            return None
        if parser_cls is AsymptoteParser:
            for suffix in [".asy", ".log"]:
                p = aux / f"{jobname}{suffix}"
                if p.exists():
                    return p
            return None
        if parser_cls is MintedParser:
            for suffix in [".pygmented"]:
                p = aux / f"{jobname}{suffix}"
                if p.exists():
                    return p
            return None
        return None

    def run(
        self,
        jobname: str,
        auxdir: str | Path,
        steps: list[str],
        captured_outputs: dict[str, str] | None = None,
    ) -> list[OldToolResult]:
        captured_outputs = captured_outputs or {}
        results: list[OldToolResult] = []
        seen: set[tuple[str, str]] = set()

        for step_name in steps:
            parser_cls = self._STEP_TO_PARSER.get(step_name)
            if parser_cls is None:
                continue
            parser = parser_cls()
            parser_cls_name = parser_cls.__name__
            parsed: ParsedLog | None = None
            key: str | None = None

            if step_name in captured_outputs:
                key = f"captured:{step_name}"
                if (parser_cls_name, key) in seen:
                    continue
                text = captured_outputs[step_name]
                parsed = parser.parse(text)
                parsed.source_path = key
            else:
                log_path = self.discover_log_path(parser_cls, jobname, auxdir)
                if log_path is None:
                    continue
                key = str(log_path)
                if (parser_cls_name, key) in seen:
                    continue
                parsed = parser.parse_file(log_path)

            if parsed is not None and key is not None:
                seen.add((parser_cls_name, key))
                tool_result = _old_parsed_log_to_result(
                    parsed,
                    step_name=step_name,
                    old_step_to_category=self._STEP_TO_CATEGORY,
                    old_step_to_importance=self._STEP_TO_IMPORTANCE,
                )
                results.append(tool_result)

        return results


# ====== SYNTHETIC LOG GENERATION ======

def _write_synthetic_logs(tmpdir: Path, jobname: str) -> dict[str, str]:
    main_log = r"""This is pdfTeX, Version 3.141592653-2.6-1.40.25 (TeX Live 2024)
entering extended mode
(./main.tex
LaTeX2e <2023-11-01>
(/usr/local/texlive/2024/article.cls)
(./main.aux)
Overfull \hbox (15.0pt too wide) in paragraph at lines 42--45
[][]This is a really long line causing overfull hbox[]

] [2]
LaTeX Warning: Reference `fig:missing' on page 2 undefined on input line 60.

LaTeX Warning: Citation `unkn2024' on page 1 undefined on input line 30.

! Undefined control sequence.
l.100 \badmacro

[3] (./main.aux) )
Output written on main.pdf (3 pages, 123456 bytes).
Transcript written on main.log.
"""
    (tmpdir / f"{jobname}.log").write_text(main_log, encoding="utf-8")

    main_blg = """INFO - This is Biber 2.19
INFO - Logfile is 'main.blg'
INFO - Reading 'main.bcf'
INFO - Found 5 citekeys in bib section 0
ERROR - BibTeX subsystem: tmp.tex, line 88, syntax error: found "}", expected end of entry
WARN - I didn't find a database entry for 'key6' (section 0)
WARN - I didn't find a database entry for 'key7' (section 0)
INFO - Writing 'main.bbl' with encoding 'UTF-8'
"""
    (tmpdir / f"{jobname}.blg").write_text(main_blg, encoding="utf-8")

    main_bcf = """<?xml version="1.0" encoding="UTF-8"?>
<bcf:controlfile version="2.1">
  <bcf:citekey order="1">key1</bcf:citekey>
  <bcf:citekey order="2">key2</bcf:citekey>
</bcf:controlfile>
"""
    (tmpdir / f"{jobname}.bcf").write_text(main_bcf, encoding="utf-8")

    main_ilg = """This is makeindex, version 2.16 [TeX Live 2024].
Scanning input style file ./main.ist...done (1 attributes redefined).
Scanning input file main.idx...done (152 lines accepted, 2 rejected).
Processing...done (150 entries accepted, 0 rejected).
Sorting...done (312 comparisons).
Generating output file main.ind...done (456 lines written, 0 warnings).
Warning line 42 : No see also reference to `foo'
Output written in main.ind.
Transcript written in main.ilg.
"""
    (tmpdir / f"{jobname}.ilg").write_text(main_ilg, encoding="utf-8")

    main_glg = """This is makeindex, version 2.16 [TeX Live 2024].
Scanning input file main.glo...done (45 lines accepted).
Processing...done (42 entries accepted, 0 rejected).
Sorting...done.
Generating output file main.gls...done.
Warning -- Suppressing term that has no location.
Output written in main.gls.
Transcript written in main.glg.
"""
    (tmpdir / f"{jobname}.glg").write_text(main_glg, encoding="utf-8")

    main_alg = """This is makeindex, version 2.16 [TeX Live 2024].
Scanning input file main.acn...done (30 lines accepted).
Processing...done (28 entries accepted, 0 rejected).
Sorting...done.
Generating output file main.acr...done.
Warning -- Entry `foo' has no destination.
Output written in main.acr.
Transcript written in main.alg.
"""
    (tmpdir / f"{jobname}.alg").write_text(main_alg, encoding="utf-8")

    main_slg = """This is makeindex, version 2.16 [TeX Live 2024].
Scanning input file main.syg...done (12 lines accepted).
Processing...done (10 entries accepted).
Sorting...done.
Generating output file main.sys...done.
Warning -- Symbol entry `alpha' has no location.
Transcript written in main.slg.
"""
    (tmpdir / f"{jobname}.slg").write_text(main_slg, encoding="utf-8")

    main_nlg = """This is makeindex, version 2.16 [TeX Live 2024].
Scanning input file main.nlo...done (20 lines accepted).
Processing...done (18 entries accepted).
Sorting...done.
Generating output file main.nls...done (120 lines written).
Warning -- Nomenclature entry `sym1' has no description.
Transcript written in main.nlg.
"""
    (tmpdir / f"{jobname}.nlg").write_text(main_nlg, encoding="utf-8")

    main_pytxcode = """# PythonTeX Code File
# Generated by PythonTeX 0.17
print("Hello from PythonTeX")
Traceback (most recent call last):
  File "pythontex-files-main/main_defaultdefault1.py", line 5, in <module>
    NameError: name 'undefined_var' is not defined
PythonTeX: processed 3 code blocks
PythonTeX: 1 error(s) occurred
"""
    (tmpdir / f"{jobname}.pytxcode").write_text(main_pytxcode, encoding="utf-8")

    main_asy_log = """This is Asymptote version 2.85
Processing main-1.asy
Loading plain.asy
Loading graph.asy
Drawing box
error: /tmp/main-1.asy: 10: no matching function 'draw(unknown)'
warning: /tmp/main-1.asy: 15: label overlaps with other object
Output written on main-1.pdf
Transcript written on main.asy.log.
"""
    (tmpdir / f"{jobname}.asy.log").write_text(main_asy_log, encoding="utf-8")

    return {}


# ====== COMPARISON ======

def _result_signature(r, is_old: bool):
    return {
        "tool_name": r.tool_name,
        "category": r.category,
        "len(entries)": len(r.entries),
        "stats.entries_count": r.stats.entries_count,
        "stats.stats['error']": r.stats.stats.get("error", 0),
        "stats.stats['warning']": r.stats.stats.get("warning", 0),
    }


def main() -> int:
    print("=" * 70)
    print("TR-2.1: 新旧 LogParserManager.run() 结果对比")
    print("=" * 70)

    steps = [
        "pdflatex",
        "bibtex",
        "biber",
        "makeindex",
        "xindy",
        "makeglossaries",
        "nomencl",
        "pythontex",
        "minted",
        "asymptote",
        "pdflatex",
        "xelatex",
    ]
    jobname = "main"
    ok_all = True

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        captured = _write_synthetic_logs(tmpdir, jobname)

        old_mgr = OldLogParserManager()
        old_results = old_mgr.run(jobname, tmpdir, steps, captured)

        from pytexmk.pytexlogs.manager import LogParserManager as NewLogParserManager
        new_mgr = NewLogParserManager()
        new_results = new_mgr.run(jobname, tmpdir, steps, captured)

        print(f"\n[1] len(old_results) = {len(old_results)}")
        print(f"[2] len(new_results) = {len(new_results)}")
        if len(old_results) != len(new_results):
            print(f"  ✗ 长度不一致！ diff = {len(new_results) - len(old_results)}")
            ok_all = False
        else:
            print("  ✓ 长度一致")

        n = min(len(old_results), len(new_results))
        print(f"\n[3] 逐字段对比前 {n} 条结果：")
        for i in range(n):
            old_sig = _result_signature(old_results[i], is_old=True)
            new_sig = _result_signature(new_results[i], is_old=False)
            match = old_sig == new_sig
            status = "✓" if match else "✗"
            print(f"  [{i}] {status} old.tool={old_sig['tool_name']!r} new.tool={new_sig['tool_name']!r}")
            if not match:
                ok_all = False
                for k in old_sig:
                    ov = old_sig[k]
                    nv = new_sig[k]
                    if ov != nv:
                        print(f"      - {k}: old={ov!r} new={nv!r}")

        if ok_all:
            extra_old = len(old_results) - n
            extra_new = len(new_results) - n
            if extra_old or extra_new:
                ok_all = False
                print(f"\n  ✗ 额外结果: old多出{extra_old}, new多出{extra_new}")

    print("\n" + "=" * 70)
    if ok_all:
        print("[PASS] TR-2.1 新旧对比：Diff = 0，逐字段完全一致")
        return 0
    else:
        print("[FAIL] TR-2.1 存在差异，请检查上述报告")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

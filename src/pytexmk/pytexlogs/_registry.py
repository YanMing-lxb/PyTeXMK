"""解析器注册中心：定义 LogParserSpec 数据类与 LogParserRegistry，用于按 step 名称或日志文件后缀匹配对应的 BaseLogParser 实现，并内置 10 种默认工具（LaTeX/BibTeX/Biber/Makeindex/Xindy/Glossaries/Nomencl/PythonTeX/Asymptote/Minted）的注册逻辑。."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .asymptote import AsymptoteParser
from .base import BaseLogParser
from .biber import BiberParser
from .bibtex import BibtexParser
from .glossaries import GlossariesParser
from .latexlog import LatexLogParser
from .makeindex import MakeindexParser
from .minted import MintedParser
from .nomencl import NomenclParser
from .pythontex import PythontexParser
from .xindy import XindyParser


@dataclass(slots=True)
class LogParserSpec:
    step_names: list[str]
    log_suffixes: list[str]
    category: str
    importance: Literal["high", "medium", "low"]
    parser_cls: type[BaseLogParser]
    discover_hook: Callable[[str, Path], Path | None] | None = None

    def default_discover(self, jobname: str, auxdir: str | Path) -> Path | None:
        aux = Path(auxdir)
        for suffix in self.log_suffixes:
            p = aux / f"{jobname}{suffix}"
            if p.exists():
                return p
        return None


class LogParserRegistry:
    _instance: LogParserRegistry | None = None
    _default_instance: LogParserRegistry | None = None

    def __init__(self) -> None:
        self._step_to_spec: dict[str, LogParserSpec] = {}
        self._suffix_to_specs: dict[str, list[LogParserSpec]] = {}

    @classmethod
    def get_instance(cls) -> LogParserRegistry:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def get_default_registry(cls) -> LogParserRegistry:
        if cls._default_instance is None:
            cls._default_instance = cls()
            cls._default_instance._register_defaults()
        return cls._default_instance

    def _register_defaults(self) -> None:
        specs: list[LogParserSpec] = [
            LogParserSpec(
                step_names=["pdflatex", "xelatex", "lualatex", "latex"],
                log_suffixes=[".log"],
                category="compile",
                importance="high",
                parser_cls=LatexLogParser,
            ),
            LogParserSpec(
                step_names=["bibtex"],
                log_suffixes=[".blg", ".bcf"],
                category="bibliography",
                importance="high",
                parser_cls=BibtexParser,
            ),
            LogParserSpec(
                step_names=["biber"],
                log_suffixes=[".blg", ".bcf"],
                category="bibliography",
                importance="high",
                parser_cls=BiberParser,
            ),
            LogParserSpec(
                step_names=["makeindex", "upmendex", "mendex"],
                log_suffixes=[".ilg"],
                category="index",
                importance="medium",
                parser_cls=MakeindexParser,
            ),
            LogParserSpec(
                step_names=["xindy", "texindy"],
                log_suffixes=[".glg", ".alg", ".slg", ".ilg"],
                category="index",
                importance="medium",
                parser_cls=XindyParser,
            ),
            LogParserSpec(
                step_names=["makeglossaries", "glossaries"],
                log_suffixes=[".glg", ".alg", ".slg"],
                category="glossary",
                importance="medium",
                parser_cls=GlossariesParser,
            ),
            LogParserSpec(
                step_names=["nomencl"],
                log_suffixes=[".nlg"],
                category="glossary",
                importance="medium",
                parser_cls=NomenclParser,
            ),
            LogParserSpec(
                step_names=["pythontex"],
                log_suffixes=[".pytxcode"],
                category="code",
                importance="low",
                parser_cls=PythontexParser,
            ),
            LogParserSpec(
                step_names=["asy", "asymptote"],
                log_suffixes=[".asy", ".log"],
                category="external",
                importance="low",
                parser_cls=AsymptoteParser,
            ),
            LogParserSpec(
                step_names=["minted"],
                log_suffixes=[".pygmented"],
                category="code",
                importance="low",
                parser_cls=MintedParser,
            ),
        ]
        for spec in specs:
            self.register_spec(spec)

    def register_spec(self, spec: LogParserSpec) -> None:
        for step_name in spec.step_names:
            self._step_to_spec[step_name] = spec
        for suffix in spec.log_suffixes:
            if suffix not in self._suffix_to_specs:
                self._suffix_to_specs[suffix] = []
            self._suffix_to_specs[suffix].append(spec)

    def register(
        self,
        step_name: str,
        parser_cls: type[BaseLogParser],
        log_suffixes: list[str] | None = None,
        category: str = "custom",
        importance: Literal["high", "medium", "low"] = "low",
    ) -> None:
        spec = LogParserSpec(
            step_names=[step_name],
            log_suffixes=log_suffixes or [],
            category=category,
            importance=importance,
            parser_cls=parser_cls,
        )
        self.register_spec(spec)

    def lookup(self, step_name: str) -> LogParserSpec | None:
        return self._step_to_spec.get(step_name)

    def lookup_by_suffix(self, suffix: str) -> list[LogParserSpec]:
        return list(self._suffix_to_specs.get(suffix, []))

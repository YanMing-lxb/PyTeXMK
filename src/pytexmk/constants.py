# -*- coding: utf-8 -*-
"""
PyTeXMK 常量定义模块
"""

# 默认目录名称
DEFAULT_OUTPUT_DIR = "build"
DEFAULT_AUX_DIR = "auxiliary"

# 编译相关默认值
DEFAULT_COMPILE_TIMES = 2
DEFAULT_TIMEOUT = 300  # 秒
MAX_COMPILE_RETRIES = 5

# TeX 引擎名称
ENGINE_PDFLATEX = "pdflatex"
ENGINE_XELATEX = "xelatex"
ENGINE_LUALATEX = "lualatex"
ENGINE_LATEX = "latex"
ENGINE_PDFTEX = "pdftex"
ENGINE_XETEX = "xetex"
ENGINE_LUATEX = "luatex"
ENGINE_UPLATEX = "uplatex"
ENGINE_PLATEX = "platex"

SUPPORTED_ENGINES = [
    ENGINE_PDFLATEX,
    ENGINE_XELATEX,
    ENGINE_LUALATEX,
    ENGINE_LATEX,
    ENGINE_PDFTEX,
    ENGINE_XETEX,
    ENGINE_LUATEX,
    ENGINE_UPLATEX,
    ENGINE_PLATEX,
]

# BibTeX 相关工具
BIBER = "biber"
BIBTEX = "bibtex"
BIBTEX8 = "bibtex8"
PBIBTEX = "pbibtex"
UPBIBTEX = "upbibtex"

# 索引相关工具
MAKEINDEX = "makeindex"
XINDY = "xindy"
MAKEGLOSSARIES = "makeglossaries"

# 文件扩展名
TEX_EXTENSIONS = [".tex"]
LOG_EXTENSION = ".log"
AUX_EXTENSION = ".aux"
PDF_EXTENSION = ".pdf"
DVI_EXTENSION = ".dvi"
SYNCTEX_EXTENSION = ".synctex.gz"
OUT_EXTENSION = ".out"
TOC_EXTENSION = ".toc"
LOF_EXTENSION = ".lof"
LOT_EXTENSION = ".lot"
BBL_EXTENSION = ".bbl"
BLG_EXTENSION = ".blg"
BCF_EXTENSION = ".bcf"
RUN_EXTENSION = ".run.xml"
FLS_EXTENSION = ".fls"
FDB_LATEXMK_EXTENSION = ".fdb_latexmk"

# 辅助文件扩展名列表
AUXILIARY_EXTENSIONS = [
    ".aux",
    ".log",
    ".out",
    ".toc",
    ".lof",
    ".lot",
    ".bbl",
    ".blg",
    ".bcf",
    ".run.xml",
    ".fls",
    ".fdb_latexmk",
    ".synctex.gz",
    ".nav",
    ".snm",
    ".vrb",
    ".idx",
    ".ilg",
    ".ind",
    ".glo",
    ".gls",
    ".glg",
    ".ist",
    ".acn",
    ".acr",
    ".alg",
    ".loe",
    ".loa",
    ".lol",
]

# 配置文件名
CONFIG_FILENAME = "pytexmk.toml"
LOCAL_CONFIG_NAME = ".pytexmkrc"

# 日志文件中的关键标记
RERUN_CITATION_MARKERS = [
    "Citation(s) may have changed",
    "There were undefined citations",
    "Please rerun LaTeX",
]

RERUN_REFERENCE_MARKERS = [
    "Reference(s) may have changed",
    "There were undefined references",
    "Label(s) may have changed",
    "Please rerun to get cross-references right",
]

ERROR_MARKERS = [
    "!",
    "Error:",
    "Fatal error",
    "Emergency stop",
]

WARNING_MARKERS = [
    "Warning:",
    "Overfull",
    "Underfull",
    "Package warning",
    "Class warning",
]

# 退出码
EXIT_SUCCESS = 0
EXIT_GENERAL_ERROR = 1
EXIT_TOOLCHAIN_NOT_FOUND = 2
EXIT_COMPILATION_ERROR = 3
EXIT_COMPILATION_TIMEOUT = 4
EXIT_FILE_NOT_FOUND = 5
EXIT_CONFIG_ERROR = 6
EXIT_INVALID_ENGINE = 7

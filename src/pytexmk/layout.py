"""PyTeXMK 文件布局常量：产物后缀与目录排除集的唯一来源。

历史上 ``cli_state`` / ``build_state`` / ``compile_engine`` / ``aux_repair`` /
``cli_compile`` / ``file_ops`` / ``cli_watch`` 各自维护过一份近似集合，已经漂移
出过真实问题（``build_state`` 写了裸 ``.gz``、干跑与真删的排除目录不一致）。
新增后缀/目录时只改这里，不要在业务模块里另起一份。
"""

#: SyncTeX 定位文件的两种落盘格式。TeX 默认写 gzip 压缩的 ``.synctex.gz``；
#: ``-synctex=-1``（例如 ``-pa=-synctex=-1``）写明文 ``.synctex``。
#: 生成、归档、缓存校验、清理必须同时认这两种，否则明文 sidecar 会留在辅助目录。
SYNCTEX_SUFFIXES: tuple[str, ...] = (".synctex.gz", ".synctex")

# 输出文件后缀（编译结果，编译后从根目录迁移到 outdir）
OUT_SUFFIXES: tuple[str, ...] = (".pdf", *SYNCTEX_SUFFIXES)

# 辅助文件后缀（编译中间产物，编译前后在 auxdir 与根目录之间往返）
# 注意：这里不要写裸 `.gz` —— 它既会造出个永远不存在的 `<name>.gz`，
# 又会让 `-ca` 的递归清理把用户自己的 *.gz 数据文件一并删掉。
# `.synctex` / `.synctex.gz` 属输出侧（见 OUT_SUFFIXES），按目标清理走 `-C`。
# `.ist`（makeindex 样式）与用户自己的 `.xdy` 是**输入**文件，不能放进
# 无条件删除的集合；`.xdy` 确实可能由 makeglossaries 生成，因此保留在列表里
# （只参与搬运/清理）。`-ca/-Ca` 按后缀递归清理时 `.bbl/.xdv/.xdy` 一并删除，
# 不再按 jobname 判定所有权，也不再提示“可能属于作者”。
#
# 同样不要写裸 `.xml` / `.tmp`：它们不是 TeX 产物，而是用户常见的 XML 数据
# 与临时文件。biber/biblatex 真正生成的是 `.run.xml`（下面单独列出），
# 旧版把 `.xml` 当通配后缀，`-ca` 会把 `data/records.xml` 一并删掉。
AUX_SUFFIXES: tuple[str, ...] = (
    ".log", ".blg", ".ilg",
    ".aux", ".bbl",
    ".toc", ".lof", ".lot",
    ".out", ".bcf", ".idx", ".ind", ".nlo", ".nls", ".glo", ".gls",
    # glossaries 的每套 glossary 类型各有一组输入/输出/日志（acronym 用 acn/acr/alg）
    ".glg", ".alg", ".acn", ".acr", ".xdy",
    ".bak", ".spl", ".ent-x", ".ltx", ".los", ".lol", ".loc",
    ".listing", ".userbak", ".nav", ".snm", ".vrb", ".fls", ".xdv",
    ".fdb_latexmk", ".run.xml",
)

#: 每次编译都会重写、不参与"源文件是否变过"比对的产物。
#: 必须写完整后缀（``.synctex.gz``），不要写裸 ``.gz``：那会把用户的 .gz 数据
#: 文件当成产物跳过，源文件改了也不会触发重编。
VOLATILE_SUFFIXES: frozenset[str] = frozenset(
    {
        ".aux", ".out", ".toc", ".lof", ".lot", ".log", ".pdf", ".synctex.gz",
        ".synctex",
        ".bbl", ".blg", ".ilg", ".nlo", ".nls", ".bcf", ".run.xml", ".fls",
        ".xdv", ".spl", ".nav", ".snm", ".vrb", ".idx", ".ind", ".glo", ".gls",
        ".glg", ".alg", ".acn", ".acr", ".xdy",
        ".bak", ".userbak", ".listing", ".los", ".lol", ".loc", ".ltx",
        ".ent-x", ".fdb_latexmk",
    }
)

#: 源快照不参与比对的产物后缀。
#: 保留 PDF 图片、TeX 输入（.ltx）及自定义索引样式（.xdy）。
#: recorder 记录的实际输出由编译器按路径排除。
SOURCE_SNAPSHOT_EXCLUDED_SUFFIXES: frozenset[str] = VOLATILE_SUFFIXES - {".pdf", ".ltx", ".xdy"}

#: 从 .fls 收集投稿依赖时跳过的辅助产物后缀。
#: 同样保留 ``.pdf``：PDF 可能是真实图片输入（例如 \includegraphics{fig.pdf}）。
FLS_IGNORED_SUFFIXES: frozenset[str] = VOLATILE_SUFFIXES - {".pdf"}

#: `--watch` 轮询变化的源码后缀（编辑器改动的直接输入）
SOURCE_SUFFIXES: frozenset[str] = frozenset(
    {
        ".tex", ".bib", ".bst", ".cls", ".sty", ".def", ".clo",
        ".cfg", ".ist", ".tikz", ".bbx", ".cbx",
    }
)

#: 构建依赖快照要覆盖的源/资源后缀（C1：只盯 .tex 会漏掉图片、宏包、bib 的改动）
DEPENDENCY_SUFFIXES: frozenset[str] = frozenset(
    {
        ".tex", ".bib", ".bst", ".cls", ".sty", ".def", ".clo", ".cfg", ".ist",
        ".tikz", ".asy", ".lua", ".py", ".svg", ".pdf", ".png", ".jpg", ".jpeg",
        ".eps", ".bbx", ".cbx", ".lbx", ".glo", ".gls", ".nlo", ".nls", ".bcf",
    }
)

#: 只需要检查"括号是否配平/是否被截断"的行式辅助文件。
#: 不检查 .log / .pdf / .synctex.gz 等非结构化或二进制产物。
CHECKED_AUX_SUFFIXES: tuple[str, ...] = (
    ".aux", ".toc", ".lof", ".lot", ".out", ".bbl",
    ".idx", ".ind", ".nlo", ".nls", ".glo", ".gls", ".nav", ".snm",
)

#: 命名索引（imakeidx）的产物后缀：主干不是 jobname，静态 aux_files 覆盖不到
NAMED_INDEX_SUFFIXES: tuple[str, ...] = (".idx", ".ind", ".ilg")

#: 只由索引工具生成的辅助后缀。native 构建前清理根目录残留时只动这些，
#: 避免把用户手放的 .bbl / .aux 之类一并处理。**不含** `.ist`：样式文件是
#: 用户输入，删掉就等于静默删源码。
INDEX_ARTIFACT_SUFFIXES: tuple[str, ...] = (
    ".idx", ".ind", ".ilg", ".nlo", ".nls", ".glo", ".gls", ".glg",
    ".acn", ".acr", ".alg", ".xdy",
)

#: 可能由用户手写、不能无条件删除的索引类后缀：即使 auxdir 已有同名文件，
#: 也要先确认两份内容一致（即根目录只是同一产物的旧副本）才删。
INDEX_USER_EDITABLE_SUFFIXES: tuple[str, ...] = (".ist", ".xdy")

#: 永远不扫描/不清理的目录（VCS、虚拟环境、依赖目录）
EXCLUDED_DIRS: frozenset[str] = frozenset(
    {
        ".git", ".github", "__pycache__", "node_modules",
        "venv", ".venv", "env", "site-packages",
    }
)

#: `-ca` 递归清理额外跳过的目录（示例/测试/发布/文档不是辅助产物）
CLEAN_EXCLUDED_DIRS: frozenset[str] = EXCLUDED_DIRS | frozenset(
    {"examples", "tests", "dist", "docs"}
)

#: 编译/打包产物目录（既不是源码，也不该被当成子项目）
GENERATED_DIRS: frozenset[str] = frozenset(
    {"Build", "Auxiliary", "build", "out", "output", "dist", "Submission"}
)

#: 投稿包兜底收集的源/资源后缀；由构建依赖集派生，只剔除 biber 控制文件
#: （.bcf 是编译中间产物，不是作者手写依赖）。
SUBMISSION_FALLBACK_SUFFIXES: frozenset[str] = DEPENDENCY_SUFFIXES - {".bcf"}

#: 投稿包收集时永远跳过的目录；`.git/.github` 之外的点目录在调用方按
#: ``part.startswith(".")`` 统一处理。
SUBMISSION_EXCLUDED_DIRS: frozenset[str] = GENERATED_DIRS | {".git", ".github"}

#: `--watch` 轮询时跳过的目录
WATCH_SKIP_DIRS: frozenset[str] = EXCLUDED_DIRS | GENERATED_DIRS

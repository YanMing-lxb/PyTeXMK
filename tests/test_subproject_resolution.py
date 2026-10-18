"""用例：`-s` 子项目解析的健壮性（别名兜底、叶子目录名、.tex 条目）。

真实故障：用户在根目录跑 `pytexmk -s Review -l`，但根 .pytexmkrc 里还没有
`[subprojects]` 段（或用户从未跑过 `-ls`），于是报"未找到子项目: Review"，
而 `-ls` 明明刚刚把 Review 扫描出来了。
"""

import pytest

from pytexmk.context import ContextResolver, ProjectNotFoundError


class _Loader:
    def __init__(self, config):
        self.config = config

    def load_config(self, root):
        return self.config


class _Args:
    def __init__(self, subproject=None):
        self.subproject = subproject


def _make_subproject(root, rel, body="\\documentclass{article}\n\\begin{document}x\\end{document}\n"):
    """在 root/rel 下写一个能通过 has_magic 的主文件。"""
    target = root / rel
    target.mkdir(parents=True, exist_ok=True)
    (target / "main.tex").write_text(body, encoding="utf-8")
    return target


# ---------------------------------------------------- 配置里已有 [subprojects]
def test_resolve_by_leaf_dir_name(tmp_path):
    """`-ls` 把深层子项目记成完整相对路径，用户写叶子目录名也应命中。"""
    root = tmp_path / "root"
    root.mkdir()
    _make_subproject(root, "Section/en02")
    resolver = ContextResolver(_Loader({"subprojects": {"Section/en02": "Section/en02"}}))

    ctx = resolver.resolve(_Args(subproject="en02"), cwd=root)
    assert ctx.work_root == (root / "Section" / "en02").resolve()
    assert ctx.subproject == "Section/en02"


def test_resolve_is_case_insensitive(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    _make_subproject(root, "Review")
    resolver = ContextResolver(_Loader({"subprojects": {"Review": "Review"}}))

    ctx = resolver.resolve(_Args(subproject="review"), cwd=root)
    assert ctx.work_root == (root / "Review").resolve()


def test_resolve_accepts_backslashes(tmp_path):
    """Windows 用户习惯写反斜杠路径。"""
    root = tmp_path / "root"
    root.mkdir()
    _make_subproject(root, "Section/en02")
    resolver = ContextResolver(_Loader({"subprojects": {"Section/en02": "Section/en02"}}))

    ctx = resolver.resolve(_Args(subproject=r"section\en02"), cwd=root)
    assert ctx.work_root == (root / "Section" / "en02").resolve()


# ------------------------------------------- 配置里没有 [subprojects]（核心回归）
def test_resolve_falls_back_to_scan_when_config_has_no_subprojects(tmp_path):
    """回归：从未跑过 `-ls`、根配置里没有 [subprojects] 时，`-s` 仍应可用。

    历史实现只读持久化的 [subprojects]，别名表为空就直接抛
    ProjectNotFoundError，于是"扫描得到却编译不了"。
    """
    root = tmp_path / "root"
    root.mkdir()
    _make_subproject(root, "Review")
    resolver = ContextResolver(_Loader({}))  # 完全没有 subprojects 段

    ctx = resolver.resolve(_Args(subproject="Review"), cwd=root)
    assert ctx.work_root == (root / "Review").resolve()
    assert ctx.subproject == "Review"


def test_resolve_fallback_scan_ignores_excluded_dirs(tmp_path):
    """扫描兜底必须沿用 project_scan 的排除规则，不能把 Auxiliary/Build 当子项目。"""
    root = tmp_path / "root"
    root.mkdir()
    _make_subproject(root, "Review")
    _make_subproject(root, "Auxiliary")  # 默认排除目录
    resolver = ContextResolver(
        _Loader(
            {
                "project_scan": {"depth": 3, "exclude": []},
                "folder": {"outdir": "./Build/", "auxdir": "./Auxiliary/"},
            }
        )
    )

    with pytest.raises(ProjectNotFoundError):
        resolver.resolve(_Args(subproject="Auxiliary"), cwd=root)


def test_resolve_unknown_alias_still_raises(tmp_path):
    """兜底扫描不能把"确实不存在"的别名变成静默成功。"""
    root = tmp_path / "root"
    root.mkdir()
    _make_subproject(root, "Review")
    resolver = ContextResolver(_Loader({}))

    with pytest.raises(ProjectNotFoundError) as exc:
        resolver.resolve(_Args(subproject="NoSuchThing"), cwd=root)
    assert "NoSuchThing" in str(exc.value)


# ------------------------------------------------------ 条目直接指向 .tex 文件
def test_resolve_tex_entry_sets_work_file(tmp_path):
    """`name = "docs/main.tex"` 这类条目：工作目录取父目录，主文件单独记录。

    历史实现直接把文件路径当 work_root 交给 os.chdir()，会抛 NotADirectoryError。
    """
    root = tmp_path / "root"
    root.mkdir()
    (root / "docs").mkdir()
    (root / "docs" / "main.tex").write_text("x", encoding="utf-8")
    resolver = ContextResolver(_Loader({"subprojects": {"doc": "docs/main.tex"}}))

    ctx = resolver.resolve(_Args(subproject="doc"), cwd=root)
    assert ctx.work_root == (root / "docs").resolve()
    assert ctx.work_file == (root / "docs" / "main.tex").resolve()


def test_resolve_dir_entry_has_no_work_file(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    _make_subproject(root, "Review")
    resolver = ContextResolver(_Loader({"subprojects": {"Review": "Review"}}))

    ctx = resolver.resolve(_Args(subproject="Review"), cwd=root)
    assert ctx.work_file is None


# ------------------------------------------------------------ 无 -s 的常规路径
def test_resolve_without_subproject_uses_root(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    resolver = ContextResolver(_Loader({"subprojects": {"Review": "Review"}}))

    ctx = resolver.resolve(_Args(), cwd=root)
    assert ctx.work_root == root.resolve()
    assert ctx.subproject is None
    assert ctx.work_file is None

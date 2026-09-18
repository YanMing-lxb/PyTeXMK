"""用例 2：别名/路径解析、-s 解析、未命中抛 ProjectNotFoundError。"""
import pytest
from pytexmk.context import ContextResolver, ProjectNotFoundError


class _FakeLoader:
    def __init__(self, config):
        self.config = config

    def load_config(self, root):
        return self.config


class _Args:
    def __init__(self, subproject=None):
        self.subproject = subproject


def test_build_subprojects_flat_and_table_form(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    config = {
        "subprojects": {
            "doc": "docs/main.tex",              # flat `name = "path"`
            "grp": {"path": "chapters/intro"},   # `[subprojects.x] path = ...`
        }
    }
    sub = ContextResolver(None).build_subprojects(config, root)
    assert isinstance(sub, dict)
    assert sub["doc"] == (root / "docs/main.tex").resolve()
    assert sub["grp"] == (root / "chapters/intro").resolve()


def test_build_subprojects_ignores_absolute_and_parent_escape(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside"
    config = {
        "subprojects": {
            "abs": str(outside / "main.tex"),   # 绝对路径 -> 忽略
            "go_back": "../outside",             # .. 越界 -> 忽略
            "ok": "inside",                      # 合法相对路径 -> 保留
        }
    }
    sub = ContextResolver(None).build_subprojects(config, root)
    assert list(sub.keys()) == ["ok"]
    assert "abs" not in sub and "go_back" not in sub


def test_resolve_s_flag_and_not_found(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "docs").mkdir(parents=True)
    (root / "docs" / "main.tex").write_text("x", encoding="utf-8")
    config = {"subprojects": {"doc": "docs/main.tex"}}
    resolver = ContextResolver(_FakeLoader(config))

    # -s doc 命中：work_root 指向子项目
    ctx = resolver.resolve(_Args(subproject="doc"), cwd=root)
    assert ctx.root == root.resolve()
    assert ctx.work_root == (root / "docs/main.tex").resolve()
    assert ctx.subproject == "doc"

    # 未命中别名抛错
    with pytest.raises(ProjectNotFoundError):
        resolver.resolve(_Args(subproject="nope"), cwd=root)

    # 无 -s：work_root == root，subproject 为 None
    ctx2 = resolver.resolve(_Args(), cwd=root)
    assert ctx2.subproject is None
    assert ctx2.work_root == root.resolve()
    assert ctx2.subprojects["doc"] == (root / "docs/main.tex").resolve()
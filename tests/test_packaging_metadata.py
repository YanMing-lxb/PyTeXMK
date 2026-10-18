"""用例：pyproject.toml 的两套 dev 依赖声明必须保持一致，且都锁定 3.15。

背景：[project.optional-dependencies].dev（PEP 621 extras，给 pip 用户）与
[dependency-groups].dev（PEP 735，给 uv 开发者）无法互相 include，
一旦只改其中一处就会悄悄分叉（历史上 pillow 出现过 12.3 / 13.00 两个下限）。
这里用解析出的 TOML 直接比对两边，作为迁移与后续维护的护栏。
"""

import tomllib
from pathlib import Path

import pytest

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


@pytest.fixture(scope="module")
def pyproject() -> dict:
    with PYPROJECT.open("rb") as f:
        return tomllib.load(f)


def _lower_bounds(requirements: list[str]) -> dict[str, str | None]:
    """把 "name>=1.2.3" 归一化成 {小写名: 下限}，无下限则为 None。"""
    bounds: dict[str, str | None] = {}
    for requirement in requirements:
        name, sep, version = requirement.partition(">=")
        bounds[name.strip().lower()] = version.strip() if sep else None
    return bounds


def test_requires_python_covers_315(pyproject):
    assert pyproject["project"]["requires-python"] == ">=3.15"


def test_both_dev_tables_exist_and_match(pyproject):
    extras = pyproject["project"]["optional-dependencies"]["dev"]
    group = pyproject["dependency-groups"]["dev"]
    assert _lower_bounds(extras) == _lower_bounds(group)


def test_dev_lower_bounds_are_pinned(pyproject):
    """每个 dev 依赖都必须带下限：上限/浮动版本会让 CI 每次装到不同版本。"""
    for table in (
        pyproject["project"]["optional-dependencies"]["dev"],
        pyproject["dependency-groups"]["dev"],
    ):
        for requirement in table:
            assert ">=" in requirement, f"缺少版本下限: {requirement}"


def test_runtime_dependencies_carry_lower_bounds(pyproject):
    for requirement in pyproject["project"]["dependencies"]:
        assert ">=" in requirement, f"运行时依赖缺少版本下限: {requirement}"


def test_pep639_license_and_no_license_classifier(pyproject):
    """setuptools 对 PEP 639 有硬性要求：用 license 表达式时不得再有 License 分类器。"""
    project = pyproject["project"]
    assert project["license"] == "GPL-3.0-or-later"
    assert not [c for c in project.get("classifiers", []) if c.startswith("License ::")]


def test_ruff_and_pytest_target_315(pyproject):
    tool = pyproject["tool"]
    assert tool["ruff"]["target-version"] == "py315"
    assert tool["pytest"]["ini_options"]["minversion"] == "9.1"

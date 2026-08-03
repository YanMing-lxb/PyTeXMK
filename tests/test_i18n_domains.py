import sys
from pathlib import Path

# 插入项目 src 与 tools 到 sys.path 以便 import
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

# 再 import lang_tool（来自 tools/）
import lang_tool


def test_known_domains_all_detected():
    domains = {d for d, _ in lang_tool._get_modules()}
    core5 = {"compile_engine", "detection", "compile_report", "cli_workflow", "file_ops"}
    assert core5.issubset(domains), f"缺失核心域: {core5 - domains}"


def test_cli_domains_are_covered():
    domains = {d for d, _ in lang_tool._get_modules()}
    cli4 = {"__main__", "cli_args", "cli_workflow", "check_version"}
    assert cli4.issubset(domains), f"缺失 CLI 域: {cli4 - domains}"


def test_split_domains_all_independent():
    domains = {d for d, _ in lang_tool._get_modules()}
    split7 = {"lifecycle", "paths", "pdf_tools", "subprocess_runner", "tex_project", "timing", "ui_messages"}
    assert split7.issubset(domains), f"缺失拆分新域: {split7 - domains}"
    old3 = {"auxiliary_fun", "additional", "info_print"}
    assert old3 & domains == set(), f"旧共享域残留: {old3 & domains}"


def test_pot_count_equals_domain_count_after_extract(tmp_path):
    new_locale_en = tmp_path / "locale" / "en"
    new_locale_en.mkdir(parents=True, exist_ok=True)
    modules = lang_tool._get_modules()
    lang_tool._generate_pot_files(new_locale_en, modules)
    pot_files = list(new_locale_en.glob("*.pot"))
    assert len(pot_files) == len(modules), (
        f"pot 数 {len(pot_files)} != domain 数 {len(modules)}。"
        f" missing pots: {set(d for d,_ in modules) - {p.stem for p in pot_files}}"
    )
    for p in pot_files:
        assert p.stat().st_size > 0, f"{p.name} 为空！"

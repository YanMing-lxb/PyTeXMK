"""B 类「文案与实现对齐」回归：explain 默认交互模式、-ls 写回语义、-A 帮助转义、epilog 退出码。"""

from types import SimpleNamespace

import pytest

from pytexmk.cli import cli_args, cli_config, cli_early
from pytexmk.cli.cli_state import WorkflowState


def test_explain_shows_effective_interaction_mode(capsys):
    """未显式设置 interaction 时，安静模式也用 nonstopmode（quiet 只管显示）。"""
    state = SimpleNamespace(
        interaction="",
        non_quiet=False,
        project_name="main",
        output_name=None,
        compiled_program="XeLaTeX",
        native_build=True,
        outdir="Build",
        auxdir="Auxiliary",
        shell_escape="auto",
        synctex=True,
        extra_args=[],
        max_extra_compilations=8,
        preview_after_compile=False,
        submission_output_dir="./Submission/",
        preflight_enabled=True,
        args=SimpleNamespace(draft=False),
    )
    cli_config.explain(state)
    out = capsys.readouterr().out

    assert "nonstopmode" in out
    assert "batchmode" not in out


def test_explain_keeps_explicit_interaction(capsys):
    state = SimpleNamespace(
        interaction="errorstopmode",
        non_quiet=False,
        project_name="main",
        output_name=None,
        compiled_program="XeLaTeX",
        native_build=True,
        outdir="Build",
        auxdir="Auxiliary",
        shell_escape="auto",
        synctex=False,
        extra_args=[],
        max_extra_compilations=8,
        preview_after_compile=False,
        submission_output_dir="./Submission/",
        preflight_enabled=True,
        args=SimpleNamespace(draft=False),
    )
    cli_config.explain(state)
    out = capsys.readouterr().out

    assert "errorstopmode" in out


def test_list_subprojects_writes_back(monkeypatch, tmp_path, capsys):
    """`-ls` 直接写回；写回由 write_subprojects_to_rc 完成。"""
    monkeypatch.chdir(tmp_path)
    rc = tmp_path / ".pytexmkrc"
    rc.write_text("[subprojects]\n", encoding="utf-8")

    calls: list[object] = []

    def fake_write(path, entries):
        calls.append(path)
        path.write_text('[subprojects]\n"Cover" = "Cover"\n', encoding="utf-8")
        return True

    monkeypatch.setattr(cli_early, "write_subprojects_to_rc", fake_write)
    monkeypatch.setattr(cli_early, "print_subproject_table", lambda entries: None)
    monkeypatch.setattr(cli_early, "exit_pytexmk", lambda code=0: None)
    cp = SimpleNamespace(load_config=lambda root: {})

    cli_early._list_subprojects(cp)

    assert calls == [rc]
    assert "已更新" in capsys.readouterr().out


def test_list_subprojects_creates_config_when_missing(monkeypatch, tmp_path, capsys):
    """根配置缺失时先用模板创建，再把清单写回。"""
    monkeypatch.chdir(tmp_path)
    rc = tmp_path / ".pytexmkrc"
    monkeypatch.setattr(cli_early, "discover_subprojects", lambda root, config: [])
    monkeypatch.setattr(cli_early, "print_subproject_table", lambda entries: None)
    codes: list[int] = []
    monkeypatch.setattr(cli_early, "exit_pytexmk", lambda code=0: codes.append(code))

    def fake_init():
        rc.write_text("[subprojects]\n", encoding="utf-8")
        return True

    def fake_write(path, entries):
        path.write_text('[subprojects]\n"Cover" = "Cover"\n', encoding="utf-8")
        return True

    monkeypatch.setattr(cli_early, "write_subprojects_to_rc", fake_write)
    cp = SimpleNamespace(load_config=lambda root: {}, init_project_config=fake_init)

    cli_early._list_subprojects(cp)

    assert rc.exists()
    assert '"Cover"' in rc.read_text(encoding="utf-8")
    out = capsys.readouterr().out
    assert "已生成根项目配置文件" in out
    assert "已更新" in out
    assert codes == [0]


def test_list_subprojects_init_failure_exits_config_error(monkeypatch, tmp_path):
    """模板创建失败时不能假装写回成功。"""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli_early, "discover_subprojects", lambda root, config: [])
    monkeypatch.setattr(cli_early, "print_subproject_table", lambda entries: None)
    codes: list[int] = []
    monkeypatch.setattr(cli_early, "exit_pytexmk", lambda code=0: codes.append(code))
    cp = SimpleNamespace(
        load_config=lambda root: {},
        init_project_config=lambda: False,
    )

    cli_early._list_subprojects(cp)

    assert not (tmp_path / ".pytexmkrc").exists()
    assert codes == [4]


def test_list_subprojects_refuses_to_write_when_config_parse_failed(monkeypatch, tmp_path):
    """根配置解析失败时，不能用默认配置扫描结果覆盖用户文件。"""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".pytexmkrc").write_text("[subprojects]\n", encoding="utf-8")
    monkeypatch.setattr(cli_early, "discover_subprojects", lambda root, config: [])
    monkeypatch.setattr(cli_early, "print_subproject_table", lambda entries: None)
    monkeypatch.setattr(
        cli_early, "write_subprojects_to_rc", lambda rc, entries: pytest.fail("不应写盘")
    )
    codes = []
    monkeypatch.setattr(cli_early, "exit_pytexmk", lambda code=0: codes.append(code))
    cp = SimpleNamespace(
        load_config=lambda root: {},
        load_errors={"bad": "parse error"},
    )

    cli_early._list_subprojects(cp)

    assert codes == [4]


def test_list_subprojects_write_failure_exits_config_error(monkeypatch, tmp_path):
    """写盘失败不能仍以 0 退出。"""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".pytexmkrc").write_text("[subprojects]\n", encoding="utf-8")
    monkeypatch.setattr(cli_early, "write_subprojects_to_rc", lambda rc, entries: False)
    monkeypatch.setattr(cli_early, "print_subproject_table", lambda entries: None)
    codes = []
    monkeypatch.setattr(cli_early, "exit_pytexmk", lambda code=0: codes.append(code))
    cp = SimpleNamespace(load_config=lambda root: {})

    cli_early._list_subprojects(cp)

    assert codes == [4]


def test_list_subprojects_reports_unchanged(monkeypatch, tmp_path, capsys):
    """清单与现有段落一致时，不能谎报「已更新」。"""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".pytexmkrc").write_text("[subprojects]\n", encoding="utf-8")
    monkeypatch.setattr(cli_early, "write_subprojects_to_rc", lambda rc, entries: True)
    monkeypatch.setattr(cli_early, "print_subproject_table", lambda entries: None)
    monkeypatch.setattr(cli_early, "exit_pytexmk", lambda code=0: None)
    cp = SimpleNamespace(load_config=lambda root: {})

    cli_early._list_subprojects(cp)

    out = capsys.readouterr().out
    assert "未改动" in out
    assert "已更新" not in out


def test_list_subprojects_reports_update_when_changed(monkeypatch, tmp_path, capsys):
    """段落真被重写时才提示「已更新」。"""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".pytexmkrc").write_text("[subprojects]\n", encoding="utf-8")

    def fake_write(rc, entries):
        rc.write_text('[subprojects]\n"Cover" = "Cover"\n', encoding="utf-8")
        return True

    monkeypatch.setattr(cli_early, "write_subprojects_to_rc", fake_write)
    monkeypatch.setattr(cli_early, "print_subproject_table", lambda entries: None)
    monkeypatch.setattr(cli_early, "exit_pytexmk", lambda code=0: None)
    cp = SimpleNamespace(load_config=lambda root: {})

    cli_early._list_subprojects(cp)

    out = capsys.readouterr().out
    assert "已更新" in out


def test_all_subprojects_help_escapes_markup():
    """`[subprojects]` 会被 rich 当标记吞掉：只转义左方括号，右括号保持原样。"""
    parser = cli_args.build_parser()
    action = next(a for a in parser._actions if a.dest == "all_subprojects")
    assert "\\[subprojects]" in action.help
    assert "\\]" not in action.help  # rich 不认 `\]`，会原样留下反斜杠


def test_epilog_explains_errors_without_exit_code_table():
    """帮助页不再要求用户背退出码，只说明错误会直接给出原因。"""
    parser = cli_args.build_parser()
    epilog = parser.epilog
    epilog = epilog() if callable(epilog) else epilog
    assert "直接说明原因与下一步" in epilog
    assert "退出码：" not in epilog


def test_help_width_is_fixed_and_moderate():
    """帮助页固定为 96 列（按显示宽度，不随超宽终端拉伸）。"""
    from rich.cells import cell_len

    parser = cli_args.build_parser()
    lines = parser.format_help().splitlines()
    assert max(cell_len(line) for line in lines) <= 96


def test_workflow_state_has_attributes_used_by_explain():
    """explain 依赖的属性在 WorkflowState 上真实存在（避免测试与实现漂移）。"""
    import logging

    state = WorkflowState(args=SimpleNamespace(), logger=logging.getLogger("test"))
    for attr in ("interaction", "non_quiet", "project_name", "output_name", "compiled_program"):
        assert hasattr(state, attr)

"""``run_workflow`` 的阶段顺序与提前返回。

编译主流程按“早退出 → 批量 → watch → 清理 → 报告 → explain → 编译”分派。
顺序错了会出现“清理把 explain 抢走”“-ap 继承 watch 卡死”这类问题，而单测
各子模块都发现不了。这里用替身记录调用序列，断言只走一条分支。
"""
from types import SimpleNamespace

import pytest

from pytexmk.cli import cli_config, cli_report, cli_workflow


def _args(**overrides):
    values = {
        "verbose": False,
        "all_subprojects": False,
        "watch": False,
        "clean": False,
        "clean_out": False,
        "clean_recursive": False,
        "clean_recursive_out": False,
        "explain": False,
        "report": False,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.fixture
def wired(monkeypatch):
    """把所有阶段替换成记录器，返回 (calls, state)。"""
    calls: list[str] = []
    state = SimpleNamespace(project_name="main")

    monkeypatch.setattr(cli_workflow, "console", SimpleNamespace(print=lambda *a, **k: None))
    monkeypatch.setattr(cli_workflow, "setup_logger", lambda verbose: SimpleNamespace())
    monkeypatch.setattr(cli_workflow, "ConfigParser", lambda: SimpleNamespace())
    monkeypatch.setattr(
        cli_workflow.cli_early, "handle", lambda args, cp, logger: calls.append("early")
    )
    monkeypatch.setattr(
        cli_workflow,
        "_run_all_subprojects",
        lambda args, cp, logger: calls.append("all"),
    )
    monkeypatch.setattr(
        cli_workflow.cli_context,
        "build",
        lambda args, cp, logger: calls.append("build") or state,
    )
    monkeypatch.setattr(
        cli_workflow.cli_context, "resolve_target", lambda a, s: calls.append("resolve_target")
    )
    monkeypatch.setattr(
        cli_workflow.cli_context, "resolve_clean_target", lambda a, s: calls.append("resolve_clean")
    )
    monkeypatch.setattr(
        cli_workflow.cli_context, "apply_magic_comments", lambda s: calls.append("magic")
    )
    monkeypatch.setattr(cli_workflow.cli_compile, "clean_main", lambda a, s: calls.append("clean_main"))
    monkeypatch.setattr(
        cli_workflow.cli_compile, "clean_recursive", lambda a, s: calls.append("clean_recursive")
    )
    monkeypatch.setattr(cli_workflow.cli_compile, "run", lambda a, s: calls.append("run"))
    monkeypatch.setattr(cli_workflow.cli_compile, "finalize", lambda s: calls.append("finalize"))
    monkeypatch.setattr(
        cli_workflow.cli_compile,
        "apply_effective_build_plan",
        lambda a, s: calls.append("build_plan"),
    )
    monkeypatch.setattr(cli_report, "handle", lambda s: calls.append("report"))
    monkeypatch.setattr(cli_config, "explain", lambda s: calls.append("explain"))
    return calls, state


def test_plain_build_order(wired):
    calls, _ = wired
    cli_workflow.run_workflow(_args())
    assert calls == ["early", "build", "resolve_target", "magic", "run", "finalize"]


def test_all_subprojects_returns_before_context(wired):
    calls, _ = wired
    cli_workflow.run_workflow(_args(all_subprojects=True))
    assert calls == ["early", "all"]


def test_watch_returns_before_context(wired, monkeypatch):
    calls, _ = wired
    import pytexmk.cli.cli_watch as cli_watch

    monkeypatch.setattr(cli_watch, "watch_loop", lambda a: calls.append("watch"))
    cli_workflow.run_workflow(_args(watch=True))
    assert calls == ["early", "watch"]


def test_clean_main_exits_before_compile(wired):
    """``-c/-C`` 清理完成即退出，不再二次解析主文件、编译或收尾预览。"""
    calls, _ = wired
    cli_workflow.run_workflow(_args(clean=True))
    assert calls == [
        "early",
        "build",
        "resolve_target",
        "magic",
        "clean_main",
    ]


def test_clean_recursive_exits_before_compile(wired):
    calls, _ = wired
    cli_workflow.run_workflow(_args(clean_recursive=True))
    assert calls == [
        "early",
        "build",
        "resolve_clean",
        "magic",
        "clean_recursive",
    ]


def test_clean_recursive_out_exits_before_compile(wired):
    """``-Ca`` 同为递归清理：走不阻断的 resolve_clean，清理完直接退出。"""
    calls, _ = wired
    cli_workflow.run_workflow(_args(clean_recursive_out=True))
    assert calls == [
        "early",
        "build",
        "resolve_clean",
        "magic",
        "clean_recursive",
    ]


def test_report_stops_before_compile(wired):
    calls, _ = wired
    cli_workflow.run_workflow(_args(report=True))
    assert calls == ["early", "build", "resolve_target", "magic", "report"]


def test_explain_with_clean_still_explains_instead_of_cleaning(wired):
    calls, _ = wired
    cli_workflow.run_workflow(_args(clean=True, explain=True))
    assert calls == ["early", "build", "resolve_target", "magic", "build_plan", "explain"]


def test_no_project_name_skips_run_but_finalizes(wired):
    calls, state = wired
    state.project_name = None
    cli_workflow.run_workflow(_args())
    assert calls == ["early", "build", "resolve_target", "magic", "finalize"]


def test_before_build_hook_runs_before_dispatch(wired):
    calls, _ = wired

    def hook(state):
        calls.append("hook")

    cli_workflow.run_workflow(_args(), before_build=hook)
    assert calls == ["early", "build", "resolve_target", "magic", "hook", "run", "finalize"]


# ------------------------------------------------------------------ -sp 分派

def _run_args(**overrides):
    values = {
        "pdf_repair": None,
        "submission_pack": True,
        "force_rebuild": False,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.fixture
def pack_spy(monkeypatch):
    from pytexmk.cli import cli_compile

    calls: list[str] = []
    monkeypatch.setattr(
        cli_compile, "_compile", lambda a, s: calls.append("compile") or True
    )
    monkeypatch.setattr(
        cli_compile, "_submission_pack", lambda a, s: calls.append("pack")
    )
    return calls


def test_sp_alone_packs_without_entering_compile(pack_spy):
    """``-sp`` 单独使用时只打包：不预处理、不预检、不汇总警告。"""
    from pytexmk.cli import cli_compile

    cli_compile.run(_run_args(), SimpleNamespace())
    assert pack_spy == ["pack"]


def test_sp_with_force_compiles_then_packs(pack_spy):
    """``-f -sp`` 明确要求重编：先编译再打包。"""
    from pytexmk.cli import cli_compile

    cli_compile.run(_run_args(force_rebuild=True), SimpleNamespace())
    assert pack_spy == ["compile", "pack"]

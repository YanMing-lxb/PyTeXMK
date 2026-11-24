"""真实 CLI 的旗标验收：短旗标必须被 argparse 接受，而不是退出码 2。

进程内解析测试能证明 parser 认识旗标，但证明不了 ``python -m pytexmk`` 的
真实入口没有在分派前把参数丢掉。这里在空目录里跑真实进程：旗标合法时失败
原因是"没有主文件"（退出码 1），旗标不合法时是参数错误（退出码 2）。
"""
import pytest


@pytest.mark.parametrize("flag", ["-dr", "-pv", "-C", "-fr", "-sp"])
def test_flag_reaches_business_logic(tmp_path, run_cli, flag):
    result = run_cli(tmp_path, flag)
    combined = (result.stdout + result.stderr).lower()
    # 退出码 2 + usage 是 argparse 拒绝参数的特征
    assert result.returncode != 2, combined
    assert "usage:" not in combined, combined


def test_version_prints_single_line(tmp_path, run_cli):
    result = run_cli(tmp_path, "--version")
    assert result.returncode == 0
    assert len(result.stdout.strip().splitlines()) == 1

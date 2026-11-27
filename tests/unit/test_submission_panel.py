"""``-sp`` 完成面板：包信息合成一行，问题用 ``+-- [扫描解析]`` 分类头列前 5 项。"""

from pathlib import Path
from types import SimpleNamespace

from pytexmk.cli import cli_compile


def _make_pack(tmp_path: Path) -> Path:
    submit = tmp_path / "Submission"
    submit.mkdir(parents=True, exist_ok=True)
    pack = submit / "main-submission.zip"
    pack.write_bytes(b"x")
    return pack


def _run(tmp_path, monkeypatch, result, *, keep_preamble: bool = False, verbose: bool = False):
    from pytexmk import submission

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(submission, "build_pack", lambda *a, **k: result)
    state = SimpleNamespace(
        project_name="main",
        outdir="Build",
        auxdir="Auxiliary",
        output_name="main",
        submission_reproducible=True,
        submission_output_dir="./Submission/",
        submission_keep_preamble=keep_preamble,
    )
    cli_compile._submission_pack(SimpleNamespace(verbose=verbose), state)


def _compat(**overrides):
    fields = {
        "ok": True,
        "non_ascii_chars": {},
        "incompatible_packages": {},
        "char_locations": {},
        "tex_files": [],
    }
    fields.update(overrides)
    return SimpleNamespace(**fields)


def _result(pack: Path, **overrides):
    fields = {
        "zip_path": pack,
        "files": ["main.tex"],
        "pdf_pages": 3,
        "pdf_bytes": 1024,
        "rounds": 2,
        "sanitized": [],
        "sha256": "deadbeef",
        "log_path": pack.with_suffix(".log"),
        "compat": _compat(),
        # 产物检查的默认是“一切正常”，单个用例按需覆盖
        "used_fls": True,
        "fls_path": Path("Auxiliary/main.fls"),
        "stale_sources": [],
        "sanitize": True,
    }
    fields.update(overrides)
    return SimpleNamespace(**fields)


def test_panel_reports_issues_below_last_rule(tmp_path, monkeypatch, capsys):
    pack = _make_pack(tmp_path)
    result = _result(
        pack,
        compat=_compat(
            ok=False,
            non_ascii_chars={"板": 2, "式": 1},
            char_locations={"板": ["main.tex:9"], "式": ["main.tex:9"]},
            incompatible_packages={"ctex": "ctex 依赖 xeCJK/fontspec"},
        ),
    )
    _run(tmp_path, monkeypatch, result)

    out = capsys.readouterr().out
    assert "诊断日志" in out
    assert "main-submission.log" in out
    # 已净化的宏包只面板提示“无需手改”，不进红字错误清单
    assert "已在提交副本中注释，无需手改" in out
    assert "ctex:" not in out
    # 字符问题逐条报在面板收尾线与问题块收尾线之间
    lines = out.splitlines()
    rule_idx = [i for i, line in enumerate(lines) if line.strip().startswith("=")]
    block = "\n".join(lines[rule_idx[-2] : rule_idx[-1]])
    assert "未自动转换" not in out
    # 同一 文件:行号 的多个字符合并成一行，重复出现才写 ×N（不再显示 U+ 码）
    assert "main.tex:9  板×2 式（2 种）" in out
    assert "其余" not in out  # 合并后仅 1 项，不超过 5 行
    # 分类头给出“字符数/文件数”，块内标题带看日志的指引
    assert "+-- [扫描解析] · 2c/1f" in out
    assert "逐字位置与全部计数见诊断日志" in block
    # 体积与文件数/页数/轮数合成“包信息”一行
    assert "包信息" in out and "个文件，PDF 3 页，编译 2 轮)" in out


def test_panel_lists_packages_as_errors_when_preamble_kept(tmp_path, monkeypatch, capsys):
    """``keep_preamble=true`` 时宏包没被注释，必须进红字清单。"""
    pack = _make_pack(tmp_path)
    result = _result(
        pack,
        compat=_compat(
            ok=False,
            incompatible_packages={"ctex": "ctex 依赖 xeCJK/fontspec"},
        ),
    )
    _run(tmp_path, monkeypatch, result, keep_preamble=True)

    out = capsys.readouterr().out
    assert "ctex: ctex 依赖" in out
    assert "已在提交副本中注释" not in out


def test_panel_has_no_error_block_when_only_packages_are_sanitized(
    tmp_path, monkeypatch, capsys
):
    """只有被自动注释的宏包时，面板不应出现“需人工修改”的红字块。"""
    pack = _make_pack(tmp_path)
    result = _result(
        pack,
        compat=_compat(ok=False, incompatible_packages={"fontspec": "pdflatex 不支持 fontspec"}),
    )
    _run(tmp_path, monkeypatch, result)

    out = capsys.readouterr().out
    assert "未自动转换" not in out
    assert "fontspec（已在提交副本中注释，无需手改）" in out


def test_panel_pack_info_skips_unknown_pages_and_rounds(tmp_path, monkeypatch, capsys):
    """解析不到页数/轮数时只保留体积与文件数，不打印 ``?``。"""
    pack = _make_pack(tmp_path)
    result = _result(pack, pdf_pages=None, rounds=None)
    _run(tmp_path, monkeypatch, result)

    out = capsys.readouterr().out
    assert "包信息" in out
    assert "体积 0.00 MB (1 个文件)" in out
    assert "?" not in out


def test_panel_stops_after_five_issues_and_points_to_log(tmp_path, monkeypatch, capsys):
    pack = _make_pack(tmp_path)
    chars = {chr(0x4E00 + i): 1 for i in range(8)}
    result = _result(pack, compat=_compat(ok=False, non_ascii_chars=chars))
    _run(tmp_path, monkeypatch, result)

    out = capsys.readouterr().out
    issue_lines = [
        line for line in out.splitlines() if line.startswith("    ") and "其余" not in line
    ]
    assert len(issue_lines) == 5
    assert "其余 3 项见诊断日志" in out
    assert "+-- [扫描解析] · 8c " in out  # 全部字符都没位置信息时只报字符数


def test_cli_does_not_abort_when_pack_has_issues(tmp_path, monkeypatch, capsys):
    """有问题也只打印，不抛异常/不退出。"""
    pack = _make_pack(tmp_path)
    result = _result(pack, compat=_compat(ok=False, non_ascii_chars={"板": 1}))
    _run(tmp_path, monkeypatch, result)  # 不抛异常即通过
    assert "板" in capsys.readouterr().out


def test_panel_explains_counts_only_in_verbose(tmp_path, monkeypatch, capsys):
    """``-vb`` 才在分类头下加一行“c/f/p 是什么”。"""
    pack = _make_pack(tmp_path)
    result = _result(
        pack,
        compat=_compat(ok=False, non_ascii_chars={"板": 1}, char_locations={"板": ["main.tex:9"]}),
    )
    _run(tmp_path, monkeypatch, result)
    assert "c 字符" not in capsys.readouterr().out

    _run(tmp_path, monkeypatch, result, verbose=True)
    verbose_out = capsys.readouterr().out
    assert "计数：c 字符 / f 文件 / p 宏包" in verbose_out
    assert "main.tex:9  板 (U+677F)" in verbose_out  # 逐字符带码位


def test_panel_omits_issue_line_when_pack_is_clean(tmp_path, monkeypatch, capsys):
    pack = _make_pack(tmp_path)
    _run(tmp_path, monkeypatch, _result(pack))

    out = capsys.readouterr().out
    assert "main-submission.log" in out
    assert "扫描解析" not in out
    assert "依赖清单" not in out and "PDF 一致性" not in out


def test_panel_reports_missing_pdf_instead_of_green_pass(tmp_path, monkeypatch, capsys):
    """没有 PDF 时不能报“通过”：`.fls` 齐也不能证明包里有可核对的 PDF。"""
    pack = _make_pack(tmp_path)
    result = _result(pack, pdf_pages=None, pdf_bytes=None)
    _run(tmp_path, monkeypatch, result)

    out = capsys.readouterr().out
    flat = "".join(line.strip() for line in out.splitlines())
    assert "PDF 产物" in out
    assert "未找到" in flat and "Build/main.pdf" in flat
    assert "包内不带 PDF" in flat
    assert "通过：" not in out
    assert "main-submission.zip" in out  # 仍照常出包，不中断


def test_panel_warns_on_missing_fls_and_stale_pdf(tmp_path, monkeypatch, capsys):
    """产物检查只提示：缺 .fls 与 PDF 旧于源码各一行黄字，仍照常出包。"""
    pack = _make_pack(tmp_path)
    result = _result(
        pack,
        used_fls=False,
        fls_path=Path("Auxiliary/main.fls"),
        stale_sources=["Section/en/Section1.tex"],
    )
    _run(tmp_path, monkeypatch, result)  # 不抛异常即证明未中断

    out = capsys.readouterr().out
    flat = "".join(line.strip() for line in out.splitlines())  # 折行会把词切开，先压平
    assert "依赖清单" in out
    assert "Auxiliary" in out and ".fls" in out
    assert "兜底" in flat and "建议先编译一次" in flat
    assert "PDF 一致性" in out
    assert "PDF 早于 1 个源文件" in flat
    assert "main-submission.zip" in out  # 面板正常收尾，说明流程未被打断

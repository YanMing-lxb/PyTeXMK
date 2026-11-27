"""2026-11 审查整改的回归测试：PDF 零残留、非 ASCII 字符只报告、投稿包、构建参数。"""

import zipfile
from pathlib import Path

from pytexmk.build_state import BuildState
from pytexmk.compile import CompileLaTeX, detect_shell_escape
from pytexmk.pdf_tools import TMP_SUFFIX, PdfFileOperation
from pytexmk.submission import build_pack, scan_compat
from pytexmk.tex_project import MainFileOperation


def _blank_pdf(path: Path) -> Path:
    """生成一个最小合法 PDF（供修复/打包测试使用）。"""
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    with path.open("wb") as fh:
        writer.write(fh)
    return path


def test_native_biber_reads_control_file_from_auxdir(tmp_path, monkeypatch):
    """native 构建必须让 biber 从 auxdir 读取 main.bcf。

    回归：曾经把 ``--input-directory`` 固定为 ``.``，而 native 构建的 .bcf
    实际写在 ``Auxiliary/``；biber 找不到控制文件，真实 MiKTeX 端到端会以
    退出码 5 失败。这里只验证命令构造，避免测试依赖本机 biber。
    """
    from pytexmk.detection import BibEngine

    model = CompileLaTeX(
        project_name="main",
        compiled_program="PdfLaTeX",
        out_files=[],
        aux_files=[],
        outdir="Build",
        auxdir="Auxiliary",
        non_quiet=True,
        native=True,
    )
    captured: dict[str, list[str]] = {}
    monkeypatch.setattr(
        model.MSP, "run_command", lambda command, *a, **k: captured.update(command=command)
    )
    model.compile_bib(BibEngine.BIBER)

    command = captured["command"]
    input_index = command.index("--input-directory")
    output_index = command.index("--output-directory")
    assert command[input_index + 1] == "Auxiliary"
    assert command[output_index + 1] == "Auxiliary"
    assert command[-1] == "main"


# --------------------------------------------------------------------- C6


def test_pdf_repair_failure_keeps_original_and_no_residue(tmp_path, monkeypatch):
    """修复失败时原文件必须逐字节不变，且不留下临时文件（C6）。"""
    pdf = tmp_path / "fig.pdf"
    original = b"%PDF-1.4 broken but precious"
    pdf.write_bytes(original)

    monkeypatch.setattr("pytexmk.pdf_tools.shutil.which", lambda name: None)

    class BoomReader:
        def __init__(self, *a, **k):
            raise ValueError("broken")

    monkeypatch.setattr("pypdf.PdfReader", BoomReader)
    PdfFileOperation()._repair_one(pdf)

    assert pdf.read_bytes() == original
    assert list(tmp_path.glob(f"*{TMP_SUFFIX}")) == []
    assert list(tmp_path.glob("*.bak")) == []


def test_pdf_repair_success_replaces_atomically(tmp_path, monkeypatch):
    """修复成功：内容被替换、大小合理，且没有任何临时/备份残留。"""
    pdf = _blank_pdf(tmp_path / "fig.pdf")
    monkeypatch.setattr("pytexmk.pdf_tools.shutil.which", lambda name: None)
    PdfFileOperation()._repair_one(pdf)
    assert pdf.exists() and pdf.stat().st_size > 0
    assert list(tmp_path.glob(f"*{TMP_SUFFIX}")) == []
    assert list(tmp_path.glob("*.bak")) == []


def test_pdf_repair_scopes_to_fls_references(tmp_path, monkeypatch):
    """只修复 .fls 里真实引用的 PDF，仓库里无关 PDF 不动。"""
    root = tmp_path
    used = _blank_pdf(root / "figs" / "used.pdf") if (root / "figs").mkdir() is None else None
    unused = _blank_pdf(root / "figs" / "unused.pdf")
    (root / "main.fls").write_text(f"INPUT {used}\n", encoding="utf-8")
    monkeypatch.setattr("pytexmk.pdf_tools.shutil.which", lambda name: None)
    PdfFileOperation().pdf_repair("main", str(root), str(root / "Build"))
    assert used.exists() and unused.exists()
    assert list(root.rglob(f"*{TMP_SUFFIX}")) == []


def test_pdf_repair_ignores_pdf_outside_project(tmp_path):
    """项目外的共享 PDF 不能被 -rp 纳入原地修复候选。"""
    project = tmp_path / "project"
    project.mkdir()
    outside = _blank_pdf(tmp_path / "outside.pdf")
    (project / "main.fls").write_text(f"INPUT {outside}\n", encoding="utf-8")

    assert PdfFileOperation._referenced_pdfs(project, project / "main.fls") == set()


# ------------------------------------------------------ 3.9 非 ASCII 字符只报告


def test_scan_compat_reports_packages_and_chars(tmp_path):
    (tmp_path / "main.tex").write_text(
        "\\documentclass{article}\n\\usepackage{fontspec}\n正文 α 和 ☃\n% 注释里的 α 不算\n",
        encoding="utf-8",
    )
    report = scan_compat(tmp_path, [tmp_path / "main.tex"])
    assert "fontspec" in report.incompatible_packages
    assert report.non_ascii_chars == {"正": 1, "文": 1, "α": 1, "和": 1, "☃": 1}
    assert report.char_locations["α"] == ["main.tex:3"]


def test_build_pack_collects_fls_deps_but_not_bbl(tmp_path):
    root = tmp_path
    (root / "figs").mkdir()
    (root / "figs" / "fig1.pdf").write_bytes(b"%PDF-1.4 fake")
    (root / "main.tex").write_text(
        "\\documentclass{article}\\begin{document}α\\end{document}", encoding="utf-8"
    )
    aux = root / "Auxiliary"
    aux.mkdir()
    (aux / "main.bbl").write_text("% bbl content", encoding="utf-8")
    (root / "main.bbl").write_text("% hand-written root bbl", encoding="utf-8")
    (aux / "main.fls").write_text(
        "\n".join([
            f"INPUT {root / 'main.tex'}",
            f"INPUT {root / 'figs' / 'fig1.pdf'}",
            f"INPUT {root / 'Auxiliary' / 'main.aux'}",
            f"INPUT {root / 'main.bbl'}",
        ]),
        encoding="utf-8",
    )
    out = root / "Build"
    out.mkdir()
    _blank_pdf(out / "main.pdf")

    result = build_pack(root, "main", out, aux, submit_dir=root / "Submission")

    assert result.zip_path.exists()
    assert list((root / "Submission").glob("*.tmp")) == []
    with zipfile.ZipFile(result.zip_path) as zf:
        names = set(zf.namelist())
        assert "main.tex" in names
        assert "figs/fig1.pdf" in names
        assert "main.bbl" not in names
        assert "pytexmk-submission-notes.txt" in names
        main_tex = zf.read("main.tex").decode("utf-8")
        assert "\\ensuremath{\\alpha}" not in main_tex  # 正文保持原样
        assert "α" in main_tex
        info = zf.getinfo("main.tex")
        assert info.date_time == (1980, 1, 1, 0, 0, 0)  # 可复现
    assert result.compat.non_ascii_chars == {"α": 1}
    assert result.pdf_pages == 1
    assert not list(root.glob("pytexmk_submission_*"))


# ------------------------------------------------------------ 编译命令构造


def _compiler(tmp_path, **kwargs):
    kwargs.setdefault("shell_escape", False)
    kwargs.setdefault("native", False)
    return CompileLaTeX("main", "XeLaTeX", [".pdf"], [".aux"], "./Build/", "./Auxiliary/", False, **kwargs)


def test_native_command_uses_output_directory_and_no_two_stage(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cmd = _compiler(tmp_path, native=True)._latex_command()
    joined = " ".join(cmd)
    assert "-output-directory=" in joined
    assert "-jobname=main" in joined
    assert "-no-pdf" not in joined
    assert "-recorder" in cmd


def test_shell_escape_flag_only_when_requested(tmp_path):
    assert "-shell-escape" not in _compiler(tmp_path)._latex_command()
    assert "-shell-escape" in _compiler(tmp_path, shell_escape=True)._latex_command()


def test_detect_shell_escape(tmp_path):
    (tmp_path / "a.tex").write_text("\\usepackage{minted}", encoding="utf-8")
    (tmp_path / "b.tex").write_text("plain", encoding="utf-8")
    assert detect_shell_escape([tmp_path / "a.tex"]) is True
    assert detect_shell_escape([tmp_path / "b.tex"]) is False


# ------------------------------------------------------------- C1 / C2 state


def test_build_state_stores_build_key(tmp_path):
    store = BuildState(tmp_path, "main")
    assert store.save_round(
        round_no=2, fingerprint="fp", dims={"aux": 0}, converged=True, build_key="sha256:abc"
    )
    assert store.build_key() == "sha256:abc"


def test_source_snapshot_includes_image_via_fls(tmp_path, monkeypatch):
    from pytexmk.compile_engine import _iter_source_files

    monkeypatch.chdir(tmp_path)
    (tmp_path / "main.tex").write_text("\\documentclass{article}", encoding="utf-8")
    fig = tmp_path / "fig.png"
    fig.write_bytes(b"png")
    aux = tmp_path / "Auxiliary"
    aux.mkdir()
    (aux / "main.fls").write_text(f"INPUT {tmp_path / 'main.tex'}\nINPUT {fig}\n", encoding="utf-8")
    names = {Path(p).name for p in _iter_source_files("main", str(aux))}
    assert "fig.png" in names


def test_source_fallback_excludes_main_output_pdf(tmp_path, monkeypatch):
    """没有 .fls 时，根目录的 main.pdf 是输出而非输入，必须排除。"""
    from pytexmk.compile_engine import _iter_source_files

    monkeypatch.chdir(tmp_path)
    (tmp_path / "main.tex").write_text("\\documentclass{article}", encoding="utf-8")
    (tmp_path / "main.pdf").write_bytes(b"%PDF-1.4\n")
    names = {Path(p).name for p in _iter_source_files("main", "Auxiliary")}
    assert "main.tex" in names
    assert "main.pdf" not in names


# --------------------------------------------------------------------- C3


def test_draft_restore_writes_back_original(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    src = tmp_path / "main.tex"
    original = "\\documentclass[a4paper]{article}\nbegin\n"
    src.write_text(original, encoding="utf-8")
    mfo = MainFileOperation()
    mfo.draft_model("main", True)
    assert "draft" in src.read_text(encoding="utf-8")
    mfo.restore_draft()
    assert src.read_text(encoding="utf-8") == original


# ------------------------------------------------------------ SyncTeX 3.11


def test_synctex_check_ok(tmp_path, monkeypatch):
    import subprocess

    import pytexmk.synctex as synctex

    pdf = tmp_path / "main.pdf"
    tex = tmp_path / "main.tex"
    pdf.write_bytes(b"%PDF-1.4")
    # 修订后校验会先确认同名 synctex 文件存在，否则直接报“需要重新编译”
    (tmp_path / "main.synctex.gz").write_bytes(b"fake")
    tex.write_text("\\documentclass{article}\n\\begin{document}\nHi\n\\end{document}\n", encoding="utf-8")

    def fake_run(command, **_kwargs):
        if command[1] == "view":
            return subprocess.CompletedProcess(command, 0, "Page:1\nx:10.5\ny:20.5\n", "")
        return subprocess.CompletedProcess(command, 0, f"Input:{tex}\nLine:3\n", "")

    monkeypatch.setattr(synctex.shutil, "which", lambda _name: "synctex")
    monkeypatch.setattr(synctex.subprocess, "run", fake_run)
    report = synctex.check(pdf, tex, line=3)
    assert report.ok
    assert report.forward_page == 1
    assert report.reverse_file == str(tex)
    assert "SyncTeX 正常" in report.summary()


def test_synctex_check_detects_wrong_file(tmp_path, monkeypatch):
    import subprocess

    import pytexmk.synctex as synctex

    pdf = tmp_path / "main.pdf"
    tex = tmp_path / "main.tex"
    pdf.write_bytes(b"%PDF-1.4")
    (tmp_path / "main.synctex.gz").write_bytes(b"fake")
    tex.write_text("\\documentclass{article}\n", encoding="utf-8")

    def fake_run(command, **_kwargs):
        if command[1] == "view":
            return subprocess.CompletedProcess(command, 0, "Page:1\nx:1\ny:2\n", "")
        return subprocess.CompletedProcess(command, 0, f"Input:{tmp_path / 'other.tex'}\nLine:3\n", "")

    monkeypatch.setattr(synctex.shutil, "which", lambda _name: "synctex")
    monkeypatch.setattr(synctex.subprocess, "run", fake_run)
    report = synctex.check(pdf, tex, line=3, root=tmp_path)
    assert not report.ok
    assert any("定位到项目外的文件" in error for error in report.errors)


def test_includeonly_option_is_removed():
    r"""部分编译入口已删除：`-io/--includeonly` 不再是合法参数。"""
    import pytest

    from pytexmk.cli.cli_args import build_parser

    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["-io", "a,b"])
    assert exc.value.code == 2

"""`.fls` 解析单一入口的回归测试。"""

from pytexmk.fls import iter_fls_inputs


def test_iter_fls_inputs_reads_input_lines(tmp_path):
    fls = tmp_path / "main.fls"
    fls.write_text(
        "PWD /tmp\n"
        "INPUT /tmp/main.tex\n"
        "INPUT /tmp/fig with space.pdf\n"
        "OUTPUT /tmp/main.pdf\n",
        encoding="utf-8",
    )
    assert list(iter_fls_inputs(fls)) == [
        "/tmp/main.tex",
        "/tmp/fig with space.pdf",
    ]


def test_iter_fls_inputs_missing_file_is_empty(tmp_path):
    assert list(iter_fls_inputs(tmp_path / "missing.fls")) == []

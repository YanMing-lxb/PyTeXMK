"""用例 3 & 5：配置合并优先级、缺失配置静默兜底且不落盘。"""
from pytexmk.config import DEFAULT_CONFIG, _merge_dict


def test_merge_dict_override_and_fallback():
    base = {"a": 1, "b": {"x": 1, "y": 2}, "c": "keep"}
    over = {"b": {"y": 20, "z": 30}, "c": "new"}
    merged = _merge_dict(base, over)
    assert merged["a"] == 1            # 未覆盖键保留默认
    assert merged["b"]["x"] == 1       # 深层未覆盖字段保留
    assert merged["b"]["y"] == 20      # 深层覆盖
    assert merged["b"]["z"] == 30      # 深层新增
    assert merged["c"] == "new"
    assert base["b"]["y"] == 2         # 不修改原始 dict


def test_load_config_priority(tmp_path, make_parser):
    user_rc = tmp_path / "user"
    user_rc.mkdir()
    (user_rc / ".pytexmkrc").write_text(
        'quiet_mode = false\ndefault_file = "user_main"\ncompiled_program = "PDFLaTeX"\n',
        encoding="utf-8",
    )
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / ".pytexmkrc").write_text(
        'compiled_program = "LuaLaTeX"\nfolder = { outdir = "./Out" }\n',
        encoding="utf-8",
    )
    parser = make_parser(user_rc)
    cfg = parser.load_config(proj)

    assert cfg["quiet_mode"] is False                # 用户 rc 覆盖默认 True
    assert cfg["default_file"] == "user_main"        # 用户 rc 覆盖默认
    assert cfg["compiled_program"] == "LuaLaTeX"     # 项目 rc 覆盖用户/默认
    assert cfg["folder"]["outdir"] == "./Out"        # 项目新增深层键
    assert cfg["folder"]["auxdir"] == "./Auxiliary/"  # 内置默认兜底保留
    assert DEFAULT_CONFIG["quiet_mode"] is True      # 内置默认未被污染


def test_load_config_missing_uses_default_silently(tmp_path, make_parser):
    empty = tmp_path / "empty"
    empty.mkdir()
    parser = make_parser(tmp_path / "no_user_rc")
    cfg = parser.load_config(empty)

    assert cfg["default_file"] == "main"
    assert cfg["compiled_program"] == "XeLaTeX"
    # 缺配置不抛错、不落盘
    assert not (empty / ".pytexmkrc").exists()
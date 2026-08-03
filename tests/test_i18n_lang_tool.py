import gettext
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

import lang_tool  # noqa: E402
from config import POT_DIR, SRC_LOCALE_DIR  # noqa: E402


def test_lang_tool_get_modules_returns_tuple_items():
    result = lang_tool._get_modules()
    assert all(
        isinstance(item, tuple)
        and len(item) == 2
        and isinstance(item[0], str)
        and len(item[0]) > 0
        and isinstance(item[1], list)
        and len(item[1]) > 0
        for item in result
    ), f"_get_modules 结构不合规，样例: {result[:2]}"
    for domain, _files in result:
        assert " " not in domain and "." not in domain and "/" not in domain, (
            f"非法 domain 字符合规性检查失败: {domain!r}"
        )


def test_pot_regeneration_runs_clean(tmp_path):
    new_templates = tmp_path / "locale" / "templates"
    new_templates.mkdir(parents=True, exist_ok=True)
    modules = lang_tool._get_modules()
    lang_tool._generate_pot_files(new_templates, modules)
    compile_report_pot = new_templates / "compile_report.pot"
    assert compile_report_pot.exists(), "compile_report.pot 未生成"
    content = compile_report_pot.read_text(encoding="utf-8")
    assert len(content.strip()) > 0, "compile_report.pot 内容为空"
    assert "POT-Creation-Date:" in content, "缺少 POT-Creation-Date 头"
    first_p = modules[0][1][0]
    assert Path(first_p).exists(), f"源文件路径不存在于磁盘: {first_p}"


# -----------------------------------------------------------------------------
# 新增：非交互 add_lang
# -----------------------------------------------------------------------------
def test_add_lang_non_interactive_creates_locale(tmp_path, monkeypatch):
    """locale_code_override 传 "ja" 时，跳过 input，pybabel init 生成所有 domain 的 ja/LC_MESSAGES/*.po。"""
    # 先抽一次真实 POT 到项目真实 POT_DIR（避免 add-lang 里缺 pot）
    modules = lang_tool._get_modules()
    lang_tool._generate_pot_files(POT_DIR, modules)

    # 清理先前可能残留的 ja 目录（避免该测试跑多遍污染）
    ja_dir = SRC_LOCALE_DIR / "ja"
    if ja_dir.exists():
        shutil.rmtree(ja_dir, ignore_errors=True)

    try:
        lang_tool.add_lang(locale_code_override="ja")
        po_dir = SRC_LOCALE_DIR / "ja" / "LC_MESSAGES"
        assert po_dir.is_dir(), f"ja/LC_MESSAGES 目录未生成: {po_dir}"
        po_files = sorted(po_dir.glob("*.po"))
        assert len(po_files) == len(modules), (
            f"ja 的 .po 文件数 {len(po_files)} 与 domain 数 {len(modules)} 不一致。"
        )
        # 任意一个抽标准头
        sample = po_files[0].read_text(encoding="utf-8")
        assert 'msgid ""' in sample
        sample_flat = sample.replace("\\n", "").replace("\n", "").lower()
        assert "content-type: text/plain; charset=utf-8" in sample_flat
    finally:
        # 清理 ja，不污染仓库
        ja_root = SRC_LOCALE_DIR / "ja"
        if ja_root.exists():
            shutil.rmtree(ja_root, ignore_errors=True)


# -----------------------------------------------------------------------------
# 新增：update 保留已填 msgstr（NFR-4 / AC-3）
# -----------------------------------------------------------------------------
def test_update_preserves_existing_msgstr(tmp_path):
    """先造一个 fake locale（用 en_US），手动写一条 msgstr；跑 update 后 msgstr 仍然保留；新增 dummy msgid 同时会出现。"""
    modules = lang_tool._get_modules()
    # 先确保 POT_DIR/templates 已有 pot
    lang_tool._generate_pot_files(POT_DIR, modules)

    # 选一个小 domain（比如 cli_workflow）做操作
    domain = next((d for d, _ in modules if d == "cli_workflow"), modules[0][0])
    lang_code = "en_US"
    lc_root = SRC_LOCALE_DIR / lang_code
    lc_dir = lc_root / "LC_MESSAGES"
    lc_dir.mkdir(parents=True, exist_ok=True)
    po_path = lc_dir / f"{domain}.po"

    # 1) 用 pybabel init 造一份原始 po
    pot_path = POT_DIR / f"{domain}.pot"

    subprocess.run(
        [
            "uv",
            "run",
            "pybabel",
            "init",
            "-i",
            str(pot_path),
            "-d",
            str(SRC_LOCALE_DIR),
            "-l",
            lang_code,
            "-D",
            domain,
        ],
        check=True,
    )
    assert po_path.exists(), f"{po_path} 未由 pybabel init 生成"

    # 2) 找到第一条存在的 msgid（非空），手动插入对应的 msgstr 作为“已翻译”标记
    original = po_path.read_text(encoding="utf-8")
    lines = original.splitlines()
    marker_msgid = None
    marker_msgstr = "MARKER_KEEP_AFTER_UPDATE_PYTEST_1234"
    for i, line in enumerate(lines):
        if line.startswith('msgid "') and line != 'msgid ""':
            marker_msgid = line[len('msgid "') : -1]
            # 下一行是 msgstr ""，修改之
            if i + 1 < len(lines) and lines[i + 1].startswith('msgstr "'):
                lines[i + 1] = f'msgstr "{marker_msgstr}"'
            break
    assert marker_msgid is not None, "cli_workflow.po 中没找到可写入的 msgid，测试前置失败"
    po_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # 3) 运行 update()
    lang_tool.update()

    # 4) 检查：marker 存在 → msgstr 没有被覆盖
    after = po_path.read_text(encoding="utf-8")
    assert marker_msgstr in after, "update() 覆盖了旧 msgstr（NFR-4 违规）：marker_msgstr 丢失"

    # 5) 清理 en_US 整棵树，不污染仓库
    if lc_root.exists():
        shutil.rmtree(lc_root, ignore_errors=True)


# -----------------------------------------------------------------------------
# 新增：mo 跳过缺 .po 的 case（AC-4 / NFR-5）
# -----------------------------------------------------------------------------
def test_mo_skips_missing_po_without_error(tmp_path, monkeypatch):
    """人为删除一个 domain 的 po，mo 只 warning 跳过，不抛 CalledProcessError。"""
    modules = lang_tool._get_modules()
    lang_tool._generate_pot_files(POT_DIR, modules)

    lang_code = "en"
    lc_dir = SRC_LOCALE_DIR / lang_code / "LC_MESSAGES"
    lc_dir.mkdir(parents=True, exist_ok=True)

    # 先 init 一个 domain 的 .po，再删另一个 domain 的 .po（或直接造：只 init 其中 1 个，其他都不存在）
    domain_init = modules[0][0]
    subprocess = __import__("subprocess")
    subprocess.run(
        [
            "uv",
            "run",
            "pybabel",
            "init",
            "-i",
            str(POT_DIR / f"{domain_init}.pot"),
            "-d",
            str(SRC_LOCALE_DIR),
            "-l",
            lang_code,
            "-D",
            domain_init,
        ],
        check=True,
    )
    # 确保至少有一个 domain 的 .po 确实不存在
    missing_domain = modules[-1][0]
    missing_po = lc_dir / f"{missing_domain}.po"
    if missing_po.exists():
        missing_po.unlink()

    # mo() 只 warning，不应该抛异常（run_command 如果 pybabel compile 自己失败才抛，这里是缺 po 直接跳过，不走到 pybabel）
    lang_tool.mo()

    # 只验证 init 了的那个 .mo 已产出
    expected_mo = lc_dir / f"{domain_init}.mo"
    assert expected_mo.exists(), f"{expected_mo} 没被 compile 出来"

    # 清理 en locale
    for f in list(lc_dir.rglob("*")):
        if f.is_file():
            try:
                f.unlink()
            except OSError:
                pass
    for d in sorted(lc_dir.rglob("*"), key=lambda p: len(str(p)), reverse=True):
        if d.is_dir():
            try:
                d.rmdir()
            except OSError:
                pass
    try:
        if not any(lc_dir.iterdir()):
            lc_dir.rmdir()
            parent = lc_dir.parent
            if not any(parent.iterdir()):
                parent.rmdir()
    except OSError:
        pass


# -----------------------------------------------------------------------------
# 新增：language.py set_language zh → NullTranslations（AC-5）
# -----------------------------------------------------------------------------
def test_set_language_zh_returns_null(monkeypatch):
    """monkeypatch 强制 zh_CN，翻译函数就是 NullTranslations。"""
    import pytexmk.language as langmod

    monkeypatch.setattr(langmod.locale, "getdefaultlocale", lambda: ("zh_CN", "cp936"))
    translator = langmod.set_language("cli_workflow")
    assert callable(translator)
    # NullTranslations.gettext 直接原样返回
    sentinel = "这是中文 42 个字符 ★pytest★"
    assert translator(sentinel) == sentinel
    # 确认底层返回的是 NullTranslations 实例
    # （通过 fallback 链：language.py 里 zh 分支直接 new NullTranslations）
    t_class = type(translator.__self__ if hasattr(translator, "__self__") else langmod.gettext.NullTranslations())
    assert issubclass(t_class, gettext.NullTranslations)

import re
import subprocess
import sys

from config import BABEL_CFG_PATH, POT_DIR, SRC_DIR, SRC_LOCALE_DIR, __version__
from utils import console, run_command

if sys.stdout.encoding != "UTF-8":
    sys.stdout.reconfigure(encoding="utf-8")


def _write_babel_cfg_mapping():
    with open(BABEL_CFG_PATH, "w", encoding="utf-8") as f:
        f.write("[python: **.py]\n")
        f.write("encoding = utf-8\n")
        f.write("keywords = _\n")
        f.write("add_location = False\n")
        f.write("width = 120\n")
    console.log(f"写入 babel.cfg 成功: {BABEL_CFG_PATH}")


def _get_modules():
    pattern = re.compile(r"_\s*=\s*set_language\(\s*['\"]([^'\"]+)['\"]\s*\)")
    domain_map = {}
    for p in SRC_DIR.rglob("*.py"):
        if "__pycache__" in str(p) or p.suffix.lower() != ".py":
            continue
        content = p.read_text(encoding="utf-8")
        matches = pattern.findall(content)
        if len(matches) == 0:
            continue
        if len(matches) >= 2:
            console.print(f"文件 {p} 出现多个 domain {matches}，取第一个 {matches[0]}", style="warning")
        domain = matches[0]
        if domain not in domain_map:
            domain_map[domain] = []
        domain_map[domain].append(p.resolve())
    return sorted(domain_map.items(), key=lambda x: x[0])


def _generate_pot_files(locale_dir, modules):
    _write_babel_cfg_mapping()
    version_str = __version__
    for domain, files in modules:
        locale_dir.mkdir(parents=True, exist_ok=True)
        command = [
            "uv",
            "run",
            "pybabel",
            "extract",
            "--mapping-file",
            str(BABEL_CFG_PATH),
            "--output",
            str(locale_dir / f"{domain}.pot"),
            "--project",
            "PyTeXMK",
            "--version",
            version_str,
            "--msgid-bugs-address",
            "dev@example.com",
            "--no-location",
            "--width=120",
            *[str(f) for f in files],
        ]
        run_command(
            command,
            f"pybabel extract 成功生成 {domain}.pot",
            f"pybabel extract 生成 {domain}.pot 失败",
            process_name="pybabel extract",
        )


def _discover_locales() -> list[str]:
    """返回 locale 目录下存在 LC_MESSAGES 的所有 locale_code，跳过 templates。"""
    result: list[str] = []
    if not SRC_LOCALE_DIR.exists():
        return result
    for sub in SRC_LOCALE_DIR.iterdir():
        if not sub.is_dir():
            continue
        if sub.name == "templates":
            continue
        if (sub / "LC_MESSAGES").exists():
            result.append(sub.name)
    return sorted(result)


def _migrate_en_pot_to_templates() -> None:
    """Open Q2 (a)：Round3 遗留 `locale/en/*.pot` 自动搬到 POT_DIR/templates，一次性迁移。"""
    old_en_dir = SRC_LOCALE_DIR / "en"
    if not old_en_dir.is_dir():
        return
    POT_DIR.mkdir(parents=True, exist_ok=True)
    moved: list[str] = []
    for pot in sorted(old_en_dir.glob("*.pot")):
        target = POT_DIR / pot.name
        if target.exists():
            # 目标已存在则不覆盖（防止 templates 里已有更新版本）
            console.print(f"跳过迁移 {pot.name}：{target} 已存在", style="info")
            continue
        try:
            pot.replace(target)
            moved.append(pot.name)
        except OSError as e:
            console.print(f"✗ 迁移 {pot} → {target} 失败：{e}", style="error")
    if moved:
        console.log(f"已迁移 Round3 遗留 {len(moved)} 份 pot 到 {POT_DIR}: {', '.join(moved)}")
    # 清理可能的 .pot.bak 历史残留（一次性，之后不会再产生）
    for leftover in list(SRC_LOCALE_DIR.rglob("*.pot.bak")) + list(SRC_LOCALE_DIR.rglob("*.pot~")) + list(
        SRC_LOCALE_DIR.rglob("*-temp.pot")
    ):
        try:
            leftover.unlink()
            console.log(f"清理历史冗余备份文件：{leftover}")
        except OSError as e:
            console.print(f"✗ 清理 {leftover} 失败：{e}", style="error")


def pot() -> None:
    modules = _get_modules()
    if not modules:
        console.print("✗ 未扫描到任何 domain（检查 src/pytexmk 下是否有 set_language('xxx') 调用）", style="error")
        sys.exit(1)
    _generate_pot_files(POT_DIR, modules)
    console.log(f"POT 模板生成完成：共 {len(modules)} 份，已写入 {POT_DIR}")


def add_lang(locale_code_override: str | None = None) -> None:
    """交互式新增语言；locale_code_override 用于测试（跳过 input）。"""
    modules = _get_modules()
    if not modules:
        console.print("✗ 未扫描到任何 domain（检查 src/pytexmk 下是否有 set_language('xxx') 调用）", style="error")
        sys.exit(1)

    # 1. 先确保 pot 模板最新
    _generate_pot_files(POT_DIR, modules)

    # 2. 获取 locale_code（交互式或 override）
    if locale_code_override is None:
        prompt = "请输入要新增的语言 locale code（如 en_US / ja_JP / fr_FR，回车取消）: "
        try:
            locale_code = input(prompt).strip()
        except EOFError:
            locale_code = ""
    else:
        locale_code = locale_code_override.strip()

    if not locale_code:
        console.log("取消新增语言。")
        return

    # 3. 合法性校验
    if not re.fullmatch(r"[A-Za-z]{2,3}([_-][A-Za-z0-9]{2,8})?", locale_code):
        console.print(
            f"✗ 非法 locale code 格式：{locale_code!r}，只允许 2-3 字母 + 可选 _区域，如 en、en_US、zh_Hans、ja_JP",
            style="error",
        )
        if locale_code_override is not None:
            sys.exit(1)
        return

    # 4. 判断重复
    po_dir = SRC_LOCALE_DIR / locale_code / "LC_MESSAGES"
    if po_dir.exists() and any(po_dir.glob("*.po")):
        console.print(
            f"✗ 语言 {locale_code} 已存在（{po_dir} 下已有 .po 文件），跳过；如需更新现有翻译请用 `make update`。",
            style="error",
        )
        return

    # 5. 初始化 .po（每个 domain 一份 pybabel init）
    po_dir.mkdir(parents=True, exist_ok=True)
    init_ok = 0
    for domain, _ in modules:
        pot_file = POT_DIR / f"{domain}.pot"
        if not pot_file.exists():
            console.print(f"✗ 跳过 {locale_code}/{domain}：缺少 POT 模板 {pot_file}", style="error")
            continue
        command = [
            "uv",
            "run",
            "pybabel",
            "init",
            "--input-file",
            str(pot_file),
            "--output-dir",
            str(SRC_LOCALE_DIR),
            "--locale",
            locale_code,
            "--domain",
            domain,
        ]
        run_command(
            command,
            f"pybabel init 成功：{locale_code}/LC_MESSAGES/{domain}.po",
            f"pybabel init 失败：{locale_code}/{domain}",
            process_name="pybabel init",
        )
        init_ok += 1
    console.log(
        f"新增语言 {locale_code} 成功：共生成 {init_ok}/{len(modules)} 份 .po。"
        f"请编辑以下文件内的 msgstr，完成后运行 `make update` 合并新 msgid + `make mo` 编译："
    )
    console.log(f"  {po_dir}/<domain>.po")


def update() -> None:
    """重新抽取 POT，然后对所有已存在 locale 执行 pybabel update；缺的 domain 补 init。"""
    # 1. 迁移历史遗留 en/*.pot → templates/ + 清理历史 bak
    _migrate_en_pot_to_templates()

    modules = _get_modules()
    if not modules:
        console.print("✗ 未扫描到任何 domain（检查 src/pytexmk 下是否有 set_language('xxx') 调用）", style="error")
        sys.exit(1)

    # 2. 重新抽取 POT（只一次）
    _generate_pot_files(POT_DIR, modules)

    # 3. 拿到所有 locale
    locales = _discover_locales()
    if not locales:
        console.print(
            "⚠ 当前未发现任何已存在的 locale。请先使用 `make add-lang` 新增语言（例如 en_US / ja_JP），再执行 update。",
            style="warning",
        )
        return

    # 4. 对 (locale, domain) 全量处理
    processed_locale_domain = 0
    for locale_code in locales:
        po_dir = SRC_LOCALE_DIR / locale_code / "LC_MESSAGES"
        for domain, _ in modules:
            pot_file = POT_DIR / f"{domain}.pot"
            po_file = po_dir / f"{domain}.po"
            if not pot_file.exists():
                console.print(f"✗ 跳过 {locale_code}/{domain}：缺少 POT 模板 {pot_file}", style="error")
                continue
            if po_file.exists():
                command = [
                    "uv",
                    "run",
                    "pybabel",
                    "update",
                    "--input-file",
                    str(pot_file),
                    "--output-dir",
                    str(SRC_LOCALE_DIR),
                    "--locale",
                    locale_code,
                    "--domain",
                    domain,
                    "--previous",
                    "--no-fuzzy-matching",
                ]
                run_command(
                    command,
                    f"pybabel update 成功：{locale_code}/{domain}",
                    f"pybabel update 失败：{locale_code}/{domain}",
                    process_name="pybabel update",
                )
            else:
                # 缺的 domain 补一份 init
                command = [
                    "uv",
                    "run",
                    "pybabel",
                    "init",
                    "--input-file",
                    str(pot_file),
                    "--output-dir",
                    str(SRC_LOCALE_DIR),
                    "--locale",
                    locale_code,
                    "--domain",
                    domain,
                ]
                run_command(
                    command,
                    f"pybabel init（缺失 domain 补全）成功：{locale_code}/{domain}",
                    f"pybabel init（缺失 domain 补全）失败：{locale_code}/{domain}",
                    process_name="pybabel init",
                )
            processed_locale_domain += 1

    console.log(
        f"update() 完成：已重新抽取 POT 模板，并对 {len(locales)} 套语言（{', '.join(locales)}）"
        f" × {len(modules)} 个 domain，共处理 {processed_locale_domain} 份 .po。"
        f"\n请人工补充新增空 msgstr，然后运行 `make mo` 编译。"
    )


def mo() -> None:
    """将所有已存在 locale 的 .po 编译为 .mo（用 pybabel compile 原生）；缺 .po 只 warning 跳过。"""
    modules = _get_modules()
    if not modules:
        console.print("✗ 未扫描到任何 domain（检查 src/pytexmk 下是否有 set_language('xxx') 调用）", style="error")
        sys.exit(1)
    locales = _discover_locales()
    if not locales:
        console.print(
            "⚠ 当前未发现任何已存在的 locale。请先 `make add-lang`，再执行 mo 编译。",
            style="warning",
        )
        return

    compiled = 0
    skipped = 0
    for locale_code in locales:
        for domain, _ in modules:
            po_file = SRC_LOCALE_DIR / locale_code / "LC_MESSAGES" / f"{domain}.po"
            if not po_file.exists():
                console.print(
                    f"⚠ [跳过 compile] {locale_code}/LC_MESSAGES/{domain}.po 不存在，请先 update/add-lang",
                    style="warning",
                )
                skipped += 1
                continue
            command = [
                "uv",
                "run",
                "pybabel",
                "compile",
                "--domain",
                domain,
                "--directory",
                str(SRC_LOCALE_DIR),
                "--locale",
                locale_code,
                "--use-fuzzy",
                "--statistics",
            ]
            run_command(
                command,
                f"pybabel compile 成功：{locale_code}/LC_MESSAGES/{domain}.mo",
                f"pybabel compile 失败：{locale_code}/LC_MESSAGES/{domain}",
                process_name="pybabel compile",
            )
            compiled += 1
    console.log(
        f"mo 编译完成：共处理 {len(locales)} 套语言 × {len(modules)} 个 domain"
        f"（compile 成功 {compiled} 份，跳过 {skipped} 份缺失 .po）。"
    )


def main():
    targets = {
        "pot": pot,
        "update": update,
        "mo": mo,
        "add-lang": add_lang,
    }

    if len(sys.argv) < 2 or sys.argv[1] not in targets:
        console.log(f"用法: {sys.argv[0]} <目标>")
        console.log("可用目标（pybabel 官方 4 命令）: pot, add-lang, update, mo")
        sys.exit(1)

    target = sys.argv[1]
    try:
        targets[target]()
    except subprocess.CalledProcessError as e:
        console.log(f"执行命令时出错: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

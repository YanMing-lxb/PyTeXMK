import re
import sys

from config import LANG_EN_DIR, SRC_DIR
from utils import console, run_command

if sys.stdout.encoding != "UTF-8":
    sys.stdout.reconfigure(encoding="utf-8")


def _contains_uncommented_set_language(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        content = file.readlines()

    for line in content:
        # 去除行首和行尾的空白字符
        stripped_line = line.strip()
        # 检查是否包含未注释的 _ = set_language('config')
        if re.match(r"^\s*_\s*=\s*set_language\(.+\)\s*$", stripped_line):
            return True
    return False


def _get_modules():
    modules = []
    for f in SRC_DIR.glob("*.py"):
        if _contains_uncommented_set_language(f):
            modules.append(f.stem)
    return modules


def _generate_pot_files(locale_dir, modules):
    for module in modules:
        py_file = SRC_DIR / f"{module}.py"
        temp_pot = locale_dir / f"{module}-temp.pot"
        run_command(["xgettext", "--output", str(temp_pot), str(py_file)])
        console.log(f"生成临时 .pot 文件: {temp_pot}")


def _update_pot_files(locale_dir, modules):
    for module in modules:
        temp_pot = locale_dir / f"{module}-temp.pot"
        original_pot = locale_dir / f"{module}.pot"

        if not original_pot.exists():
            if temp_pot.exists():
                temp_pot.rename(original_pot)
                console.log(
                    f"原始 .pot 文件 {original_pot} 不存在：\n将临时 .pot 文件 {temp_pot} 重命名为 {original_pot}"
                )
            else:
                console.log(f"警告: 临时 .pot 文件 {temp_pot} 不存在，跳过更新")
            continue

        run_command(["msgmerge", "--update", str(original_pot), str(temp_pot)])
        console.log(f"更新 .pot 文件: {original_pot}")


def _generate_mo_files(locale_dir, modules):
    for module in modules:
        pot_file = locale_dir / f"{module}.pot"
        mo_dir = locale_dir / "LC_MESSAGES"
        mo_dir.mkdir(exist_ok=True, parents=True)
        mo_file = mo_dir / f"{module}.mo"

        if not pot_file.exists():
            console.log(f"警告: {pot_file} 不存在，跳过更新")
            continue

        run_command(["msgfmt", "-o", str(mo_file), str(pot_file)])
        console.log(f"生成 .mo 文件: {mo_file}")


def _cleanup_temp_pot_files(locale_dir, modules):
    for module in modules:
        temp_pot = locale_dir / f"{module}-temp.pot"
        if temp_pot.exists():
            temp_pot.unlink()
            console.log(f"删除临时 .pot 文件: {temp_pot}")


def pot():
    _generate_pot_files(LANG_EN_DIR, _get_modules())
    console.log("生成 .pot 文件完成")


def mo():
    _generate_mo_files(LANG_EN_DIR, _get_modules())
    console.log("生成 .mo 文件完成")


def poup():
    _generate_pot_files(LANG_EN_DIR, _get_modules())
    _update_pot_files(LANG_EN_DIR, _get_modules())
    _generate_mo_files(LANG_EN_DIR, _get_modules())
    _cleanup_temp_pot_files(LANG_EN_DIR, _get_modules())
    console.log("更新 .pot 和 .mo 文件完成")

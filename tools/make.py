import subprocess
import shutil
import re
import sys
from pathlib import Path
from rich.console import Console




console = Console()

def clean():
    dirs_to_remove = ['build', 'dist', Path('src') / 'pytexmk.egg-info']
    for d in dirs_to_remove:
        path = Path(d)
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
            console.log(f"已删除目录: {path}")
    
    for pycache_dir in Path('.').rglob('__pycache__'):
        shutil.rmtree(pycache_dir, ignore_errors=True)
        console.log(f"已删除目录: {pycache_dir}")
    
    for pyc_file in Path('.').rglob('*.pyc'):
        try:
            pyc_file.unlink()
            console.log(f"已删除文件: {pyc_file}")
        except Exception as e:
            console.log(f"删除文件 {pyc_file} 时出错: {e}")
    
    console.log("清理完成")

def build_all():
    subprocess.run(['python', '-m', 'build'], check=True)
    console.log("构建完成")

def html():
    readme_md = Path('README.md')
    readme_html = Path('README.html')
    target_dir = Path('src/pytexmk/data')
    
    subprocess.run(['pandoc', str(readme_md), '-o', str(readme_html)], check=True)
    
    if not target_dir.exists():
        target_dir.mkdir(parents=True)
        console.log(f"已创建目录: {target_dir}")
    
    target_html = target_dir / 'README.html'
    shutil.move(str(readme_html), str(target_html))
    console.log(f"生成 HTML 并移动到 {target_html}")

def rst():
    readme_md = Path('README.md')
    readme_rst = Path('README.rst')
    subprocess.run(['pandoc', '-s', '-t', 'rst', str(readme_md), '-o', str(readme_rst)], check=True)
    console.log("生成 RST 文件")

def run_tests():
    subprocess.run(['python', 'tests/test.py'], check=True)
    console.log("测试完成")

def testwhl():
    clean()
    build_all()
    subprocess.run(['pip', 'uninstall', '-y', 'pytexmk'], check=True)
    whl_files = list(Path('dist').glob('*.whl'))
    if not whl_files:
        raise FileNotFoundError("dist 目录中没有找到 .whl 文件")
    subprocess.run(['pip', 'install', str(whl_files[0])], check=True)
    subprocess.run(['python', 'tests/test.py', '-w'], check=True)
    subprocess.run(['pip', 'uninstall', '-y', 'pytexmk'], check=True)
    clean()
    console.log("测试 .whl 文件完成")

def inswhl():
    clean()
    build_all()
    subprocess.run(['pip', 'uninstall', '-y', 'pytexmk'], check=True)
    whl_files = list(Path('dist').glob('*.whl'))
    if not whl_files:
        raise FileNotFoundError("dist 目录中没有找到 .whl 文件")
    subprocess.run(['pip', 'install', str(whl_files[0])], check=True)
    console.log("安装 pytexmk*.whl 成功")

def get_version():
    version_file = Path('src/pytexmk/version.py')
    if not version_file.exists():
        raise FileNotFoundError(f"文件 {version_file} 不存在")
    
    with open(version_file, 'r', encoding='utf-8') as file:
        content = file.read()
    
    version_match = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", content)
    if not version_match:
        raise ValueError(f"无法在 {version_file} 中找到 __version__ 变量")
    
    return version_match.group(1)

def upload():
    version = get_version()
    tag_name = f"v{version}"
    
    # 创建标签
    subprocess.run(['git', 'tag', tag_name], check=True)
    console.log(f"创建标签: {tag_name}")
    
    # 推送标签
    subprocess.run(['git', 'push', 'origin', tag_name], check=True)
    console.log(f"推送标签: {tag_name}")
    
    clean()
    console.log("上传完成")

def pot():
    locale_dir = Path('src/pytexmk/locale/en')
    modules = ['__main__', 'additional', 'check_version', 'compile', 'config', 'info_print', 'latexdiff', 'logger_config', 'run']
    for module in modules:
        pot_file = locale_dir / f'{module}.pot'
        py_file = Path(f'src/pytexmk/{module}.py')
        subprocess.run(['xgettext', '--output', str(pot_file), str(py_file)], check=True)
        console.log(f"生成 .pot 文件: {pot_file}")
    console.log("生成 .pot 文件完成")

def mo():
    locale_dir = Path('src/pytexmk/locale/en')
    modules = ['__main__', 'additional', 'check_version', 'compile', 'config', 'info_print', 'latexdiff', 'logger_config', 'run']
    for module in modules:
        pot_file = locale_dir / f'{module}.pot'
        mo_dir = locale_dir / 'LC_MESSAGES'
        mo_dir.mkdir(exist_ok=True, parents=True)
        mo_file = mo_dir / f'{module}.mo'
        subprocess.run(['msgfmt', '-o', str(mo_file), str(pot_file)], check=True)
        console.log(f"生成 .mo 文件: {mo_file}")
    console.log("生成 .mo 文件完成")

def poup():
    locale_dir = Path('src/pytexmk/locale/en')
    modules = ['__main__', 'additional', 'check_version', 'compile', 'config', 'info_print', 'latexdiff', 'logger_config', 'run']
    for module in modules:
        py_file = Path(f'src/pytexmk/{module}.py')
        temp_pot = locale_dir / f'{module}-temp.pot'
        subprocess.run(['xgettext', '--output', str(temp_pot), str(py_file)], check=True)
        console.log(f"生成临时 .pot 文件: {temp_pot}")
    for module in modules:
        temp_pot = locale_dir / f'{module}-temp.pot'
        original_pot = locale_dir / f'{module}.pot'
        subprocess.run(['msgmerge', '--update', str(original_pot), str(temp_pot)], check=True)
        console.log(f"更新 .pot 文件: {original_pot}")
    mo()
    for module in modules:
        temp_pot = locale_dir / f'{module}-temp.pot'
        if temp_pot.exists():
            temp_pot.unlink()
            console.log(f"删除临时 .pot 文件: {temp_pot}")
    console.log("更新 .pot 和 .mo 文件完成")

def main():
    targets = {
        'all': build_all,
        'clean': clean,
        'html': html,
        'rst': rst,
        'test': run_tests,
        'testwhl': testwhl,
        'inswhl': inswhl,
        'upload': upload,
        'pot': pot,
        'mo': mo,
        'poup': poup,
    }

    if len(sys.argv) < 2 or sys.argv[1] not in targets:
        console.log(f"用法: {sys.argv[0]} <目标>")
        console.log("可用目标:", ', '.join(targets.keys()))
        sys.exit(1)

    target = sys.argv[1]
    try:
        targets[target]()
    except subprocess.CalledProcessError as e:
        console.log(f"执行命令时出错: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
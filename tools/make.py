import subprocess
import shutil
import sys
from pathlib import Path

def clean():
    dirs_to_remove = ['build', 'dist', Path('src') / 'pytexmk.egg-info']
    for d in dirs_to_remove:
        path = Path(d)
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
    
    for pycache_dir in Path('.').rglob('__pycache__'):
        shutil.rmtree(pycache_dir, ignore_errors=True)
    
    for pyc_file in Path('.').rglob('*.pyc'):
        try:
            pyc_file.unlink()
        except Exception as e:
            print(f"Error deleting {pyc_file}: {e}")
    
    print("Clean completed")

def build_all():
    subprocess.run(['python', '-m', 'build'], check=True)

def html():
    readme_md = Path('README.md')
    readme_html = Path('README.html')
    target_dir = Path('src/pytexmk/data')
    
    subprocess.run(['pandoc', str(readme_md), '-o', str(readme_html)], check=True)
    
    if not target_dir.exists():
        target_dir.mkdir(parents=True)
    
    target_html = target_dir / 'README.html'
    shutil.move(str(readme_html), str(target_html))
    print("Generated HTML and moved to src/pytexmk/data/README.html")

def rst():
    readme_md = Path('README.md')
    readme_rst = Path('README.rst')
    subprocess.run(['pandoc', '-s', '-t', 'rst', str(readme_md), '-o', str(readme_rst)], check=True)
    print("Generated RST")

def run_tests():
    subprocess.run(['python', 'tests/test.py'], check=True)

def testwhl():
    clean()
    build_all()
    subprocess.run(['pip', 'uninstall', '-y', 'pytexmk'], check=True)
    whl_files = list(Path('dist').glob('*.whl'))
    if not whl_files:
        raise FileNotFoundError("No .whl files found in dist directory")
    subprocess.run(['pip', 'install', str(whl_files[0])], check=True)
    subprocess.run(['python', 'tests/test.py', '-w'], check=True)
    subprocess.run(['pip', 'uninstall', '-y', 'pytexmk'], check=True)
    clean()
    print("Testwhl completed")

def inswhl():
    clean()
    build_all()
    subprocess.run(['pip', 'uninstall', '-y', 'pytexmk'], check=True)
    whl_files = list(Path('dist').glob('*.whl'))
    if not whl_files:
        raise FileNotFoundError("No .whl files found in dist directory")
    subprocess.run(['pip', 'install', str(whl_files[0])], check=True)
    print("Install pytexmk*.whl Success")

def upload():
    clean()
    build_all()
    dist_files = list(Path('dist').glob('*'))
    if not dist_files:
        raise FileNotFoundError("No files in dist directory")
    subprocess.run(['twine', 'upload'] + [str(f) for f in dist_files], check=True)
    clean()
    print("Upload completed")

def pot():
    locale_dir = Path('src/pytexmk/locale/en')
    modules = ['__main__', 'additional', 'check_version', 'compile', 'config', 'info_print', 'latexdiff', 'logger_config', 'run']
    for module in modules:
        pot_file = locale_dir / f'{module}.pot'
        py_file = Path(f'src/pytexmk/{module}.py')
        subprocess.run(['xgettext', '--output', str(pot_file), str(py_file)], check=True)
    print("Pot files generated")

def mo():
    locale_dir = Path('src/pytexmk/locale/en')
    modules = ['__main__', 'additional', 'check_version', 'compile', 'config', 'info_print', 'latexdiff', 'logger_config', 'run']
    for module in modules:
        pot_file = locale_dir / f'{module}.pot'
        mo_dir = locale_dir / 'LC_MESSAGES'
        mo_dir.mkdir(exist_ok=True, parents=True)
        mo_file = mo_dir / f'{module}.mo'
        subprocess.run(['msgfmt', '-o', str(mo_file), str(pot_file)], check=True)
    print("Mo files generated")

def poup():
    locale_dir = Path('src/pytexmk/locale/en')
    modules = ['__main__', 'additional', 'check_version', 'compile', 'config', 'info_print', 'latexdiff', 'logger_config', 'run']
    for module in modules:
        py_file = Path(f'src/pytexmk/{module}.py')
        temp_pot = locale_dir / f'{module}-temp.pot'
        subprocess.run(['xgettext', '--output', str(temp_pot), str(py_file)], check=True)
    for module in modules:
        temp_pot = locale_dir / f'{module}-temp.pot'
        original_pot = locale_dir / f'{module}.pot'
        subprocess.run(['msgmerge', '--update', str(original_pot), str(temp_pot)], check=True)
    mo()
    for module in modules:
        temp_pot = locale_dir / f'{module}-temp.pot'
        if temp_pot.exists():
            temp_pot.unlink()
    print("Poup completed")

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
        print(f"Usage: {sys.argv[0]} <target>")
        print("Available targets:", ', '.join(targets.keys()))
        sys.exit(1)

    target = sys.argv[1]
    try:
        targets[target]()
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
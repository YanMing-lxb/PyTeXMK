import sys
from pathlib import Path

# -----------------------------------------------------------------------
# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<| 项目配置 |>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# -----------------------------------------------------------------------

PROJECT_NAME = "pytexmk"
ROOT_DIR = Path(__file__).parent.parent  # 设置项目根目录（根据用户选择的代码片段）
SRC_DIR = ROOT_DIR / "src" / "pytexmk"
SRCPYD_DIR = ROOT_DIR / "srcpyd"
ENTRY_POINT = SRCPYD_DIR / "__main__.py"
CONFIG_DIR = SRCPYD_DIR / "config"
DATA_DIR = SRCPYD_DIR / "data"
ICON_FILE = DATA_DIR / "logo.ico"
VENV_NAME = ".venv"
LANG_EN_DIR = SRC_DIR / "locale" / "en"
sys.path.append(str(ROOT_DIR))  # 关键路径设置

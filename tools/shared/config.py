import re
import sys
from pathlib import Path

# -----------------------------------------------------------------------
# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<| 项目配置 |>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# -----------------------------------------------------------------------

__team__ = "YanMing"
PROJECT_NAME = "pytexmk"
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
SRC_DIR = ROOT_DIR / "src" / "pytexmk"
TOOLS_DIR = ROOT_DIR / "tools"
SRC_ENTRY_POINT = SRC_DIR / "__main__.py"
SRC_DATA_DIR = SRC_DIR / "data"
SRC_LOCALE_DIR = SRC_DIR / "locale"
ICO_PATH = TOOLS_DIR / "icon.ico"
ICNS_PATH = TOOLS_DIR / "icon.icns"
PNG_PATH = TOOLS_DIR / "icon.png"
LOGO_SOURCE = ROOT_DIR / "imgs" / "pytexmk-logo.png"
BABEL_CFG_PATH = ROOT_DIR / "babel.cfg"
POT_DIR = SRC_LOCALE_DIR / "templates"
if sys.platform == "win32":
    ICON_FILE = ICO_PATH
elif sys.platform == "darwin":
    ICON_FILE = ICNS_PATH
elif sys.platform == "linux":
    ICON_FILE = PNG_PATH


def _read_version():
    version_file = SRC_DIR / "version.py"
    match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', version_file.read_text(encoding="utf-8"))
    if match:
        return match.group(1)
    raise RuntimeError()


__version__ = _read_version()

__all__ = [
    "BABEL_CFG_PATH",
    "ICNS_PATH",
    "ICON_FILE",
    "ICO_PATH",
    "LOGO_SOURCE",
    "PNG_PATH",
    "POT_DIR",
    "PROJECT_NAME",
    "ROOT_DIR",
    "SRC_DATA_DIR",
    "SRC_DIR",
    "SRC_ENTRY_POINT",
    "SRC_LOCALE_DIR",
    "TOOLS_DIR",
    "__team__",
    "__version__",
]

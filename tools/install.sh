#!/usr/bin/env bash
# =============================================================================
# PyTeXMK 安装 / 升级脚本（Linux / macOS）
# -----------------------------------------------------------------------------
# 设计参考 ohmyposh 的 install.sh：一条命令完成平台识别、版本解析、依赖与
# glibc 校验、下载解压、生成启动器软链、PATH 提示；重复执行即为就地升级。
# 输出语言跟随系统 locale（zh* → 中文，其它 → 英文），可用 -l 覆盖。
#
# 用法：
#   curl -fsSL https://raw.githubusercontent.com/YanMing-lxb/PyTeXMK/main/tools/install.sh | bash -s
#   curl -fsSL ... | bash -s -- -d ~/opt/pytexmk -b ~/.local/bin
#   curl -fsSL ... | bash -s -- -v 1.2.8
#   curl -fsSL ... | bash -s -- -l zh    （强制中文输出）
#
# 参数：
#   -d <目录>  程序安装目录（默认 ~/.local/opt/pytexmk）
#   -b <目录>  启动器软链目录（默认 ~/.local/bin；已有安装时沿用原目录）
#   -v <版本>  指定版本号（默认取最新 Release）
#   -m <方式>  安装方式 zip（默认，下载打包二进制）/ uv（源码安装，需已装 uv）
#   -l <语言>  输出语言 zh / en（默认跟随系统 locale）
#   -f         跳过 glibc 版本检查（仅 Linux）
#   -h         显示帮助
# =============================================================================
set -euo pipefail

REPO="YanMing-lxb/PyTeXMK"
PROGRAM="pytexmk"
RELEASES="https://github.com/${REPO}/releases"
RAW_INSTALL_URL="https://raw.githubusercontent.com/${REPO}/main/tools/install.sh"

INSTALL_DIR=""
BIN_DIR=""
VERSION=""
LANG_CODE=""
MODE="zip"
FORCE=0
TMP_DIR=""

usage() {
    case "$LANG_CODE" in
        zh)
            cat <<EOF
PyTeXMK 安装脚本（Linux / macOS）

用法：install.sh [-d <目录>] [-b <目录>] [-v <版本>] [-m zip|uv] [-l zh|en] [-f] [-h]

  -d <目录>  程序安装目录，默认 \$HOME/.local/opt/pytexmk
  -b <目录>  启动器软链目录，默认 \$HOME/.local/bin（已安装则沿用原目录）
  -v <版本>  指定版本号，例如 1.2.8；默认取最新 Release
  -m <方式>  安装方式：zip（默认，下载打包好的二进制）或 uv（需已安装 uv，从 PyPI 源码安装）
  -l <语言>  输出语言 zh（中文）/ en（英文），默认跟随系统语言
  -f         跳过 glibc 版本检查（Linux 二进制要求 glibc ≥ 2.28）
  -h         显示本帮助

示例：
  curl -fsSL ${RAW_INSTALL_URL} | bash -s
  curl -fsSL ${RAW_INSTALL_URL} | bash -s -- -d ~/opt/pytexmk
  curl -fsSL ${RAW_INSTALL_URL} | bash -s -- -m uv
  curl -fsSL ${RAW_INSTALL_URL} | bash -s -- -l en
EOF
            ;;
        *)
            cat <<EOF
PyTeXMK installer for Linux / macOS

Usage: install.sh [-d <dir>] [-b <dir>] [-v <version>] [-m zip|uv] [-l zh|en] [-f] [-h]

  -d <dir>      Install directory for the program, default \$HOME/.local/opt/pytexmk
  -b <dir>      Directory for the launcher symlink, default \$HOME/.local/bin
                (the existing location is reused when PyTeXMK is already installed)
  -v <version>  Pin a version, e.g. 1.2.8; defaults to the latest release
  -m <mode>     Install mode: zip (default, download the packaged binary) or uv
                (install from PyPI, requires uv to be present)
  -l <lang>     Output language: zh (Chinese) or en (English), defaults to the system locale
  -f            Skip the glibc check (the Linux binary needs glibc >= 2.28)
  -h            Show this help

Examples:
  curl -fsSL ${RAW_INSTALL_URL} | bash -s
  curl -fsSL ${RAW_INSTALL_URL} | bash -s -- -d ~/opt/pytexmk
  curl -fsSL ${RAW_INSTALL_URL} | bash -s -- -m uv
  curl -fsSL ${RAW_INSTALL_URL} | bash -s -- -l zh
EOF
            ;;
    esac
}

# ------------------------------------------------------------------------------
# 语言：-l 覆盖 > 系统 locale（中文环境走中文，其余走英文）
# ------------------------------------------------------------------------------
detect_lang() {
    if [ -n "${PYTEXMK_LANG:-}" ]; then
        case "$PYTEXMK_LANG" in
            zh* | ZH*) printf 'zh' ;;
            en* | EN*) printf 'en' ;;
        esac
        return 0
    fi
    _locale="${LC_ALL:-${LC_MESSAGES:-${LANG:-}}}"
    case "$_locale" in
        zh* | *_CN* | *_SG* | *_HK* | *_TW*) printf 'zh' ;;
        *) printf 'en' ;;
    esac
}

load_messages() {
    if [ "$LANG_CODE" = "zh" ]; then
        M_DEPS='缺少依赖 %s，请先安装（如 sudo apt install %s）'
        M_OS='暂不支持该系统：%s，请改用 pip / uv 安装'
        M_ARCH='暂不支持该架构：%s。Linux 仅发布 x64 二进制，请改用：uv tool install pytexmk'
        M_MAC_INTEL='macOS 仅发布 arm64 二进制，Intel Mac 请改用：uv tool install pytexmk（或加 -m uv 重跑本脚本）'
        M_GLIBC='当前 glibc %s 低于二进制要求的 2.28（Ubuntu 20.04+ / Debian 10+ / RHEL 8+ 才满足）。\n请改用：uv tool install pytexmk　　或加 -f 强制安装（但装上的二进制无法启动）'
        M_VERSION='无法解析最新版本号，请用 -v <版本号> 指定（如 -v 1.2.8）'
        M_MODE_INVALID='不支持的安装方式：%s（可选 zip / uv）'
        M_UV_MISSING='未检测到 uv，请先安装：curl -LsSf https://astral.sh/uv/install.sh | sh'
        M_UV_START='通过 uv 安装 PyTeXMK %s'
        M_UV_IGNORE='-m uv 会忽略 -d / -b：启动器由 uv 管理（默认 ~/.local/bin），程序装在 uv 的工具目录里'
        M_EXISTING='检测到已有安装，将在原位置升级'
        M_DIR_INVALID='安装目录不合法：%s'
        M_DIR_NOT_ABS='安装目录必须是绝对路径：%s'
        M_HEADER='PyTeXMK %s (%s)\n  安装目录：%s\n  启动器：  %s'
        M_DOWNLOAD='下载 %s'
        M_UNZIP='解压'
        M_REPLACE='替换旧版本'
        M_LINK='创建启动器软链'
        M_DL_FAIL='下载失败（HTTP %s）：%s\n可能是网络/代理问题，或用 -v 指定已存在的版本'
        M_UNZIP_FAIL='解压失败'
        M_ZIP_BROKEN='压缩包结构异常：缺少 %s/%s'
        M_PATH='%s 不在 PATH 中，请追加到 shell 配置（~/.bashrc 或 ~/.zshrc）：\n   export PATH="%s:$PATH"\n   （重开终端或 source 该文件后生效）'
        M_DONE='安装完成：%s\n   升级：重跑本脚本即可（自动就地替换）\n   卸载：rm -rf %s %s'
        M_UV_DONE='安装完成：通过 uv 安装，启动器位于 %s\n   升级：uv tool upgrade %s\n   卸载：uv tool uninstall %s'
        M_RUN_FAIL='已安装但当前环境无法启动。Linux 二进制要求 glibc ≥ 2.28（Ubuntu 20.04+ / Debian 10+ / RHEL 8+），\n   旧系统请改用：uv tool install pytexmk'
        M_TEX='提示：PyTeXMK 需要系统已安装 LaTeX 发行版（TeX Live / MiKTeX / MacTeX），以及可选的 biber、xindy。'
    else
        M_DEPS='Missing dependency: %s. Install it first (e.g. sudo apt install %s)'
        M_OS='Unsupported operating system: %s. Use pip / uv instead'
        M_ARCH='Unsupported architecture: %s. Linux binaries are x64 only, use: uv tool install pytexmk'
        M_MAC_INTEL='macOS binaries are arm64 only. On Intel Macs use: uv tool install pytexmk (or re-run with -m uv)'
        M_GLIBC='Detected glibc %s, but the binary requires 2.28 or newer (Ubuntu 20.04+ / Debian 10+ / RHEL 8+).\nUse: uv tool install pytexmk    (or pass -f to force the install; the binary will not start)'
        M_VERSION='Cannot resolve the latest version. Pass one explicitly, e.g. -v 1.2.8'
        M_MODE_INVALID='Unsupported install mode: %s (use zip or uv)'
        M_UV_MISSING='uv not found. Install it first: curl -LsSf https://astral.sh/uv/install.sh | sh'
        M_UV_START='Installing PyTeXMK %s with uv'
        M_UV_IGNORE='-m uv ignores -d / -b: the launcher is managed by uv (default ~/.local/bin) and the program lives in the uv tool directory'
        M_EXISTING='Existing installation detected, upgrading in place'
        M_DIR_INVALID='Invalid install directory: %s'
        M_DIR_NOT_ABS='Install directory must be an absolute path: %s'
        M_HEADER='PyTeXMK %s (%s)\n  install dir: %s\n  launcher:    %s'
        M_DOWNLOAD='Downloading %s'
        M_UNZIP='Extracting'
        M_REPLACE='Replacing the previous version'
        M_LINK='Creating the launcher symlink'
        M_DL_FAIL='Download failed (HTTP %s): %s\nCheck your network or proxy, or pass -v with an existing version'
        M_UNZIP_FAIL='Extraction failed'
        M_ZIP_BROKEN='Unexpected archive layout: missing %s/%s'
        M_PATH='%s is not on your PATH. Add it to your shell profile (~/.bashrc or ~/.zshrc):\n   export PATH="%s:$PATH"\n   (open a new terminal or source the file afterwards)'
        M_DONE='Installation complete: %s\n   upgrade:   re-run this script (in-place)\n   uninstall: rm -rf %s %s'
        M_RUN_FAIL='Installed, but it cannot start in this environment. The Linux binary needs glibc >= 2.38 (Ubuntu 24.04+ / Debian 13+);\n   on older systems use: uv tool install pytexmk'
        M_TEX='Note: PyTeXMK requires a LaTeX distribution (TeX Live / MiKTeX / MacTeX), plus optional biber and xindy.'
    fi
}

info_msg() {
    _fmt="$1"
    shift
    printf 'ℹ️  %b\n' "$(printf -- "$_fmt" "$@")"
}
step_msg() {
    _fmt="$1"
    shift
    printf '• %b\n' "$(printf -- "$_fmt" "$@")"
}
warn_msg() {
    _fmt="$1"
    shift
    printf '⚠️  %b\n' "$(printf -- "$_fmt" "$@")"
}
die_msg() {
    _fmt="$1"
    shift
    printf '❌ %b\n' "$(printf -- "$_fmt" "$@")" >&2
    exit 1
}

cleanup() {
    if [ -n "$TMP_DIR" ] && [ -d "$TMP_DIR" ]; then
        rm -rf "$TMP_DIR"
    fi
}
trap cleanup EXIT

expand_dir() {
    case "$1" in
        "~") printf '%s' "$HOME" ;;
        "~/"*) printf '%s/%s' "$HOME" "${1#~/}" ;;
        *) printf '%s' "$1" ;;
    esac
}

resolve_link() {
    _path="$1"
    _target=""
    while [ -L "$_path" ]; do
        _target="$(readlink "$_path")"
        case "$_target" in
            /*) _path="$_target" ;;
            *) _path="$(dirname "$_path")/$_target" ;;
        esac
    done
    printf '%s' "$_path"
}

while getopts ":d:b:v:m:l:fh" opt; do
    case "$opt" in
        d) INSTALL_DIR="$OPTARG" ;;
        b) BIN_DIR="$OPTARG" ;;
        v) VERSION="$OPTARG" ;;
        m)
            case "$OPTARG" in
                zip | ZIP) MODE="zip" ;;
                uv | UV) MODE="uv" ;;
                *)
                    LANG_CODE="${LANG_CODE:-$(detect_lang)}"
                    load_messages
                    die_msg "$M_MODE_INVALID" "$OPTARG"
                    ;;
            esac
            ;;
        l)
            case "$OPTARG" in
                zh* | ZH*) LANG_CODE="zh" ;;
                en* | EN*) LANG_CODE="en" ;;
                *)
                    LANG_CODE="en"
                    printf 'Unsupported language: %s (use zh or en)\n' "$OPTARG" >&2
                    exit 1
                    ;;
            esac
            ;;
        f) FORCE=1 ;;
        h)
            [ -z "$LANG_CODE" ] && LANG_CODE="$(detect_lang)"
            load_messages
            usage
            exit 0
            ;;
        *)
            [ -z "$LANG_CODE" ] && LANG_CODE="$(detect_lang)"
            load_messages
            usage
            exit 1
            ;;
    esac
done

[ -z "$LANG_CODE" ] && LANG_CODE="$(detect_lang)"
load_messages

# ------------------------------------------------------------------------------
# 1) 依赖与平台
# ------------------------------------------------------------------------------
for tool in curl unzip; do
    command -v "$tool" >/dev/null 2>&1 || die_msg "$M_DEPS" "$tool" "$tool"
done

PLATFORM="$(uname -s 2>/dev/null | tr '[:upper:]' '[:lower:]')"
case "$PLATFORM" in
    linux) PLATFORM="linux" ;;
    darwin) PLATFORM="macos" ;;
    *) die_msg "$M_OS" "$PLATFORM" ;;
esac

ARCH="$(uname -m 2>/dev/null)"
case "$ARCH" in
    x86_64 | amd64) ARCH="x64" ;;
    arm64 | aarch64) ARCH="arm64" ;;
    *) die_msg "$M_ARCH" "$ARCH" ;;
esac

# 二进制资产只有 linux-x64 与 macos-arm64 两种；其余组合走 uv 通道。
if [ "$MODE" = "zip" ]; then
    case "${PLATFORM}:${ARCH}" in
        linux:x64 | macos:arm64) ;;
        macos:x64) die_msg "$M_MAC_INTEL" ;;
        *) die_msg "$M_ARCH" "$ARCH" ;;
    esac
fi

# ------------------------------------------------------------------------------
# 2) 版本号
# ------------------------------------------------------------------------------
if [ -z "$VERSION" ]; then
    VERSION="$(curl -fsSI -o /dev/null -w '%{redirect_url}' "${RELEASES}/latest" 2>/dev/null | sed 's#.*/tag/##; s#v##' || true)"
    if [ -z "$VERSION" ]; then
        # 跳转地址不可用时回落到 GitHub API
        VERSION="$(curl -fsSL "https://api.github.com/repos/${REPO}/releases/latest" 2>/dev/null \
            | sed -n 's/.*"tag_name": *"v\([^"]*\)".*/\1/p' || true)"
    fi
    [ -n "$VERSION" ] || die_msg "$M_VERSION"
fi
VERSION="${VERSION#v}"

# ------------------------------------------------------------------------------
# 2.5) uv 通道：从 PyPI 源码安装，不依赖打包二进制与 glibc
# ------------------------------------------------------------------------------
if [ "$MODE" = "uv" ]; then
    command -v uv >/dev/null 2>&1 || die_msg "$M_UV_MISSING"
    if [ -n "$INSTALL_DIR" ] || [ -n "$BIN_DIR" ]; then
        warn_msg "$M_UV_IGNORE"
    fi
    info_msg "$M_UV_START" "$VERSION"
    uv tool install --force "pytexmk==${VERSION}" >/dev/null || die_msg "$M_RUN_FAIL"
    # 启动器由 uv 管理：用 uv 自己的 bin 目录定位，避免 PATH 上残留的旧安装造成误判。
    UV_BIN_DIR="$(uv tool dir --bin 2>/dev/null || printf '%s' "$HOME/.local/bin")"
    UV_BIN="${UV_BIN_DIR}/${PROGRAM}"
    [ -x "$UV_BIN" ] || UV_BIN="$(command -v "$PROGRAM" 2>/dev/null || printf '%s' "$UV_BIN")"
    "$UV_BIN" --version >/dev/null 2>&1 || die_msg "$M_RUN_FAIL"
    info_msg "$M_UV_DONE" "$UV_BIN" "$PROGRAM" "$PROGRAM"
    info_msg "$M_TEX"
    exit 0
fi

# Linux 二进制在 manylinux_2_28（glibc 2.28）容器中构建，2.28 以下的发行版无法启动。
if [ "$PLATFORM" = "linux" ] && [ "$FORCE" -ne 1 ] && command -v ldd >/dev/null 2>&1; then
    GLIBC="$(ldd --version 2>/dev/null | head -n1 | grep -oE '[0-9]+\.[0-9]+' | tail -n1 || true)"
    if [ -n "$GLIBC" ] && awk -v v="$GLIBC" 'BEGIN { exit (v + 0 < 2.28 ? 0 : 1) }'; then
        die_msg "$M_GLIBC" "$GLIBC"
    fi
fi

# ------------------------------------------------------------------------------
# 3) 安装位置（已有安装则就地升级）
# ------------------------------------------------------------------------------
if [ -z "$INSTALL_DIR" ] && command -v "$PROGRAM" >/dev/null 2>&1; then
    EXISTING="$(command -v "$PROGRAM")"
    REAL="$(resolve_link "$EXISTING")"
    INSTALL_DIR="$(dirname "$REAL")"
    [ -z "$BIN_DIR" ] && BIN_DIR="$(dirname "$EXISTING")"
    info_msg "$M_EXISTING"
fi

[ -z "$INSTALL_DIR" ] && INSTALL_DIR="$HOME/.local/opt/$PROGRAM"
[ -z "$BIN_DIR" ] && BIN_DIR="$HOME/.local/bin"
INSTALL_DIR="$(expand_dir "$INSTALL_DIR")"
BIN_DIR="$(expand_dir "$BIN_DIR")"

case "$INSTALL_DIR" in
    "" | "/" | "$HOME") die_msg "$M_DIR_INVALID" "$INSTALL_DIR" ;;
    /*) ;;
    *) die_msg "$M_DIR_NOT_ABS" "$INSTALL_DIR" ;;
esac

# ------------------------------------------------------------------------------
# 4) 下载并安装
# ------------------------------------------------------------------------------
ZIP_NAME="${PROGRAM}-${VERSION}-${PLATFORM}-${ARCH}.zip"
ZIP_URL="${RELEASES}/download/v${VERSION}/${ZIP_NAME}"

info_msg "$M_HEADER" "$VERSION" "${PLATFORM}-${ARCH}" "$INSTALL_DIR" "${BIN_DIR}/${PROGRAM}"

TMP_DIR="$(mktemp -d 2>/dev/null || mktemp -d -t pytexmk)"

step_msg "$M_DOWNLOAD" "$ZIP_NAME"
HTTP_CODE="$(curl -fsSL --retry 2 -o "${TMP_DIR}/pkg.zip" -w '%{http_code}' "$ZIP_URL" || true)"
if [ "$HTTP_CODE" != "200" ]; then
    die_msg "$M_DL_FAIL" "$HTTP_CODE" "$ZIP_URL"
fi

step_msg "$M_UNZIP"
unzip -oq "${TMP_DIR}/pkg.zip" -d "$TMP_DIR" || die_msg "$M_UNZIP_FAIL"
[ -f "${TMP_DIR}/${PROGRAM}/${PROGRAM}" ] || die_msg "$M_ZIP_BROKEN" "$PROGRAM" "$PROGRAM"

step_msg "$M_REPLACE"
rm -rf "$INSTALL_DIR"
mkdir -p "$(dirname "$INSTALL_DIR")"
mv "${TMP_DIR}/${PROGRAM}" "$INSTALL_DIR"

step_msg "$M_LINK"
mkdir -p "$BIN_DIR"
ln -sfn "${INSTALL_DIR}/${PROGRAM}" "${BIN_DIR}/${PROGRAM}"

# ------------------------------------------------------------------------------
# 5) PATH 检查与自检
# ------------------------------------------------------------------------------
case ":${PATH}:" in
    *":${BIN_DIR}:"*) ;;
    *) warn_msg "$M_PATH" "$BIN_DIR" "$BIN_DIR" ;;
esac

if "${BIN_DIR}/${PROGRAM}" --version >/dev/null 2>&1; then
    info_msg "$M_DONE" "$("${BIN_DIR}/${PROGRAM}" --version 2>/dev/null | head -n1)" "$INSTALL_DIR" "${BIN_DIR}/${PROGRAM}"
else
    warn_msg "$M_RUN_FAIL"
fi

info_msg "$M_TEX"

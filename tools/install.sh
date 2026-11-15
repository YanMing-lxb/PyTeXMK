#!/usr/bin/env bash
# =============================================================================
# PyTeXMK 安装 / 升级脚本（Linux / macOS）
# -----------------------------------------------------------------------------
# 设计参考 ohmyposh 的 install.sh：一条命令完成平台识别、版本解析、依赖与
# glibc 校验、下载解压、生成启动器软链、PATH 提示；重复执行即为就地升级。
#
# 用法：
#   curl -fsSL https://raw.githubusercontent.com/YanMing-lxb/PyTeXMK/main/tools/install.sh | bash -s
#   curl -fsSL ... | bash -s -- -d ~/opt/pytexmk -b ~/.local/bin
#   curl -fsSL ... | bash -s -- -v 1.2.7
#
# 参数：
#   -d <目录>  程序安装目录（默认 ~/.local/opt/pytexmk）
#   -b <目录>  启动器软链目录（默认 ~/.local/bin；已有安装时沿用原目录）
#   -v <版本>  指定版本号（默认取最新 Release）
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
FORCE=0
TMP_DIR=""

info() { printf '%s\n' "$*"; }
warn() { printf '⚠️  %s\n' "$*"; }
step() { printf '• %s\n' "$*"; }
die() { printf '❌ %s\n' "$*" >&2; exit 1; }

cleanup() {
    if [ -n "$TMP_DIR" ] && [ -d "$TMP_DIR" ]; then
        rm -rf "$TMP_DIR"
    fi
}
trap cleanup EXIT

usage() {
    cat <<EOF
PyTeXMK 安装脚本（Linux / macOS）

用法：install.sh [-d <目录>] [-b <目录>] [-v <版本>] [-f] [-h]

  -d <目录>  程序安装目录，默认 \$HOME/.local/opt/pytexmk
  -b <目录>  启动器软链目录，默认 \$HOME/.local/bin（已安装则沿用原目录）
  -v <版本>  指定版本号，例如 1.2.7；默认取最新 Release
  -f         跳过 glibc 版本检查（Linux 二进制要求 glibc ≥ 2.38）
  -h         显示本帮助

示例：
  curl -fsSL ${RAW_INSTALL_URL} | bash -s
  curl -fsSL ${RAW_INSTALL_URL} | bash -s -- -d ~/opt/pytexmk
  curl -fsSL ${RAW_INSTALL_URL} | bash -s -- -v 1.2.7
EOF
}

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

while getopts ":d:b:v:fh" opt; do
    case "$opt" in
        d) INSTALL_DIR="$OPTARG" ;;
        b) BIN_DIR="$OPTARG" ;;
        v) VERSION="$OPTARG" ;;
        f) FORCE=1 ;;
        h)
            usage
            exit 0
            ;;
        *)
            usage
            exit 1
            ;;
    esac
done

# ------------------------------------------------------------------------------
# 1) 依赖与平台
# ------------------------------------------------------------------------------
for tool in curl unzip; do
    command -v "$tool" >/dev/null 2>&1 || die "缺少依赖 ${tool}，请先安装（如 sudo apt install ${tool}）"
done

PLATFORM="$(uname -s 2>/dev/null | tr '[:upper:]' '[:lower:]')"
case "$PLATFORM" in
    linux) PLATFORM="linux" ;;
    darwin) PLATFORM="macos" ;;
    *) die "暂不支持该系统：${PLATFORM}，请改用 pip / uv 安装" ;;
esac

ARCH="$(uname -m 2>/dev/null)"
case "$ARCH" in
    x86_64 | amd64) ARCH="x64" ;;
    *)
        die "暂不支持该架构：${ARCH}。PyTeXMK 目前只发布 x64 二进制，请改用：uv tool install pytexmk"
        ;;
esac

# Linux 二进制在 Ubuntu 24.04（glibc 2.39）上构建，2.38 以下的发行版无法启动。
if [ "$PLATFORM" = "linux" ] && [ "$FORCE" -ne 1 ] && command -v ldd >/dev/null 2>&1; then
    GLIBC="$(ldd --version 2>/dev/null | head -n1 | grep -oE '[0-9]+\.[0-9]+' | tail -n1 || true)"
    if [ -n "$GLIBC" ] && awk -v v="$GLIBC" 'BEGIN { exit (v + 0 < 2.38 ? 0 : 1) }'; then
        die "当前 glibc ${GLIBC} 低于二进制要求的 2.38（Ubuntu 24.04+ / Debian 13+ 才满足）。
请改用：uv tool install pytexmk　　或加 -f 强制安装（但装上的二进制无法启动）"
    fi
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
    [ -n "$VERSION" ] || die "无法解析最新版本号，请用 -v <版本号> 指定（如 -v 1.2.7）"
fi
VERSION="${VERSION#v}"

# ------------------------------------------------------------------------------
# 3) 安装位置（已有安装则就地升级）
# ------------------------------------------------------------------------------
if [ -z "$INSTALL_DIR" ] && command -v "$PROGRAM" >/dev/null 2>&1; then
    EXISTING="$(command -v "$PROGRAM")"
    REAL="$(resolve_link "$EXISTING")"
    INSTALL_DIR="$(dirname "$REAL")"
    [ -z "$BIN_DIR" ] && BIN_DIR="$(dirname "$EXISTING")"
    info "ℹ️  检测到已有安装，将在原位置升级"
fi

[ -z "$INSTALL_DIR" ] && INSTALL_DIR="$HOME/.local/opt/$PROGRAM"
[ -z "$BIN_DIR" ] && BIN_DIR="$HOME/.local/bin"
INSTALL_DIR="$(expand_dir "$INSTALL_DIR")"
BIN_DIR="$(expand_dir "$BIN_DIR")"

case "$INSTALL_DIR" in
    "" | "/" | "$HOME") die "安装目录不合法：${INSTALL_DIR}" ;;
    /*) ;;
    *) die "安装目录必须是绝对路径：${INSTALL_DIR}" ;;
esac

# ------------------------------------------------------------------------------
# 4) 下载并安装
# ------------------------------------------------------------------------------
ZIP_NAME="${PROGRAM}-${VERSION}-${PLATFORM}-${ARCH}.zip"
ZIP_URL="${RELEASES}/download/v${VERSION}/${ZIP_NAME}"

info "ℹ️  PyTeXMK ${VERSION} (${PLATFORM}-${ARCH})"
info "  安装目录：${INSTALL_DIR}"
info "  启动器：  ${BIN_DIR}/${PROGRAM}"

TMP_DIR="$(mktemp -d 2>/dev/null || mktemp -d -t pytexmk)"

step "下载 ${ZIP_NAME}"
HTTP_CODE="$(curl -fsSL --retry 2 -o "${TMP_DIR}/pkg.zip" -w '%{http_code}' "$ZIP_URL" || true)"
if [ "$HTTP_CODE" != "200" ]; then
    die "下载失败（HTTP ${HTTP_CODE}）：${ZIP_URL}
可能是网络/代理问题，或用 -v 指定已存在的版本"
fi

step "解压"
unzip -oq "${TMP_DIR}/pkg.zip" -d "$TMP_DIR" || die "解压失败"
[ -f "${TMP_DIR}/${PROGRAM}/${PROGRAM}" ] || die "压缩包结构异常：缺少 ${PROGRAM}/${PROGRAM}"

step "替换旧版本"
rm -rf "$INSTALL_DIR"
mkdir -p "$(dirname "$INSTALL_DIR")"
mv "${TMP_DIR}/${PROGRAM}" "$INSTALL_DIR"

step "创建启动器软链"
mkdir -p "$BIN_DIR"
ln -sfn "${INSTALL_DIR}/${PROGRAM}" "${BIN_DIR}/${PROGRAM}"

# ------------------------------------------------------------------------------
# 5) PATH 检查与自检
# ------------------------------------------------------------------------------
case ":${PATH}:" in
    *":${BIN_DIR}:"*) ;;
    *)
        warn "${BIN_DIR} 不在 PATH 中，请追加到 shell 配置（~/.bashrc 或 ~/.zshrc）：
   export PATH=\"${BIN_DIR}:\$PATH\"
   （重开终端或 source 该文件后生效）"
        ;;
esac

if "${BIN_DIR}/${PROGRAM}" --version >/dev/null 2>&1; then
    info "✅ 安装完成：$("${BIN_DIR}/${PROGRAM}" --version 2>/dev/null | head -n1)"
    info "   升级：重跑本脚本即可（自动就地替换）
   卸载：rm -rf ${INSTALL_DIR} ${BIN_DIR}/${PROGRAM}"
else
    warn "已安装但当前环境无法启动。Linux 二进制要求 glibc ≥ 2.38（Ubuntu 24.04+ / Debian 13+），
   旧系统请改用：uv tool install pytexmk"
fi

info "提示：PyTeXMK 需要系统已安装 LaTeX 发行版（TeX Live / MacTeX）与可选的 biber、xindy、latexdiff。"

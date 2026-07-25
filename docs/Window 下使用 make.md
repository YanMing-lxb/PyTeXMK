# Windows 下使用 make

本文档介绍如何在 Windows 系统中配置和使用 `make` 命令。

## 前提条件

在 Windows 中使用 `make` 需要 MinGW-w64 环境。MinGW-w64 通常不会单独发布，而是随其他软件一起安装，例如 [Strawberry Perl](https://strawberryperl.com/)。

## 检查是否已安装

在 CMD 或 PowerShell 终端中运行以下命令，检查系统中是否存在 MinGW-w64：

```cmd
where mingw32-make.exe
```

如果已安装，会输出类似以下的路径：

```cmd
C:\Applications\Strawberry\c\bin\mingw32-make.exe
```

## 配置 make 命令

为了方便使用 `make` 命令（而不是 `mingw32-make`），可以将 `mingw32-make.exe` 复制一份并重命名为 `make.exe`：

1. 找到 `mingw32-make.exe` 所在目录（如上例中的 `C:\Applications\Strawberry\c\bin\`）
2. 复制 `mingw32-make.exe`
3. 将副本重命名为 `make.exe`

完成后，在终端中输入 `make` 即可使用。

## 验证

```cmd
make --version
```

如果输出版本信息，则配置成功。

## 其他方案

- **Chocolatey**：`choco install make`
- **Scoop**：`scoop install make`
- **Git Bash**：Git for Windows 自带的 MSYS2 环境中包含 make
- **WSL**：在 Windows Subsystem for Linux 中使用原生 make

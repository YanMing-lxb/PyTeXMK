# Winget 发布开发者文档

本文档记录 PyTeXMK 向 [microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs) 仓库发布 winget 清单的完整流程、权限配置、审核说明与常见问题排查。

---

## 主题 1：WINGET_GITHUB_TOKEN 申请步骤与权限范围

自动化提 PR 流程（`.github/workflows/Release.yml` 中 `publish-to-winget` job）需要一个具有 GitHub 公开仓库读写权限的 Personal Access Token (PAT)，通过仓库 Secret `WINGET_GITHUB_TOKEN` 注入。

### 申请步骤

1. **登录 GitHub** → 点击右上角头像 → **Settings**
2. 左侧菜单底部 → **Developer settings**
3. 选择 **Personal access tokens** → 推荐使用 **Fine-grained tokens**（细粒度，权限更受控），或 **Tokens (classic)**（经典，配置更简单）

#### 选项 A：Classic Token（推荐，最简单）

1. 点击 **Generate new token (classic)**
2. **Note** 填：`PyTeXMK winget-pkgs publish CI`（或任意能识别用途的名称）
3. **Expiration** 建议选择 **90 days**（到期前循环重新生成并更新 Secret）
4. **Select scopes** 仅勾选：
   - ✅ `public_repo`（属于 `repo` 大类下的子项）
   
   > winget-pkgs 是公开仓库，自动化流程仅需要：fork 仓库权限 + 在 fork 中创建分支 + 提交 commit + 向上游提 PR 的权限，`public_repo` 恰好覆盖这一范围，无需更广泛的 `repo` 全权限。
5. 点击 **Generate token**
6. **立即复制生成的 token**（离开页面后不可再次查看，若丢失需重新生成）

#### 选项 B：Fine-grained Token（权限最小化）

1. 点击 **Generate new token**（Fine-grained）
2. **Token name** 同上
3. **Expiration** 建议 90 天
4. **Repository access** 选择 **Only select repositories** → 添加 `microsoft/winget-pkgs`（如果无法直接选上游，也可选 **Public Repositories (read-only)**，然后在 Permissions 中单独配置，通常 classic 更省事）
5. **Permissions → Repository permissions**：
   - **Contents**：Read and write（需要提交 commit 写入 fork 的分支）
   - **Pull requests**：Read and write（需要创建 PR、读取 PR 状态）
   - **Metadata**：Read-only（默认必填）
6. 生成并复制 token

### 配置到仓库 Secret

1. 进入 **PyTeXMK 仓库主页** → **Settings**
2. 左侧 → **Secrets and variables** → **Actions**
3. 点击 **New repository secret**
4. **Name** 填：`WINGET_GITHUB_TOKEN`
5. **Secret** 粘贴刚才复制的 token 值
6. 点击 **Add secret**

### 安全提示

- **🔴 绝对不要** 在任何 Issue 评论、PR 描述、截图、CI 日志、本地调试脚本中粘贴该 token 的明文值（即使是 "测试用临时 token" 也不行）
- GitHub 会自动扫描公网内容中的 PAT，一旦检测到泄漏会立即 revoke 并邮件通知，但仍应主动防范
- 若**怀疑泄漏**：立即进入 Developer settings → 对应 token 点击 **Revoke** → 重新生成 → 更新仓库 Secret
- 日志安全：`tools/winget/publish.py` 中所有子进程日志统一经过 `_sanitize_log()` 正则清洗，会把 `ghp_` / `github_pat_` / URL query 中的 token 段替换为 `<REDACTED>`，token 从环境变量 `WINGET_CREATE_GITHUB_TOKEN` 读取，不走命令行参数（wingetcreate 同样从该环境变量读取，不会出现在 argv 中）

---

## 主题 2：首次提交人工审核说明

当 Package Identifier（`YanMing-lxb.PyTeXMK`）在 winget-pkgs 仓库中**首次出现**时，机器人会自动打上 `Needs: Review` 类标签，需要 winget-pkgs 社区维护者**人工审核**，通常耗时 **1-7 天**。

### 强烈建议首次手动提交

首次提交流程涉及较多人机交互（机器人打标签、要求回复、可能需要补充信息），**强烈建议手动提交而非依赖自动化工作流**，便于第一时间响应审核反馈：

#### 手动提交步骤

**Step 1：使用官方 wingetcreate 生成清单并提交**

发布已统一到官方 `wingetcreate` 一条命令（`winget create` 或 `winget update`），清单由 wingetcreate 自动生成，仅维护 en-US 单语言，不再依赖手写模板。

```bash
# 确保已发布 GitHub Release 并带上 v 前缀 tag 后执行
WINGET_CREATE_GITHUB_TOKEN=<你的PAT> uv run python tools/winget/publish.py \
  --version 1.3.0 \
  --release-tag v1.3.0
```

`publish.py` 会调用 `wingetcreate update ... -u <installer-url> -v <version> --submit --no-open` 生成清单并直接提交 PR 到 `microsoft/winget-pkgs`；若包尚不存在，则回退执行 `wingetcreate new`。

installer URL 严格为：
```
https://github.com/YanMing-lxb/PyTeXMK/releases/download/v1.3.0/pytexmk-1.3.0-windows-x64.zip
```

**本工具不支持本地 zip 渲染清单**：清单内容由 wingetcreate 依据 Release 资产自动生成（含 SHA256、InstallerType 等）。

**如需补充 zh-CN 中文本地化**，需人工追加一条 wingetcreate 命令（默认清单仅 en-US 单语言）：
```bash
wingetcreate update-locale YanMing-lxb.PyTeXMK -l zh-CN
```

**Step 2：本地 winget validate 校验（可选）**

发布脚本会直接提交 PR，由 winget-pkgs 的 Azure-Pipelines 自动校验；若想在本地预检，可先在本地目录生成清单后单独校验：

```powershell
# 安装 winget（Windows 10 1809+ / Windows 11 默认自带）
winget --version

# 校验清单（指向版本目录，不是单个文件）
winget validate "build/winget/manifests/y/YanMing-lxb/PyTeXMK/1.3.0"
```

预期输出：`Manifest validation succeeded.` 若失败请参考「主题 3」排查。

**Step 3：Fork + 分支 + 提交 PR（手动兜底）**

虽然已改用 wingetcreate 自动提 PR，若仍需完全手动提交，可参考以下步骤：

1. 浏览器访问 [microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs) → 右上角 **Fork** 到自己账号
2. 克隆 fork 到本地：`git clone https://github.com/<你的用户名>/winget-pkgs.git`
3. 新建分支：`git checkout -b pytexmk-1.3.0`
4. 将 wingetcreate 生成（或手动编写）的 YAML 复制到 fork 的对应路径：
   ```
   winget-pkgs/manifests/y/YanMing-lxb/PyTeXMK/1.3.0/
   ```
   （首次提交需逐层新建 `y/` / `YanMing-lxb/` / `PyTeXMK/` / `1.3.0/` 目录）
5. commit + push：
   ```bash
   git add manifests/y/YanMing-lxb/PyTeXMK/1.3.0/
   git commit -m "New package: YanMing-lxb.PyTeXMK version 1.3.0"
   git push origin pytexmk-1.3.0
   ```
6. 浏览器打开 fork 仓库 → 点击 **Compare & pull request** → 提 PR 到上游 `microsoft/winget-pkgs:master`
7. PR 标题建议：`New package: YanMing-lxb.PyTeXMK v1.3.0`

### 机器人可能打的标签与应对

首次 PR 期间 winget-pkgs 机器人会根据验证结果打标签，**每个标签都需要对应处理**：

| 标签前缀 | 含义 | 常见应对 |
| --- | --- | --- |
| `Validation-*` | 自动化验证未通过（如 SHA256 不匹配、格式错误） | 按机器人评论中的具体报错修改清单，force-push 到同一分支 |
| `Needs:*` | 维护者要求补充信息（如 `Needs: Author Feedback` 要求回复、`Needs: Internal Review` 等待内部团队核验） | 在 PR 评论区回复对应要求；若要求修改则 commit 更新 |
| `Blocking-Issue` | 清单存在严重问题阻断合并（如 URL 404、InstallerType 非法） | 按评论指出的问题点修复后 force-push，然后回复机器人 re-trigger 验证 |

> 提示：首次通过后，后续版本更新的 PR 机器人会自动验证（`Azure-Pipelines` 校验通过），通常无需人工审核即可自动合并。

---

## 主题 3：清单验证失败常见排查思路

`winget validate` 或 winget-pkgs PR 的自动化流水线报错时，按以下清单逐项排查：

### 1. SHA256 不匹配

**报错特征**：`InstallerSha256 mismatch` / `Hash validation failed`

**排查步骤**：
- 重新从 **GitHub Release 页面**手动下载 zip 资产（不要用本地 build 的 zip）
- 本地计算哈希校验：
  ```powershell
  Get-FileHash "pytexmk-1.3.0-windows-x64.zip" -Algorithm SHA256 | Select-Object Hash
  ```
- 对比 `YanMing-lxb.PyTeXMK.installer.yaml` 中 `InstallerSha256` 字段
- **根因 A**：执行 `publish.py`（wingetcreate）时 GitHub Release 资产尚未上传完成 → Release workflow 中 `needs: [publish-to-github-release]` 已保证时序，本地手动执行时请等待 Release 页面 Assets 列表加载稳定后再执行
- **根因 B**：Release 资产被覆盖重新上传 → 重新发布

### 2. RelativeFilePath 错误

**报错特征**：`Relative file path does not exist within the archive` / `NestedInstallerFiles[0].RelativeFilePath invalid`

**排查步骤**：
- 用解压工具或命令行检查 zip 包的目录结构：
  ```powershell
  tar -tf pytexmk-1.3.0-windows-x64.zip
  ```
- 预期顶层目录为 `pytexmk/`，内部存在 `pytexmk.exe`，即完整路径为 `pytexmk/pytexmk.exe`
- 检查 wingetcreate 生成的清单中 `RelativeFilePath: pytexmk/pytexmk.exe` 是否与实际 zip 结构一致
- 若 `zip_release.py` 的 staging 目录结构有变更（如去掉顶层目录或改名为 `PyTeXMK`），需同步调整 Release 资产或提交时的清单

### 3. NestedInstallerType=portable 不支持 scope=machine

**报错特征**：`NestedInstallerType portable does not support machine scope` / `Scope machine not allowed`

**说明**：winget 中 `NestedInstallerType: portable`（便携版，解包即可用）**仅支持 user 级安装**，不支持 machine 级（所有用户）。

**处理方式**：
- 当前 manifest 默认仅声明 `Scope: user`，不会触发此报错
- 若未来要支持机器级安装，有两条路径：
  - (a) 改用 MSI / Inno Setup / NSIS 打包 EXE，将 `InstallerType` 改为 `msi` / `exe` 并配置 `InstallerSwitches`
  - (b) 在 manifest 中显式声明仅支持 user：保持 `Scope: user` 不变，并在 `InstallModes` 中不包含 `machine`

### 4. winget validate 返回 Unknown error

**报错特征**：`Manifest validation failed: Unknown error` / 错误信息不含具体字段名

**排查步骤**：
- 检查 winget 客户端版本：`winget --version`，建议 ≥ `v1.6.x`
- 检查 manifest schema 版本：清单顶层的 `PackageIdentifier` 下方应有 `ManifestVersion: 1.6.0`（与 wingetcreate 生成的一致）
- 用较新版本的 winget 客户端校验：前往 [winget-cli Releases](https://github.com/microsoft/winget-cli/releases) 升级 App Installer
- 或使用 winget-pkgs 官方验证工具：在 [winget-pkgs PR 验证页面](https://github.com/microsoft/winget-pkgs/blob/master/doc/tools.md) 用 `SandboxTest` 环境复现

### 5. PR 创建失败 403 Forbidden

**报错特征**：wingetcreate 提交时抛错 `403 Forbidden` / `Resource not accessible by integration` / `Bad credentials`

**排查步骤**：
- 进入仓库 **Settings → Secrets and variables → Actions**，确认 `WINGET_GITHUB_TOKEN` Secret 存在
- 确认对应 PAT **未过期**：Developer settings 中查看 Expiration
- （Classic Token）确认已勾选 `public_repo` 权限：仅有 `read:user` 等会 fork 失败
- （Fine-grained Token）确认 Repository Permissions 中 `Contents` 与 `Pull requests` 均为 Read and write
- 可通过 `gh api` 本地快速验证 token 权限：
  ```bash
  set WINGET_GITHUB_TOKEN=<值>
  gh api repos/microsoft/winget-pkgs --header "Authorization: Bearer %WINGET_GITHUB_TOKEN%"
  ```
  返回仓库元数据 = 权限正常；401/403 = token 有问题

### 6. 安装后命令找不到（pytexmk 未加入 PATH）

**用户端现象**：winget install 成功后，执行 `pytexmk` 提示 "不是内部或外部命令"

**排查步骤**：
- 检查 manifest 中 `PortableCommandAlias`：应为 `pytexmk`（与 Installer 的嵌套 portable 对应）
- 检查是否为 PATH 未刷新：winget 安装完成后，**新开一个终端**再运行（当前已打开的终端会话不会自动刷新 PATH 环境变量）
- 检查实际安装位置：默认在 `%LOCALAPPDATA%\Microsoft\WinGet\Packages\YanMing-lxb.PyTeXMK_Microsoft.Winget.Source_8wekyb3d8bbwe\`，确认其中 `pytexmk\pytexmk.exe` 存在且存在指向它的 shim

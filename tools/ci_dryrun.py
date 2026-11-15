"""触发 GitHub Actions 的 Release 工作流做一次 dry_run（只构建、不发布）。

用途：打 tag 之前先验证打包链路是否还通——Linux 走 manylinux_2_28 容器、
macOS 产 arm64、glibc 水位门禁、子进程环境探针、Windows zip 与 winget 安装源。
dry_run 模式下工作流只构建和上传 artifact，不会往 PyPI / GitHub Release 推任何东西。

为什么是独立脚本且只用标准库：
    make 里其它 python 目标走 `uv run`（项目虚拟环境），但同一个仓库被 Windows
    与 WSL 交替使用时会互相重建 `.venv`，Windows 侧常因 `.venv/lib64` 报警失败。
    这个命令本质上只是一次 HTTP 调用 + 轮询，没有任何三方依赖，因此
    写成纯标准库脚本 + `uv run --no-project`，两边都稳定可跑。

用法：
    python tools/ci_dryrun.py                 触发并跟踪到结束（失败时退出码 1）
    python tools/ci_dryrun.py --check         只校验 token 与目标，不真的触发
    python tools/ci_dryrun.py --no-watch      触发后立即返回，只打印运行地址
    python tools/ci_dryrun.py --ref <分支>    指定分支（默认当前分支）

需要 token：环境变量 GH_TOKEN 或 GITHUB_TOKEN，或者已登录的 gh CLI。
token 需要 actions:write（经典 token 勾选 workflow 即可）。
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime

GITHUB_API = "https://api.github.com"
FALLBACK_SLUG = "YanMing-lxb/PyTeXMK"


def git(*args, default=""):
    """执行 git 命令并返回 stdout；失败时返回 default，不抛异常。"""
    try:
        result = subprocess.run(["git", *args], capture_output=True, text=True, check=False)
    except OSError:
        return default
    return result.stdout.strip() if result.returncode == 0 else default


def repo_slug():
    """从 origin 远程地址解析 owner/repo，解析不出时回落到常量。"""
    url = git("remote", "get-url", "origin")
    match = re.search(r"github\.com[:/]+(.+?)(?:\.git)?$", url)
    return match.group(1) if match else FALLBACK_SLUG


def resolve_token():
    """取 token：环境变量优先，其次是已登录的 gh CLI。"""
    for name in ("GH_TOKEN", "GITHUB_TOKEN"):
        value = os.environ.get(name, "").strip()
        if value:
            return value
    try:
        result = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=False)
    except OSError:
        result = None
    if result is not None and result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()
    raise SystemExit(
        "未找到 GitHub token：请设置 GH_TOKEN（或 GITHUB_TOKEN），或先执行 gh auth login。\n"
        "token 需要 actions:write 权限（经典 token 勾选 workflow 即可）。"
    )


def api(method, path, token, payload=None):
    """调用 GitHub REST API；token 只放在请求头，不会写进日志。"""
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(GITHUB_API + path, data=data, method=method)
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("Authorization", f"Bearer {token}")
    request.add_header("X-GitHub-Api-Version", "2022-11-28")
    if data is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read()
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:300]
        raise SystemExit(f"GitHub API 调用失败 {e.code}：{detail}") from e
    except urllib.error.URLError as e:
        raise SystemExit(f"无法访问 GitHub API：{e.reason}") from e


def parse_ts(value):
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


def wait_for_run(slug, workflow, ref, token, since, attempts=20, interval=3):
    """等刚触发的那次 workflow_dispatch 出现在 runs 列表里。"""
    path = f"/repos/{slug}/actions/workflows/{workflow}/runs?event=workflow_dispatch&branch={ref}&per_page=10"
    for _ in range(attempts):
        for run in api("GET", path, token).get("workflow_runs", []):
            if parse_ts(run["created_at"]) >= since:
                return run
        time.sleep(interval)
    raise SystemExit("触发成功但 60s 内没在 runs 列表里看到本次运行，请到 Actions 页面确认")


def report_jobs(slug, run_id, token):
    """打印各 job 结论，有失败返回 False。"""
    jobs = api("GET", f"/repos/{slug}/actions/runs/{run_id}/jobs?per_page=50", token).get("jobs", [])
    ok = True
    for job in jobs:
        conclusion = job.get("conclusion") or "?"
        mark = "[OK]" if conclusion == "success" else ("[--]" if conclusion == "skipped" else "[!!]")
        print(f"  {mark} {job.get('name')} -> {conclusion}")
        if conclusion not in {"success", "skipped"}:
            ok = False
    return ok


def main():
    parser = argparse.ArgumentParser(description="触发 Release 工作流的 dry_run（只构建不发布）")
    parser.add_argument("--workflow", default="Release.yml", help="工作流文件名（默认 Release.yml）")
    parser.add_argument("--ref", default="", help="分支名（默认当前分支）")
    parser.add_argument("--check", action="store_true", help="只校验 token 与目标，不触发")
    parser.add_argument("--no-watch", action="store_true", help="触发后立即返回，不跟踪结果")
    parser.add_argument("--interval", type=int, default=20, help="跟踪时的轮询间隔秒数（默认 20）")
    args = parser.parse_args()

    ref = args.ref or git("rev-parse", "--abbrev-ref", "HEAD") or "main"
    slug = repo_slug()

    if args.check:
        resolve_token()
        print(f"[OK] 前置检查通过：将触发 {slug} 的 {args.workflow}（ref={ref}，dry_run=true）")
        return 0

    token = resolve_token()

    # workflow_dispatch 跑的是远端代码，本地未推送的改动不会生效
    local = git("rev-parse", "HEAD")
    remote = git("rev-parse", f"origin/{ref}")
    if not remote:
        print(f"[!] 没有 origin/{ref}：请确认分支已推送到远端")
    elif local and local != remote:
        print(f"[!] 本地 {ref} 与 origin/{ref} 不一致：CI 跑的是远端代码，请先 push")

    since = datetime.now(UTC).replace(microsecond=0)
    print(f"[>] 触发 {slug} 的 {args.workflow}（ref={ref}，dry_run=true，只构建不发布）")
    api("POST", f"/repos/{slug}/actions/workflows/{args.workflow}/dispatches", token, {"ref": ref, "inputs": {"dry_run": "true"}})

    run = wait_for_run(slug, args.workflow, ref, token, since)
    print(f"运行地址: {run['html_url']}")
    if args.no_watch:
        print("已触发，未跟踪结果（去掉 --no-watch 可自动跟踪）")
        return 0

    print("等待构建结束（Linux 走 manylinux_2_28 容器，通常 5~10 分钟）…")
    while True:
        run = api("GET", f"/repos/{slug}/actions/runs/{run['id']}", token)
        if run["status"] == "completed":
            break
        time.sleep(args.interval)

    print(f"结论: {run['conclusion']}（{run['html_url']}）")
    jobs_ok = report_jobs(slug, run["id"], token)
    return 0 if jobs_ok and run["conclusion"] == "success" else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n已中断（已触发的那次运行不会因此取消）")
        sys.exit(130)

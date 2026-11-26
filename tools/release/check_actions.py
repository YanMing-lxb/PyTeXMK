"""检查 GitHub Actions 引用的 action 版本，可选一键更新到最新 release。

用途：
    扫描 ``.github/workflows`` 与 ``.github/actions`` 下的 workflow / composite
    配置，提取 ``uses: owner/repo@ref`` 引用，对比 GitHub 上该 action 的最新
    release，报告哪些过期；``--apply`` 可把完整 semver 引用直接更新到最新标签。

钉版本策略（与本仓库约定一致）：
    · 发布主版本浮动标签（如 ``v7``）的 action：钉 ``@vN``，自动跟随同主版本的
      补丁/小版本，无需频繁检查；脚本不会改动这类主版本标签。
    · 不发布主版本标签的 action（如 setup-uv、pypa-publish）：钉完整 semver，
      脚本在有新 release 时提示，并可 ``--apply`` 升级。

用法：
    python tools/release/check_actions.py            # 只读检查，输出报告；有过期则退出码 1
    python tools/release/check_actions.py --apply   # 把可升级的 semver 引用改写为最新标签
    python tools/release/check_actions.py --json     # 机器可读输出

只依赖标准库；token 可选（``GH_TOKEN`` / ``GITHUB_TOKEN``），未登录走匿名 API 限流。
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
WORKFLOW_DIR = ROOT_DIR / ".github" / "workflows"
ACTION_DIR = ROOT_DIR / ".github" / "actions"

USES_RE = re.compile(r"^\s*uses:\s*([^\s#]+)")
REF_RE = re.compile(r"^(?P<owner>[^/]+)/(?P<repo>[^@]+)@(?P<ref>.+)$")
SEMVER_RE = re.compile(r"^v?(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)")
MAJOR_TAG_RE = re.compile(r"^v\d+$")


def find_workflow_files():
    """收集 workflow 与 composite action 配置文件。"""
    files = []
    if WORKFLOW_DIR.exists():
        files.extend(sorted(WORKFLOW_DIR.glob("*.yml")))
        files.extend(sorted(WORKFLOW_DIR.glob("*.yaml")))
    if ACTION_DIR.exists():
        files.extend(sorted(ACTION_DIR.glob("*/action.yml")))
        files.extend(sorted(ACTION_DIR.glob("*/action.yaml")))
    return files


def parse_uses(path):
    """提取 ``(slug, ref, 行号, 原文行)``；跳过本地路径与 docker 引用。"""
    refs = []
    lines = path.read_text(encoding="utf-8").splitlines()
    for no, line in enumerate(lines, start=1):
        match = USES_RE.match(line)
        if not match:
            continue
        value = match.group(1)
        if value.startswith("./") or value.startswith("docker://"):
            continue
        ref_match = REF_RE.match(value)
        if not ref_match:
            continue
        slug = f"{ref_match.group('owner')}/{ref_match.group('repo')}"
        refs.append((slug, ref_match.group("ref"), no, line))
    return refs


def api_get(path, token):
    """调用 GitHub REST API；404 返回 None，其它错误直接退出。"""
    request = urllib.request.Request("https://api.github.com" + path)
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("User-Agent", "pytexmk-check-actions")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=30) as resp:
            return json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise SystemExit(f"GitHub API {exc.code}: {path}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"无法访问 GitHub API：{exc.reason}") from exc


def latest_tag(slug, token):
    """优先取最新 release 标签；没有 release 时回退到首个 tag。"""
    release = api_get(f"/repos/{slug}/releases/latest", token)
    if release and release.get("tag_name"):
        return release["tag_name"]
    tags = api_get(f"/repos/{slug}/tags?per_page=1", token)
    if tags:
        return tags[0]["name"]
    return None


def semver_tuple(ref):
    match = SEMVER_RE.match(ref)
    if not match:
        return None
    return tuple(int(match.group(k)) for k in ("major", "minor", "patch"))


def classify(current, latest):
    """判定版本状态：up-to-date / outdated / major-tag / unknown。"""
    if latest is None:
        return "unknown", "取不到最新版本"
    if MAJOR_TAG_RE.match(current):
        latest_major = latest.lstrip("v").split(".")[0]
        if latest_major == current.lstrip("v"):
            return "major-tag", "主版本浮动标签，跟随同主版本最新"
        return "outdated", f"主版本落后：{current} → {latest}"
    current_v, latest_v = semver_tuple(current), semver_tuple(latest)
    if current_v is None or latest_v is None:
        return "unknown", "版本号格式无法解析"
    if latest_v > current_v:
        return "outdated", f"{current} → {latest}"
    return "up-to-date", "已是最新"


def collect_references():
    """汇总 slug -> ref -> 引用位置列表。"""
    used = {}
    for file in find_workflow_files():
        for slug, ref, no, _line in parse_uses(file):
            used.setdefault(slug, {}).setdefault(ref, []).append((file, no))
    return used


def main():
    parser = argparse.ArgumentParser(description="检查 GitHub Action 版本并可选更新")
    parser.add_argument("--apply", action="store_true", help="把过期的 semver 引用改写为最新标签")
    parser.add_argument("--json", action="store_true", help="输出 JSON 报告")
    args = parser.parse_args()

    token = next(
        (os.environ.get(name, "").strip() for name in ("GH_TOKEN", "GITHUB_TOKEN") if os.environ.get(name, "").strip()),
        "",
    )

    used = collect_references()
    report = []
    outdated = False
    for slug in sorted(used):
        latest = latest_tag(slug, token)
        for ref in sorted(used[slug]):
            status, note = classify(ref, latest)
            outdated = outdated or status == "outdated"
            report.append(
                {
                    "slug": slug,
                    "ref": ref,
                    "latest": latest,
                    "status": status,
                    "note": note,
                    "uses": [
                        {"file": str(f.relative_to(ROOT_DIR)), "line": no}
                        for f, no in used[slug][ref]
                    ],
                }
            )

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        marks = {"up-to-date": "✓", "major-tag": "↺", "outdated": "✗", "unknown": "?"}
        for item in report:
            print(
                f"{marks[item['status']]} {item['slug']}@{item['ref']}  "
                f"最新: {item['latest'] or '?'}  ({item['note']})"
            )
        n_outdated = sum(item["status"] == "outdated" for item in report)
        print(f"\n共 {len(report)} 个引用，过期 {n_outdated} 个。")

    if args.apply:
        changed = []
        for item in report:
            if item["status"] != "outdated" or MAJOR_TAG_RE.match(item["ref"]):
                continue  # 主版本浮动标签保持不动
            old, new = f"@{item['ref']}", f"@{item['latest']}"
            for loc in item["uses"]:
                path = ROOT_DIR / loc["file"]
                text = path.read_text(encoding="utf-8")
                text = text.replace(f"uses: {item['slug']}{old}", f"uses: {item['slug']}{new}")
                path.write_text(text, encoding="utf-8")
                changed.append(f"{loc['file']}: {item['slug']}{old} → {new}")
        if changed:
            print("\n已更新：")
            for entry in changed:
                print("  " + entry)

    sys.exit(1 if outdated and not args.apply else 0)


if __name__ == "__main__":
    main()

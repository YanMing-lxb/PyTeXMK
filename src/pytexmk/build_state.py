"""构建状态持久化：跨进程复用的产物基线、源快照与收敛标记。

为什么需要
----------
收敛判定原本完全依赖**进程内快照**（``prepare_aux_out_snapshots()`` 读到的
上一轮内容只活在内存里）。一旦用户 Ctrl+C 中断、换台机器、或从 git 拉下新
代码，重启后的"第 1 轮"就没有任何基线可比，只能靠多编译一轮重新观察——
这正是"确认轮"无法省略的根因之一。

本模块把基线落到**共享状态文件** ``<auxdir>/.pytexmk_refcache.json`` 的
``pytexmk.build`` 命名空间里。文件本身由 ``pytexlogs.ProjectStateStore``
统一读写，PyTeXMK 不自己碰 JSON，因此不会和``pytexlogs.refs``互相覆盖。

不新增任何辅助文件：复用 pytexlogs 已经在写的那个文件。
"""

import hashlib
import logging
from collections.abc import Iterable
from pathlib import Path
from typing import Any, NamedTuple

from pytexlogs import ProjectStateStore

from .language import set_language

_ = set_language("build_state")
logger = logging.getLogger(__name__)

#: 参与稳定性比对的辅助产物（按后缀）
TRACKED_ARTIFACTS: tuple[str, ...] = (".aux", ".out", ".toc", ".nlo", ".bbl", ".nls")

#: 会随每次编译重写的文件，不参与源快照比对
_VOLATILE_SUFFIXES = frozenset(
    {
        ".aux", ".out", ".toc", ".lof", ".lot", ".log", ".pdf", ".synctex.gz",
        ".bbl", ".blg", ".ilg", ".nlo", ".nls", ".bcf", ".run.xml", ".fls",
        ".xdv", ".spl", ".nav", ".snm", ".vrb", ".idx", ".ind", ".glo", ".gls",
        ".bak", ".userbak", ".tmp", ".listing", ".los", ".lol", ".loc", ".ltx",
        ".ent-x", ".gz", ".fdb_latexmk",
    }
)


class ArtifactBaseline(NamedTuple):
    """上一轮结束时各辅助产物的内容摘要。"""

    hashes: dict[str, str | None]
    fingerprint: str = ""

    def is_empty(self) -> bool:
        """没有任何基线（首次运行或状态文件被清理）。"""
        return not self.hashes


def _digest_file(path: Path) -> str | None:
    """计算文件 sha256；文件不存在返回 None。"""
    try:
        data = path.read_bytes()
    except OSError:
        return None
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _digest_text(text: str) -> str:
    """计算字符串 sha256。"""
    return "sha256:" + hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


class BuildState:
    """构建状态的读写门面（薄封装，落盘交给 ``ProjectStateStore``）。"""

    def __init__(self, auxdir: str | Path, project_name: str) -> None:
        """初始化：绑定 auxdir 与主文件名。"""
        self.auxdir = Path(auxdir)
        self.project_name = project_name
        self._store = ProjectStateStore(self.auxdir, project_name)

    # ------------------------------------------------------------ 产物基线

    def _artifact_path(self, suffix: str) -> Path:
        """辅助产物在根目录或 auxdir 中的位置（优先根目录）。"""
        root_candidate = Path(f"{self.project_name}{suffix}")
        if root_candidate.exists():
            return root_candidate
        return self.auxdir / f"{self.project_name}{suffix}"

    def current_artifact_hashes(self) -> dict[str, str | None]:
        """计算**当前**各辅助产物的内容摘要。"""
        return {suffix: _digest_file(self._artifact_path(suffix)) for suffix in TRACKED_ARTIFACTS}

    def load_baseline(self) -> ArtifactBaseline:
        """读取**上一轮**落盘的产物基线。"""
        build = self._store.get_build()
        hashes = build.get("artifacts")
        if not isinstance(hashes, dict):
            return ArtifactBaseline({}, "")
        clean: dict[str, str | None] = {}
        for suffix in TRACKED_ARTIFACTS:
            value = hashes.get(suffix)
            clean[suffix] = value if isinstance(value, str) else None
        return ArtifactBaseline(clean, str(build.get("fingerprint") or ""))

    def baseline_matches_current(self) -> bool:
        """当前产物是否与上次落盘的基线完全一致。

        用于"源文件未变则跳过编译"：基线一致说明上次编译后什么都没被改动。
        """
        baseline = self.load_baseline()
        if baseline.is_empty():
            return False
        current = self.current_artifact_hashes()
        return all(current.get(suffix) == baseline.hashes.get(suffix) for suffix in TRACKED_ARTIFACTS)

    # ------------------------------------------------------------ 每轮落盘

    def save_round(
        self,
        *,
        round_no: int,
        fingerprint: str,
        dims: dict[str, int],
        signals: dict[str, list[str]] | None = None,
        stop_reason: str = "",
        converged: bool = False,
        sources: dict[str, Any] | None = None,
    ) -> bool:
        """把本轮结束时的状态写进状态文件。"""
        payload: dict[str, Any] = {
            "fingerprint": fingerprint,
            "round": int(round_no),
            "dims": {str(k): int(v) for k, v in dims.items()},
            "artifacts": self.current_artifact_hashes(),
            "converged": bool(converged),
            "stop_reason": stop_reason,
        }
        if signals is not None:
            payload["signals"] = {
                "permanent": sorted(signals.get("permanent", [])),
                "transient": sorted(signals.get("transient", [])),
            }
        if sources is not None:
            payload["sources"] = sources
        return self._store.update_build(**payload)

    # ------------------------------------------------------------ 源快照

    def source_snapshot(self, tex_files: Iterable[str | Path]) -> dict[str, dict[str, int]]:
        """记录参与编译的源文件 ``(size, mtime_ns)``。

        用纳秒时间戳而非秒，避免"同尺寸、同秒内修改"被误判为未变。
        """
        snapshot: dict[str, dict[str, int]] = {}
        for raw in tex_files:
            path = Path(raw)
            if path.suffix.lower() in _VOLATILE_SUFFIXES:
                continue
            try:
                stat = path.stat()
            except OSError:
                continue
            snapshot[path.as_posix()] = {"size": stat.st_size, "mtime_ns": stat.st_mtime_ns}
        return snapshot

    def sources_unchanged(self, tex_files: Iterable[str | Path]) -> bool:
        """源文件是否与上次落盘的快照完全一致。"""
        previous = self._store.get_build().get("sources")
        if not isinstance(previous, dict) or not previous:
            return False
        current = self.source_snapshot(tex_files)
        if not current:
            return False
        if set(current) != set(previous):
            return False
        for name, meta in current.items():
            old = previous.get(name)
            if not isinstance(old, dict):
                return False
            if old.get("size") != meta["size"] or old.get("mtime_ns") != meta["mtime_ns"]:
                return False
        return True

    def was_converged(self) -> bool:
        """上次是否判定为收敛。"""
        return bool(self._store.get_build().get("converged"))

    def last_stop_reason(self) -> str:
        """上次停止的原因标识。"""
        return str(self._store.get_build().get("stop_reason") or "")

    # ------------------------------------------------------------ 清理

    def record_fingerprint(self, fingerprint: str) -> bool:
        """只更新指纹（用于源文件未变、整次编译被跳过时刷新时间戳）。"""
        return self._store.update_build(fingerprint=fingerprint)

    def discard(self) -> bool:
        """清除 ``pytexmk.build`` 基线，保留 ``pytexlogs.refs``。

        ``pytexmk -c`` 删掉辅助文件后必须调用，否则下次编译会把"产物已删除"
        误判为"产物未变动"。
        """
        return self._store.remove_namespace("pytexmk")

    def remove_state_file_if_empty(self) -> bool:
        """若状态文件只剩空骨架，则删除它（``-Ca`` 彻底清理场景）。

        只要还有任何工具的命名空间内容就保留，避免误删 pytexlogs 的引用缓存。
        """
        state = self._store.load()
        has_payload = any(
            isinstance(state.get(key), dict) and state[key]
            for key in state
            if key not in ("schema_version", "timestamp", "jobs")
        )
        if has_payload:
            return False
        return self._store.clear()

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
from .layout import SOURCE_SNAPSHOT_EXCLUDED_SUFFIXES

_ = set_language("build_state")
logger = logging.getLogger(__name__)

#: 参与稳定性比对的辅助产物（按后缀）
TRACKED_ARTIFACTS: tuple[str, ...] = (".aux", ".out", ".toc", ".nlo", ".bbl", ".nls")

#: 不参与源快照比对的产物后缀；.pdf 特意保留（可能是 \includegraphics 输入）
_SOURCE_SNAPSHOT_EXCLUDED_SUFFIXES = SOURCE_SNAPSHOT_EXCLUDED_SUFFIXES


class ArtifactBaseline(NamedTuple):
    """上一轮结束时各辅助产物的内容摘要。"""

    hashes: dict[str, str | None]
    fingerprint: str = ""

    def is_empty(self) -> bool:
        """没有任何基线（首次运行或状态文件被清理）。"""
        return not self.hashes


def _digest_file(path: Path) -> str | None:
    """计算文件 sha256；文件不存在返回 None。

    用 ``hashlib.file_digest`` 流式读取，避免大 PDF/日志整份进内存。
    """
    try:
        with path.open("rb") as fh:
            digest = hashlib.file_digest(fh, "sha256")
    except OSError:
        return None
    return "sha256:" + digest.hexdigest()


class BuildState:
    """构建状态的读写门面（薄封装，落盘交给 ``ProjectStateStore``）。"""

    def __init__(self, auxdir: str | Path, project_name: str) -> None:
        """初始化：绑定 auxdir 与主文件名。"""
        self.auxdir = Path(auxdir)
        self.project_name = project_name
        self._store = ProjectStateStore(self.auxdir, project_name)

    # ------------------------------------------------------------ 产物基线

    def _artifact_path(self, suffix: str) -> Path:
        """辅助产物路径：auxdir 与根目录都存在时取**较新的**那份。

        0.5 无条件优先根目录：native 构建（``-output-directory``）把新产物写在
        auxdir，根目录残留的是上一轮的旧副本，基线比对因此会"看到旧文件"，
        误判成"未变化"而跳过一次本该发生的编译。
        """
        name = f"{self.project_name}{suffix}"
        candidates = [p for p in (self.auxdir / name, Path(name)) if p.exists()]
        if not candidates:
            return Path(name)
        try:
            return max(candidates, key=lambda p: p.stat().st_mtime)
        except OSError:
            return candidates[0]

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
        build_key: str = "",
        diagnostics: dict[str, Any] | None = None,
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
        if build_key:
            payload["build_key"] = build_key
        if signals is not None:
            payload["signals"] = {
                "permanent": sorted(signals.get("permanent", [])),
                "transient": sorted(signals.get("transient", [])),
            }
        if sources is not None:
            payload["sources"] = sources
        if diagnostics is not None:
            payload["diagnostics"] = diagnostics
        return self._store.update_build(**payload)

    # ------------------------------------------------------------ 源快照

    def source_snapshot(self, tex_files: Iterable[str | Path]) -> dict[str, dict[str, int]]:
        """记录参与编译的源文件 ``(size, mtime_ns)``。

        用纳秒时间戳而非秒，避免"同尺寸、同秒内修改"被误判为未变。
        """
        snapshot: dict[str, dict[str, int]] = {}
        for raw in tex_files:
            path = Path(raw)
            if path.suffix.lower() in _SOURCE_SNAPSHOT_EXCLUDED_SUFFIXES:
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

    def build_key(self) -> str:
        """上次构建的参数指纹（编译器/交互模式/shell-escape/目录等）。

        参数变了就必须重新编译：换 ``pdflatex`` 为 ``xelatex`` 得到的 PDF
        与上次基线完全不可比，不能因为"源文件没动"就跳过。
        """
        return str(self._store.get_build().get("build_key") or "")

    def diagnostics_record(self) -> dict[str, Any]:
        """上次落盘的诊断可用性记录（``available`` / ``digest`` / ``size``）。"""
        record = self._store.get_build().get("diagnostics")
        return record if isinstance(record, dict) else {}

    def record_outputs(self, pdf: Path | None, synctex: Path | None) -> bool:
        """记录 outdir 里 PDF/SyncTeX 的内容摘要（配对校验用）。

        只记录 PDF 是否存在不够：外部工具替换 PDF、但留下上一轮的 synctex，
        缓存命中后编辑器会按旧坐标跳到错误位置。这里把两份文件的摘要**一起**
        落盘，复用时必须同时匹配。
        """
        payload = {
            "pdf": _digest_file(pdf) if pdf is not None else None,
            "synctex": _digest_file(synctex) if synctex is not None else None,
        }
        return self._store.update_build(output_artifacts=payload)

    def output_record(self) -> dict[str, Any]:
        """上次记录的 outdir 产物摘要。"""
        record = self._store.get_build().get("output_artifacts")
        return record if isinstance(record, dict) else {}

    def log_path(self) -> Path:
        """日志路径：auxdir 与根目录都存在时取较新的那份。

        非原生构建（``--no-native``）的 ``.log`` 先写在根目录，归档后才进
        auxdir；构建基线是在归档**之前**落盘的，只看 auxdir 会记成“不可用”，
        导致下一次永远无法安全复用诊断。
        """
        name = f"{self.project_name}.log"
        candidates = [p for p in (self.auxdir / name, Path(name)) if p.is_file()]
        if not candidates:
            return self.auxdir / name
        try:
            return max(candidates, key=lambda p: p.stat().st_mtime)
        except OSError:
            return candidates[0]

    def log_record(self) -> dict[str, Any]:
        """当前日志的可用性与内容摘要。"""
        log_path = self.log_path()
        try:
            size = log_path.stat().st_size
        except OSError:
            return {"available": False, "digest": None, "size": 0}
        return {
            "available": size > 0,
            "digest": _digest_file(log_path),
            "size": size,
        }

    # ------------------------------------------------------------ 清理

    def discard(self) -> bool:
        """清除 ``pytexmk.build`` 基线，保留 ``pytexlogs.refs``。

        ``pytexmk -c`` 删掉辅助文件后必须调用，否则下次编译会把"产物已删除"
        误判为"产物未变动"。
        """
        return self._store.remove_namespace("pytexmk")

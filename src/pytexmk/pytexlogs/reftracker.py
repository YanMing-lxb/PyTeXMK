"""参考文献引用变更追踪：对比新旧 .aux/.bcf 检测新增/移除引用."""
from __future__ import annotations

import json
import logging
import re
from collections import Counter
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from .biber import BiberParser

__all__ = [
    "RefChangeTracker",
    "citation_command_re",
    "input_re",
]

input_re = re.compile(r"\\(?:input|include)\{(.+?)\}")
citation_command_re = re.compile(
    r"\\(?:cite|upcite|citet|citep|parencite|textcite|footcite|smartcite|autocite)\{([^}]+)\}",
    re.IGNORECASE,
)

logger = logging.getLogger(__name__)


class RefChangeTracker:
    """参考文献变更追踪器：从 aux/bcf 提取引用键并与缓存 diff。"""
    def __init__(self, auxdir: str | Path, jobname: str, translate_fn: Callable[[str], str] | None = None) -> None:
        """初始化 RefChangeTracker：缓存 auxdir、jobname 与引用缓存路径。"""
        self.auxdir = Path(auxdir)
        self.jobname = jobname
        self.cache_path = self.auxdir / ".pytexmk_refcache.json"
        self._translate_fn: Callable[[str], str] = translate_fn or (lambda s: s)

    def extract_from_aux(self, aux_path: str | Path) -> list[str]:
        """从 LaTeX .aux 文件提取所有 cite 引用键列表。"""
        path = Path(aux_path)
        if not path.exists():
            return []
        text = path.read_text(encoding="utf-8", errors="ignore")
        keys: list[str] = []

        pattern1 = re.compile(r"\\citation\{([^}]+)\}")
        pattern2 = re.compile(r"\\abx@aux@cite\{[^}]*\}\{([^}]+)\}")
        pattern3 = re.compile(r"\\bibcite\{([^}]+)\}")

        for m in pattern1.finditer(text):
            try:
                group = m.group(1)
                for k in group.split(","):
                    key = k.strip()
                    if key:
                        keys.append(key)
            except Exception as e:  # noqa: BLE001
                logger.warning("pattern1 匹配解析异常: %s", e)

        for m in pattern2.finditer(text):
            try:
                group = m.group(1)
                for k in group.split(","):
                    key = k.strip()
                    if key:
                        keys.append(key)
            except Exception as e:  # noqa: BLE001
                logger.warning("pattern2 匹配解析异常: %s", e)

        for m in pattern3.finditer(text):
            try:
                group = m.group(1)
                for k in group.split(","):
                    key = k.strip()
                    if key:
                        keys.append(key)
            except Exception as e:  # noqa: BLE001
                logger.warning("pattern3 匹配解析异常: %s", e)

        return keys

    def extract_from_bcf(self, bcf_path: str | Path) -> list[str]:
        """从 Biber .bcf 文件提取所有 cite 引用键列表。"""
        return BiberParser.parse_bcf(bcf_path)

    def detect_mode(self) -> Literal["bibtex", "biber", "unknown"]:
        """检测当前参考文献模式：bibtex/biber/unknown。"""
        bcf_path = self.auxdir / f"{self.jobname}.bcf"
        if bcf_path.exists():
            return "biber"

        aux_path = self.auxdir / f"{self.jobname}.aux"
        if aux_path.exists():
            try:
                text = aux_path.read_text(encoding="utf-8", errors="ignore")
                if "\\bibdata" in text or "\\citation" in text or "\\bibcite" in text:
                    return "bibtex"
            except Exception:  # noqa: BLE001,S110
                pass

        return "unknown"

    def extract_current(self) -> list[str]:
        """根据检测到的模式提取当前运行的引用键列表（不去重，保留重复用于计数）。"""
        mode = self.detect_mode()
        if mode == "biber":
            return self.extract_from_bcf(self.auxdir / f"{self.jobname}.bcf")
        elif mode == "bibtex":
            return self.extract_from_aux(self.auxdir / f"{self.jobname}.aux")
        return []

    def extract_current_with_counts(self) -> tuple[list[str], dict[str, int]]:
        """提取当前引用键列表（不去重）并统计每个 key 的出现次数。"""
        raw_keys = self.extract_current()
        counts = dict(Counter(raw_keys))
        return raw_keys, counts

    def extract_current_counts(self) -> dict[str, int]:
        """提取当前引用键的计数统计（不去重统计）。"""
        return self.extract_current_with_counts()[1]

    def load_cache(self) -> list[str]:
        """从 JSON 缓存加载上次保存的引用键列表（schema v1/v2 兼容，v1 缺失 schema_version 默认 1）。"""
        if not self.cache_path.exists():
            return []
        try:
            data = json.loads(self.cache_path.read_text(encoding="utf-8"))
            return list(data.get("keys", []))
        except Exception:  # noqa: BLE001
            return []

    def load_cache_counts(self) -> dict[str, int]:
        """从 JSON 缓存加载上次保存的 key_counts 统计（schema v2+，旧版返回空 dict）。"""
        if not self.cache_path.exists():
            return {}
        try:
            data = json.loads(self.cache_path.read_text(encoding="utf-8"))
            kc = data.get("key_counts", {})
            if isinstance(kc, dict):
                return {str(k): int(v) for k, v in kc.items()}
            return {}
        except Exception:  # noqa: BLE001
            return {}

    def save_cache(
        self, keys: Iterable[str], key_counts: dict[str, int] | None = None
    ) -> None:
        """将引用键列表保存为 JSON 缓存文件（schema v2：含 schema_version + key_counts）。"""
        self.auxdir.mkdir(parents=True, exist_ok=True)
        if key_counts is None:
            key_counts = dict(Counter(keys))
        data = {
            "schema_version": 2,
            "timestamp": datetime.now(UTC).isoformat(),
            "keys": sorted(set(keys)),
            "key_counts": key_counts,
        }
        self.cache_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def diff(
        self, now_keys: Iterable[str], old_keys: Iterable[str]
    ) -> dict[str, set[str]]:
        """计算新旧引用键集合差异：新增/移除/未变。"""
        now_set = set(now_keys)
        old_set = set(old_keys)
        return {
            "added": now_set - old_set,
            "removed": old_set - now_set,
            "unchanged": now_set & old_set,
        }

    def format_report(self, diff_dict: dict[str, set[str]], total_unique: int) -> str:
        """将引用差异结果格式化为人类可读字符串。"""
        added = len(diff_dict.get("added", set()))
        removed = len(diff_dict.get("removed", set()))
        old_cache_empty = len(diff_dict.get("unchanged", set())) == 0 and removed == 0

        if added == 0 and removed == 0:
            return self._translate_fn("参考文献: {} 篇引用, 无变动").format(total_unique)

        if old_cache_empty and removed == 0:
            return self._translate_fn("参考文献: {} 篇引用, 首次运行, 新增 {}").format(
                total_unique, added
            )

        return self._translate_fn("参考文献: {} 篇引用, 新增 {}, 移除 {}").format(
            total_unique, added, removed
        )

    def summarize_diff(self, old_keys: Iterable[str], now_keys: Iterable[str]) -> str:
        """便捷方法：对比新旧引用键集合并返回格式化的差异摘要字符串。"""
        diff_dict = self.diff(now_keys, old_keys)
        total_unique = len(set(now_keys))
        return self.format_report(diff_dict, total_unique)

"""``paths.get_app_path`` 三种运行形态。"""
import sys
from pathlib import Path

import pytexmk.paths as paths


def test_uses_meipass_when_present(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    assert paths.get_app_path() == tmp_path


def test_uses_executable_dir_when_frozen(monkeypatch, tmp_path):
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "pytexmk.exe"))
    assert paths.get_app_path() == tmp_path


def test_uses_package_dir_for_source_run(monkeypatch):
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    app_path = Path(paths.get_app_path())
    assert app_path.is_dir()
    assert app_path.name == "pytexmk"

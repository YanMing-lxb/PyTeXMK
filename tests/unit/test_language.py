"""系统语言探测、缓存与翻译回退。"""

import locale

import pytest

from pytexmk import language


@pytest.fixture(autouse=True)
def _clear_lang_cache():
    language.get_locale_lang.cache_clear()
    language.set_language.cache_clear()
    yield
    language.get_locale_lang.cache_clear()
    language.set_language.cache_clear()


@pytest.fixture
def clean_env(monkeypatch):
    for name in ("LANGUAGE", "LC_ALL", "LC_CTYPE", "LANG"):
        monkeypatch.delenv(name, raising=False)


def test_get_locale_lang_is_cached(clean_env, monkeypatch):
    monkeypatch.setenv("LANGUAGE", "en_US.UTF-8")
    assert language.get_locale_lang() == "en_US"

    # 本项目没有运行时切换语言的入口，缓存后不应因环境变量变化而重新探测。
    monkeypatch.setenv("LANGUAGE", "ja_JP")
    assert language.get_locale_lang() == "en_US"

    language.get_locale_lang.cache_clear()


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("zh_CN.UTF-8", "zh_CN"),
        ("ca_ES@valencia", "ca_ES"),
        ("zh_CN:zh:en_US:en", "zh_CN"),
    ],
)
def test_env_value_is_normalized(clean_env, monkeypatch, raw, expected):
    monkeypatch.setenv("LANGUAGE", raw)
    assert language.get_locale_lang() == expected


def test_c_locale_is_skipped(clean_env, monkeypatch):
    monkeypatch.setenv("LANGUAGE", "C")
    monkeypatch.setenv("LC_ALL", "ja_JP")
    assert language.get_locale_lang() == "ja_JP"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Chinese (Simplified)_China", "zh_CN"),
        ("Chinese (Traditional)_Taiwan", "zh_TW"),
        ("English_United States", "en"),
        ("Klingon", "Klingon"),
        ("", ""),
    ],
)
def test_windows_locale_names_are_normalized(raw, expected):
    assert language._normalize_windows_locale(raw) == expected


def test_falls_back_to_locale_getlocale(clean_env, monkeypatch):
    monkeypatch.setattr(locale, "getlocale", lambda: ("Chinese (Simplified)_China", None))
    monkeypatch.setattr(locale, "setlocale", lambda *a: None)
    assert language.get_locale_lang() == "zh_CN"


def test_zh_uses_identity_translation(clean_env, monkeypatch):
    monkeypatch.setattr(language, "get_locale_lang", lambda: "zh_CN")
    translate = language.set_language("unit_test_zh")
    assert translate("中文原文") == "中文原文"


def test_missing_mo_falls_back_to_source(clean_env, monkeypatch):
    monkeypatch.setattr(language, "get_locale_lang", lambda: "xx_YY")
    translate = language.set_language("unit_test_missing_domain")
    assert translate("fallback text") == "fallback text"


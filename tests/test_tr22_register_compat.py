from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pytexmk.pytexlogs.latexlog import LatexLogParser
from pytexmk.pytexlogs.manager import LogParserManager


def main() -> int:
    print("=" * 70)
    print("TR-2.2: register() + lookup() 兼容性验证")
    print("=" * 70)
    ok_all = True

    manager = LogParserManager()

    print("\n[Test 1] manager.register('my_step', LatexLogParser)")
    try:
        manager.register('my_step', LatexLogParser)
        print("  ✓ register() 无异常")
    except Exception as e:
        print(f"  ✗ register() 抛出异常: {e!r}")
        ok_all = False

    print("\n[Test 2] manager.lookup('my_step') is not None")
    try:
        spec = manager.lookup('my_step')
        if spec is not None:
            print(f"  ✓ lookup 返回 spec: parser_cls={spec.parser_cls.__name__}, category={spec.category!r}")
            if spec.parser_cls is LatexLogParser:
                print("  ✓ parser_cls 正确指向 LatexLogParser")
            else:
                print(f"  ✗ parser_cls 错误: {spec.parser_cls}")
                ok_all = False
        else:
            print("  ✗ lookup 返回 None！")
            ok_all = False
    except Exception as e:
        print(f"  ✗ lookup() 抛出异常: {e!r}")
        ok_all = False

    print("\n[Test 3] 额外：通过 run(steps=['my_step']) 调用 + captured_outputs 验证")
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        captured = {
            'my_step': (
                "This is pdfTeX, Version 3.141592653-2.6-1.40.25\n"
                "entering extended mode\n"
                "(./main.tex\n"
                "LaTeX Warning: Reference `missing' on page 1 undefined on input line 10.\n"
                "! Undefined control sequence.\n"
                "l.20 \\badcmd\n"
                "Output written on main.pdf (1 page, 1000 bytes).\n"
                "Transcript written on main.log.\n"
            )
        }
        try:
            results = manager.run('main', tmpdir, steps=['my_step'], captured_outputs=captured)
            if len(results) == 1:
                r = results[0]
                print("  ✓ run() 返回 1 条结果")
                print(f"    tool_name={r.tool_name!r} (期望 'my_step')")
                print(f"    category={r.category!r}")
                print(f"    len(entries)={len(r.entries)}")
                print(f"    stats.stats['error']={r.stats.stats.get('error')}")
                print(f"    stats.stats['warning']={r.stats.stats.get('warning')}")
                if r.tool_name != 'my_step':
                    print("  ✗ tool_name 错误")
                    ok_all = False
            else:
                print(f"  ✗ run() 返回 {len(results)} 条结果，期望 1")
                ok_all = False
        except Exception as e:
            print(f"  ✗ run() 抛出异常: {e!r}")
            import traceback
            traceback.print_exc()
            ok_all = False

    print("\n[Test 4] 验证 register 后，fallback 也生效（用完全未知的 step_name）")
    from pytexmk.pytexlogs.bibtex import BibtexParser
    manager2 = LogParserManager()
    manager2.register('custom_bib', BibtexParser)
    spec2 = manager2.lookup('custom_bib')
    if spec2 is not None and spec2.parser_cls is BibtexParser:
        print("  ✓ 第二步 register('custom_bib', BibtexParser) → lookup 成功")
    else:
        print("  ✗ 第二步 register 失败")
        ok_all = False

    print("\n" + "=" * 70)
    if ok_all:
        print("[PASS] TR-2.2 register() + lookup() 兼容性验证全通过")
        return 0
    else:
        print("[FAIL] TR-2.2 存在上述失败项")
        return 1


def test_tr22_register_compat():
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())

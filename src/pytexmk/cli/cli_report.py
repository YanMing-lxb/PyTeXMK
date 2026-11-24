"""``-r`` 报告入口：只读最近一次编译日志，生成 JSON + Markdown 报告。

语义约定：

* 不触发编译，也不在找不到日志时生成空报告；
* JSON 由 PyTeXLogs 解析 ``Auxiliary/<jobname>.log`` 生成；
* Markdown 报告只读取这份 JSON 再生成；
* 路径固定，不提供参数或配置项；
* 成功退出 0；缺日志按一般错误退出；JSON 或 Markdown 写失败退出 ``9``。
"""

from pathlib import Path

from ..diagnostics import ReportWriteError, generate_report_from_latest_log
from ..language import set_language
from ..lifecycle import EXIT_ERROR, EXIT_REPORT_FAILED, exit_pytexmk
from ..report_export import export_report, print_report_error
from ..ui_theme import console
from .cli_state import WorkflowState

_ = set_language("cli_workflow")


def handle(state: WorkflowState) -> None:
    """为 ``-r`` 生成报告；不进入编译流程。"""
    jobname = state.output_name
    if not jobname:
        console.print(
            "[bold red]" + _("无法确定主文件，不能定位最近一次编译日志") + "[/bold red]"
        )
        exit_pytexmk(EXIT_ERROR)

    try:
        json_path, reason = generate_report_from_latest_log(
            state.auxdir,
            jobname,
            root_file=f"{state.project_name}.tex",
        )
    except ReportWriteError as exc:
        console.print(str(exc), style="bold red", markup=False)
        exit_pytexmk(EXIT_REPORT_FAILED)
    if json_path is None:
        console.print(
            "[bold red]"
            + _("无法从最近一次编译日志生成报告: %(r)s") % {"r": reason}
            + "[/bold red]"
        )
        exit_pytexmk(EXIT_ERROR)

    md_path = Path(state.auxdir) / f"{jobname}.pytexmk-report.md"
    result = export_report(json_path, md_path)
    if not result.ok:
        print_report_error(result)
        exit_pytexmk(EXIT_REPORT_FAILED)

    console.print("[bold green]" + _("诊断报告已生成") + "[/bold green]")
    console.print("  " + _("JSON: ") + str(json_path))
    console.print("  " + _("Markdown: ") + str(result.md_path))

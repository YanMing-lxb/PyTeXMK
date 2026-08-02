import logging
import webbrowser
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from rich import print

from pytexmk.language import set_language

_ = set_language("additional")


class PdfFileOperation:
    def __init__(self, viewer="default"):
        self.logger = logging.getLogger(__name__)
        self.viewer = viewer

    def set_viewer(self, new_viewer):
        self.viewer = new_viewer

    def _preview_pdf_by_viewer(self, local_path: str):
        if self.viewer == "default" or not self.viewer:
            self.logger.info(_("未设置 PDF 查看器,使用默认 PDF 查看器"))
            webbrowser.open(local_path)
        elif self.viewer and self.viewer != "default":
            self.logger.info(_("设置 PDF 查看器: ") + f"{self.viewer}")

    def pdf_preview(self, project_name: str, outdir: str):
        try:
            pdf_name = f"{project_name}.pdf"
            pdf_path = Path(outdir) / pdf_name
            local_path = f"file://{pdf_path.resolve().as_posix()}"
            self.logger.info(_("文件路径: ") + f"{local_path}")
            self._preview_pdf_by_viewer(local_path)
        except Exception as e:  # noqa: BLE001
            self.logger.error(_("打开文件失败: ") + f"{pdf_name} -->{e}")

    def pdf_repair(self, project_name: str, root_dir: str, excluded_folder: str):
        root_dir = Path(root_dir)
        pdf_files = [
            path
            for path in root_dir.rglob("*.pdf")
            if ".git" not in path.parts
            and ".github" not in path.parts
            and path.is_file()
            and path.name != f"{project_name}.pdf"
            and path.parent.name != excluded_folder
        ]

        if not pdf_files:
            print(_("当前路径下没有 PDF 文件"))
            return

        print(_("找到 PDF 文件数目: ") + f"[bold cyan]{len(pdf_files)}[/bold cyan]")
        for pdf_file in pdf_files:
            try:
                reader = PdfReader(pdf_file)
                writer = PdfWriter()

                for page in reader.pages:
                    writer.add_page(page)

                with open(pdf_file, "wb") as f:
                    writer.write(f)

                self.logger.info(_("修复成功: ") + str(pdf_file))
            except Exception as e:  # noqa: BLE001
                self.logger.error(_("修复失败: ") + f"{pdf_file} --> {e}")
        print(_("[bold green]修复 PDF 结束[/bold green]"))


import locale

def check_language(info_strings_zh, info_strings_en):
    # 获取当前系统的默认区域设置
    current_locale = locale.getdefaultlocale()
    if current_locale[0].startswith('zh'):
        return info_strings_zh
    else:
        return info_strings_en

def info_desrption(info_list, key):
    return info_list[key]

magic_comments_description_en = {
    '% !TEX program = xelatex': 'Specify the compilation type, options include xelatex pdflatex lualatex',
    '% !TEX root = file.tex': 'Specify the LaTeX file to be compiled, only supports the main file in the project root directory',
    '% !TEX outdir = PDFfile': 'Specify the location to store compilation results, only supports folder names',
    '% !TEX auxdir = auxfiles': 'Specify the location to store auxiliary files, only supports folder names'
}
magic_comments_description_zh = {
    '% !TEX program = xelatex': '指定编译类型，可选 xelatex pdflatex lualatex',
    '% !TEX root = file.tex': '指定待编译 LaTeX 文件名，仅支持主文件在项目根目录下的情况',
    '% !TEX outdir = PDFfile': '指定编译结果存放位置，仅支持文件夹名称',
    '% !TEX auxdir = auxfiles': '指定辅助文件存放位置，仅支持文件夹名称'
}

description_en = r"""
    <LaTeX Auxiliary Compilation Program>
    For information on magic comments and other detailed instructions, please run the [-r] parameter to read the README file.
    If you find any bugs, please update to the latest version and feel free to submit an Issue in the Github repository: https://github.com/YanMing-lxb/PyTeXMK/issues
    """
description_zh = r"""
    <LaTeX 辅助编译程序>
    如欲了解魔法注释以及其他详细说明信息请运行 [-r] 参数，阅读 README 文件。
    发现 BUG 请及时更新到最新版本，欢迎在 Github 仓库中提交 Issue: https://github.com/YanMing-lxb/PyTeXMK/issues
    """
epilog_en = f"""
    Welcome to PyTeXMK! --YanMing
    """
epilog_zh = f"""
    欢迎使用 PyTeXMK！ --焱铭
    """

help_strings_en = {
    'description': description_en,
    'epilog': epilog_en,
    'help': "show PyTeXMK help information and exit",
    'version': "show PyTeXMK version number and exit",
    'readme': "show the README file",
    'PdfLaTeX': "compile using PdfLaTeX",
    'XeLaTeX': "compile using XeLaTeX",
    'LuaLaTeX': "compile using LuaLaTeX",
    'LaTeXDiff': "compile using LaTeXDiff to generate a difference file",
    'LaTeXDiff_compile': "compile using LaTeXDiff and compile the new file",
    'clean': "clear auxiliary files of the main file",
    'Clean': "clear auxiliary files (including root directory) and output files",
    'clean_any': "clear all files with auxiliary file suffixes",
    'Clean_any': "clear all files with auxiliary file suffixes (including root directory) and main file output files",
    'unquiet': "run in non-quiet mode, displaying log information in the terminal",
    'verbose': "show detailed information during PyTeXMK operation",
    'pdf_repair': "attempt to repair all PDF files outside the root directory. Use this option if you encounter 'invalid X X R object' warnings during LaTeX compilation",
    'pdf_preview': "preview the generated PDF file using a web browser or local PDF reader after compilation. If you need to specify the main file to be compiled in the command line, place the -pv command after the document without specifying parameters (e.g., pytexmk main -pv); if you do not need to specify the main file in the command line, just enter -pv (e.g., pytexmk -pv). If [FILE_NAME] is specified, it opens the specified file without compiling (only supports PDF files in the output directory, e.g., pytexmk -pv main)",
    'document': "main file name to be compiled"
}

help_strings_zh = {
    'description': description_zh,
    'epilog': epilog_zh,
    'help': "显示 PyTeXMK 的帮助信息并退出",
    'version': "显示 PyTeXMK 的版本号并退出",
    'readme': "显示README文件",
    'PdfLaTeX': "PdfLaTeX 进行编译",
    'XeLaTeX': "XeLaTeX 进行编译",
    'LuaLaTeX': "LuaLaTeX 进行编译",
    'LaTeXDiff': "使用 LaTeXDiff 进行编译, 生成改动对比文件",
    'LaTeXDiff_compile': "使用 LaTeXDiff 进行编译, 生成改动对比文件并编译新文件",
    'clean': "清除所有主文件的辅助文件",
    'Clean': "清除所有主文件的辅助文件（包含根目录）和输出文件",
    'clean_any': "清除所有带辅助文件后缀的文件",
    'Clean_any': "清除所有带辅助文件后缀的文件（包含根目录）和主文件输出文件",
    'unquiet': "非安静模式运行, 此模式下终端显示日志信息",
    'verbose': "显示 PyTeXMK 运行过程中的详细信息",
    'pdf_repair': "尝试修复所有根目录以外的 PDF 文件, 当 LaTeX 编译过程中警告 invalid X X R object 时, 可使用此参数尝试修复所有 pdf 文件",
    'pdf_preview': "尝试编译结束后调用 Web 浏览器或者本地PDF阅读器预览生成的PDF文件 (如需指定在命令行中指定待编译主文件, 则 -pv 命令, 需放置 document 后面并无需指定参数, 示例: pytexmk main -pv; 如无需在命令行中指定待编译主文件, 则直接输入 -pv 即可, 示例: pytexmk -pv), 如有填写 [FILE_NAME] 则不进行编译打开指定文件 (注意仅支持输出目录下的 PDF 文件, 示例: pytexmk -pv main)",
    'document': "待编译主文件名"
}

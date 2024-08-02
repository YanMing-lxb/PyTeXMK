'''
 =======================================================================
 ····Y88b···d88P················888b·····d888·d8b·······················
 ·····Y88b·d88P·················8888b···d8888·Y8P·······················
 ······Y88o88P··················88888b·d88888···························
 ·······Y888P··8888b···88888b···888Y88888P888·888·88888b·····d88b·······
 ········888······"88b·888·"88b·888·Y888P·888·888·888·"88b·d88P"88b·····
 ········888···d888888·888··888·888··Y8P··888·888·888··888·888··888·····
 ········888··888··888·888··888·888···"···888·888·888··888·Y88b·888·····
 ········888··"Y888888·888··888·888·······888·888·888··888··"Y88888·····
 ·······························································888·····
 ··························································Y8b·d88P·····
 ···························································"Y88P"······
 =======================================================================

 -----------------------------------------------------------------------
Author       : 焱铭
Date         : 2024-02-28 23:11:52 +0800
LastEditTime : 2024-08-02 09:37:27 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /PyTeXMK/src/pytexmk/__main__.py
Description  : 
 -----------------------------------------------------------------------
'''
# -*- coding: utf-8 -*-
import sys
import argparse
import datetime
import webbrowser
from rich import print
from pathlib import Path
import importlib.resources
from .version import script_name, __version__
from .compile_model import CompileModel
from .logger_config import setup_logger
from .additional_operation import MoveRemoveClean, MainFileJudgment
from .info_print import time_count, time_print, print_message
from .check_version import UpdateChecker

MFJ = MainFileJudgment() # 实例化 MainFileJudgment 类
MRC = MoveRemoveClean() # 实例化 MoveRemoveClean 类

# --------------------------------------------------------------------------------
# 整体进行编译
# --------------------------------------------------------------------------------
def RUN(start_time, compiler_engine, project_name, out_files, aux_files, outdir, auxdir, unquiet):
    runtime_dict = {}
    abbreviations_num = ('1st', '2nd', '3rd', '4th', '5th', '6th')
    # 编译前的准备工作
    compile_model = CompileModel(compiler_engine, project_name, out_files, aux_files, outdir, auxdir, unquiet)
 
    print('检测并移动辅助文件到根目录...')
    runtime_move_aux_root, _  = time_count(MRC.move_to_root, aux_files, auxdir) # 将辅助文件移动到根目录
    runtime_dict['辅助文件->根目录'] = runtime_move_aux_root
 
    # 检查并处理已存在的 LaTeX 输出文件
    print('检测识别已有辅助文件...')
    runtime_read, return_read = time_count(compile_model.prepare_LaTeX_output_files, ) # 读取 LaTeX 文件
    cite_counter, toc_file, index_aux_content_dict_old = return_read # 获取 read_LaTeX_files 函数得到的参数
    runtime_dict['检测辅助文件'] = runtime_read
 
    # 首次编译 LaTeX 文档
    print_message(f"1 次 {compiler_engine} 编译")
    runtime_Latex, _ = time_count(compile_model.compile_tex, ) 
    runtime_dict[f'{compiler_engine} {abbreviations_num[0]}'] = runtime_Latex
 
    # 读取日志文件
    with open(f'{project_name}.log', 'r', encoding='utf-8') as fobj:
        log_content = fobj.read()
    compile_model.check_errors(log_content)
 
    # 编译参考文献
    runtime_bib_judgment, return_bib_judgment = time_count(compile_model.bib_judgment, cite_counter) # 判断是否需要编译参考文献
    runtime_dict['编译文献判定'] = runtime_bib_judgment
 
    bib_engine, Latex_compilation_times_bib, print_bib, name_target_bib = return_bib_judgment # 获取 bib_judgment 函数得到的参数
    if bib_engine:
        if Latex_compilation_times_bib != 0:
            print_message(f'{bib_engine} 文献编译')
            runtime_bib, _ = time_count(compile_model.compile_bib, bib_engine) # 编译参考文献
            runtime_dict[name_target_bib] = runtime_bib
 
    # 编译索引
    runtime_makindex_judgment, return_index_judgment = time_count(compile_model.index_judgment, index_aux_content_dict_old) # 判断是否需要编译目录索引
    print_index, run_index_list_cmd = return_index_judgment
    runtime_dict['编译索引判定'] = runtime_makindex_judgment
 
    if run_index_list_cmd: # 存在目录索引编译命令
        for cmd in run_index_list_cmd:
            print_message(f"{cmd[0]} 编译")
            Latex_compilation_times_index = 1
            runtime_index, return_index = time_count(compile_model.compile_index, cmd)
            name_target_index = return_index # 获取 compile_index 函数得到的参数
            runtime_dict[name_target_index] = runtime_index
    else:
        Latex_compilation_times_index = 0
 
    # 编译目录
    if compile_model.toc_changed_judgment(toc_file): # 判断是否需要编译目录
        Latex_compilation_times_toc = 1
    else:
        Latex_compilation_times_toc = 0
 
    # 计算额外需要的 LaTeX 编译次数
    Latex_compilation_times = max(Latex_compilation_times_bib, Latex_compilation_times_index, Latex_compilation_times_toc) 
     
    # 进行额外的 LaTeX 编译
    for times in range(2, Latex_compilation_times+2):
        print_message(f"{times} 次 {compiler_engine} 编译")
        runtime_Latex, _ = time_count(compile_model.compile_tex, )
        runtime_dict[f'{compiler_engine} {abbreviations_num[times-1]}'] = runtime_Latex
 
    # 编译完成，开始判断编译 XDV 文件
    if compiler_engine == "XeLaTeX":  # 判断是否编译 xdv 文件
        print_message("DVIPDFMX 编译")
        runtime_xdv, _ = time_count(compile_model.compile_xdv, ) # 编译 xdv 文件
        runtime_dict['DVIPDFMX 编译'] = runtime_xdv
 
    # 显示编译过程中关键信息
    border = "[red bold]=[/red bold]" * 80
    center = "[green on white bold]▓[/green on white bold]" * 33 + " [bold green]完成所有编译[/bold green] " + "[green on white bold]▓[/green on white bold]" * 33
    print(f"\n{border}")
    print(f"{center}")
    print(f"{border}\n")
    print(f"文档整体：{compiler_engine} 编译 {Latex_compilation_times+1} 次")
    print(f"参考文献：{print_bib}")
    print(f"目录索引：{print_index}")
    print_message("开始执行编译以外的附加命令")
     
    print('移动结果文件到输出目录...')
    runtime_move_out_outdir, _ = time_count(MRC.move_to_folder, out_files, outdir) # 将输出文件移动到指定目录
    runtime_dict["结果文件->输出目录"] = runtime_move_out_outdir
 
    print('移动辅助文件到辅助目录...')
    runtime_move_aux_auxdir, _ = time_count(MRC.move_to_folder, aux_files, auxdir) # 将辅助文件移动到指定目录
    runtime_dict["辅助文件->辅助目录"] = runtime_move_aux_auxdir
    time_print(start_time, runtime_dict) # 打印编译时长统计



def main():
    # ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! 设置默认 ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! !
    compiler_engine = "XeLaTeX"
    outdir = "./Build/"
    auxdir = "./Auxiliary/"
    magic_comments_keys = ["program", "root", "outdir", "auxdir"]
    # ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! !

    start_time = datetime.datetime.now() # 计算开始时间
    # 不能再在这个程序上花时间了，该看论文学技术了，要不然博士怎么毕业啊，吐了。---- 焱铭,2024-07-28 21:02:30
    # --------------------------------------------------------------------------------
    # 定义命令行参数
    # --------------------------------------------------------------------------------
    # TODO 完善对魔法注释的说明
    # TODO 添加latexdiff的功能
    parser = argparse.ArgumentParser(
        description=r"""
LaTeX 辅助编译程序，如欲获取详细说明信息请运行 [-r] 参数。
如发现 BUG 请及时更新到最新版本并在 Github 仓库中提交 Issue：https://github.com/YanMing-lxb/PyTeXMK/issues""",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="欢迎使用 PyTeXMK！(魔法注释的说明请阅读 README 文件)")
    parser.add_argument('-v', '--version', action='version', version=f'{script_name}: {__version__}')
    parser.add_argument('-r', '--readme', action='store_true', help="显示README文件")
    parser.add_argument('-p', '--PdfLaTeX', action='store_true', help="PdfLaTeX 进行编译")
    parser.add_argument('-x', '--XeLaTeX', action='store_true', help="XeLaTeX 进行编译")
    parser.add_argument('-l', '--LuaLaTeX', action='store_true', help="LuaLaTeX 进行编译")
    parser.add_argument('-c', '--clean', action='store_true', help="清除所有主文件的辅助文件")
    parser.add_argument('-C', '--Clean', action='store_true', help="清除所有主文件的辅助文件（包含根目录）和输出文件")
    parser.add_argument('-ca', '--clean-any', action='store_true', help="清除所有带辅助文件后缀的文件")
    parser.add_argument('-Ca', '--Clean-any', action='store_true', help="清除所有带辅助文件后缀的文件（包含根目录）和主文件输出文件")
    parser.add_argument('-uq', '--unquiet', action='store_true', help="非安静模式运行，此模式下终端显示日志信息")
    parser.add_argument('-vb', '--verbose', action='store_true', help="显示 PyTeXMK 运行过程中的详细信息")
    parser.add_argument('-pr', '--pdf-repair', action='store_true', help="尝试修复所有根目录以外的 pdf 文件，当 LaTeX 编译过程中警告 invalid X X R object 时，可使用此参数尝试修复所有 pdf 文件")
    parser.add_argument('document', nargs='?', help="待编译主文件名")
    args = parser.parse_args()

    print(f"PyTeXMK 版本：[bold green]{__version__}[/bold green]\n")
    print('[bold green]PyTeXMK 开始运行...\n')

    logger = setup_logger(args.verbose) # 实例化 logger 类

    # --------------------------------------------------------------------------------
    # README 文件打开函数
    # --------------------------------------------------------------------------------
    if args.readme: # 如果存在 readme 参数
        try:
            # 使用 pathlib 获取包数据路径
            data_path = Path(importlib.resources.files('pytexmk')) / 'data'
            # 使用 pathlib 拼接 README.html 文件路径
            readme_path = data_path / "README.html"
            print(f"[bold green]正在打开 README 文件...")
            # 使用 pathlib 获取 README.html 文件的绝对路径
            logger.info('README 的本地路径是：file://' + readme_path.resolve().as_posix())
            # 使用 webbrowser 打开 README.html 文件
            webbrowser.open('file://' + readme_path.resolve().as_posix())
        except Exception as e:
            # 记录打开 README 文件时的错误信息
            logger.error(f"打开 README 文件时出错: {e}")
        finally:
            # 打印退出信息并退出程序
            print('[bold red]正在退出 PyTeXMK ...[/bold red]')
            sys.exit()

    # --------------------------------------------------------------------------------
    # 主文件逻辑判断
    # --------------------------------------------------------------------------------
    # TODO 添加块注释，或者整合到additional_operation.py中
    project_name = '' # 待编译主文件名
    tex_files_in_root = MFJ.get_tex_files_in_root() # 运行 get_tex_file_in_root 函数判断获取当前根目录下所有 tex 文件，并去掉文件后缀
    main_file_in_root = MFJ.find_tex_commands(tex_files_in_root) # 运行 find_tex_commands 函数判断获取当前根目录下的主文件列表
    all_magic_comments = MFJ.search_magic_comments(main_file_in_root, magic_comments_keys) # 运行 search_magic_comments 函数搜索 main_file_in_root 每个文件的魔法注释
    magic_comments = {} # 存储魔法注释
    current_path = Path.cwd()  # 使用pathlib库获取当前工作目录的路径
    if args.document: # 当前目录下存在 tex 文件，且命令行参数中指定了主文件
        project_name = args.document # 使用命令行参数指定主文件
        print(f"通过命令行命令指定待编译主文件为：[bold cyan]{project_name}[/bold cyan]")
    if len(main_file_in_root) == 1: # 如果当前根目录下存在且只有一个主文件
        project_name = main_file_in_root[0] # 使用该文件作为待编译主文件
        print(f"通过根目录下唯一主文件指定待编译主文件为：[bold cyan]{project_name}.tex[/bold cyan]")

    if 'root' in all_magic_comments: # 当前目录下存在多个主文件，且存在 % TEX root 魔法注释
        logger.info("魔法注释 % !TEX root 在当前根目录下主文件中有被定义")
        if len(all_magic_comments['root']) == 1: # 当前目录下存在多个主文件，且只有一个存在 % TEX root 魔法注释
            logger.info(f"魔法注释 % !TEX root 只存在于 {all_magic_comments['root'][0][0]}.tex 中")
            check_file = MFJ.check_project_name(main_file_in_root, all_magic_comments['root'][0][1]) # 检查 magic comments 中指定的 root 文件名是否正确
            if f"{all_magic_comments['root'][0][0]}" == f"{check_file}": # 如果 magic comments 中指定的 root 文件名与当前文件名相同
                project_name = check_file # 使用魔法注释 % !TEX root 指定的文件作为主文件
                print(f"通过魔法注释 % !TEX root 指定待编译主文件为 [bold cyan]{project_name}.tex[/bold cyan]")
            else: # 如果 magic comments 中指定的 root 文件名与当前文件名不同
                logger.warning(f"魔法注释 % !TEX root 指定的文件名 [bold cyan]{check_file}.tex[/bold cyan] 与当前文件名 [bold cyan]{all_magic_comments['root'][0][0]}.tex[/bold cyan] 不同，无法确定主文件")
        if len(all_magic_comments['root']) > 1: # 当前目录下存在多个主文件，且多个 tex 文件中同时存在 % TEX root 魔法注释
            logger.warning("魔法注释 % !TEX root 在当前根目录下的多个主文件中同时被定义，无法根据魔法注释确定待编译主文件") 

    if not project_name: # 如果当前根目录下存在多个主文件，且不存在 % TEX root 魔法注释，并且待编译主文件还没有找到
        logger.info("无法根据魔法注释判断出待编译主文件，尝试根据默认主文件名指定待编译主文件")
        for file in main_file_in_root:
            if file == "main": # 如果存在 main.tex 文件
                project_name = file # 使用 main.tex 文件作为待编译主文件名
                print(f"通过默认文件名 \"main.tex\" 指定待编译主文件为：[bold cyan]{project_name}.tex[/bold cyan]")
        if not project_name: # 如果不存在 main.tex 文件
            logger.info("当前根目录下不存在名为 \"main.tex\" 的文件")

    if not project_name: # 其他情况
        logger.error("无法进行编译，当前根目录下存在多个主文件：" + ", ".join(main_file_in_root))
        logger.warning("请修改待编译主文件名为默认文件名 \"main.tex\" 或在文件中加入魔法注释 \"% !TEX root = <待编译主文件名>\" 或在终端输入 \"pytexmk <待编译主文件名>\" 进行编译，或删除当前根目录下多余的 tex 文件")
        logger.warning(f"当前根目录是：{current_path}")
        print('[bold red]正在退出 PyTeXMK ...[/bold red]')
        sys.exit(1)
    
    project_name = MFJ.check_project_name(main_file_in_root, project_name) # 检查 project_name 是否正确

    if all_magic_comments: # 如果存在魔法注释
        for key, values in all_magic_comments.items():  # 遍历所有提取的魔法注释
            for value in values:  # 遍历魔法注释中所有值
                if value[0] == project_name:  # 如果是project_name对应的文件
                    magic_comments[key] = value[1]  # 存储魔法注释
                    logger.info(f"已从 {value[0]}.tex 中提取魔法注释 % !TEX {key} = {value[1]}")
    

    # --------------------------------------------------------------------------------
    # 编译类型判断
    # -------------------------------------------------------------------------------- 
    if args.XeLaTeX:
        compiler_engine = "XeLaTeX"
    elif args.PdfLaTeX:
        compiler_engine = "PdfLaTeX"
    elif args.LuaLaTeX:
        compiler_engine = "LuaLaTeX"
    elif magic_comments.get('program'): # 如果存在 magic comments 且 program 存在
        compiler_engine = magic_comments['program'] # 使用 magic comments 中的 program 作为编译器
        print(f"通过魔法注释设置编译器为 [bold cyan]{compiler_engine}[/bold cyan]")

    # --------------------------------------------------------------------------------
    # 输出文件路径判断
    # --------------------------------------------------------------------------------
    if magic_comments.get('outdir'): # 如果存在 magic comments 且 outdir 存在
        outdir = magic_comments['outdir'] # 使用 magic comments 中的 outdir 作为输出目录
        print(f"通过魔法注释找到输出目录为 [bold cyan]{outdir}[/bold cyan]")
    if magic_comments.get('auxdir'): # 如果存在 magic comments 且 auxdir 存在
        auxdir = magic_comments['auxdir'] # 使用 magic comments 中的 auxdir 作为辅助文件目录
        print(f"通过魔法注释找到辅助文件目录为 [bold cyan]{auxdir}[/bold cyan]")

    # --------------------------------------------------------------------------------
    # 编译程序运行
    # --------------------------------------------------------------------------------
    suffixes_out = [".pdf", ".synctex.gz"]
    suffixes_aux = [".log", ".blg", ".ilg",  # 日志文件
                    ".aux", ".bbl", ".xml",  # 参考文献辅助文件
                    ".toc", ".lof", ".lot",  # 目录辅助文件
                    ".out", ".bcf",
                    ".idx", ".ind", ".nlo", ".nls", ".ist", ".glo", ".gls",  # 索引辅助文件
                    ".bak", ".spl",
                    ".ent-x", ".tmp", ".ltx", ".los", ".lol", ".loc", ".listing", ".gz",
                    ".userbak", ".nav", ".snm", ".vrb", ".fls", ".xdv", ".fdb_latexmk", ".run.xml"]

    """markdown
    | 后缀        | 功能和作用                                                     | 由来                                                         |
    |-------------|----------------------------------------------------------------|--------------------------------------------------------------|
    | .pdf        | 生成的PDF文档                                                  | Portable Document Format，便携式文档格式                     |
    | .synctex.gz | 用于同步TeX源文件和生成的PDF文件，便于编辑和查看                | SyncTeX，一种用于TeX和PDF之间同步的技术，.gz表示压缩格式      |
    | .log        | 编译日志文件，记录编译过程中的详细信息                           | Log file，记录程序运行时的日志信息                            |
    | .blg        | BibTeX日志文件，记录BibTeX处理参考文献时的信息                   | BibTeX Log file                                               |
    | .ilg        | MakeIndex日志文件，记录MakeIndex处理索引时的信息                 | MakeIndex Log file                                            |
    | .aux        | 辅助文件，用于存储交叉引用、标签等信息                           | Auxiliary file                                                |
    | .bbl        | BibTeX生成的参考文献文件，包含格式化的参考文献列表               | BibTeX Bibliography file                                     |
    | .xml        | 用于存储XML格式的数据，常用于BibTeX的输入输出                    | eXtensible Markup Language，可扩展标记语言                    |
    | .toc        | 目录文件，存储文档的章节结构信息                                 | Table of Contents file                                        |
    | .lof        | 图目录文件，存储文档中的图的列表信息                             | List of Figures file                                          |
    | .lot        | 表目录文件，存储文档中的表的列表信息                             | List of Tables file                                           |
    | .out        | 输出文件，通常由LaTeX生成，用于存储一些临时输出信息              | Output file                                                   |
    | .bcf        | Biber配置文件，用于存储Biber处理参考文献时的配置信息             | Biber Configuration File                                      |
    | .idx        | 索引文件，存储文档中的索引项信息                                 | Index file                                                    |
    | .ind        | MakeIndex生成的索引文件，包含格式化的索引列表                    | Index file generated by MakeIndex                             |
    | .nlo        | nomencl生成的术语列表文件                                        | nomencl List of Terms file                                    |
    | .nls        | nomencl生成的术语排序文件                                        | nomencl List of Terms Sorted file                             |
    | .ist        | MakeIndex样式文件，定义索引的格式                                | Index Style file                                              |
    | .glo        | glossary文件，存储文档中的术语信息                                | Glossary file                                                 |
    | .gls        | MakeIndex生成的glossary文件，包含格式化的术语列表                 | Glossary file generated by MakeIndex                          |
    | .bak        | 备份文件，通常是源文件的备份                                     | Backup file                                                   |
    | .spl        | 拼写检查文件，存储拼写检查的信息                                  | Spell Check file                                              |
    | .ent-x      | 实体扩展文件，用于存储XML实体扩展信息                             | Entity eXtension file                                         |
    | .tmp        | 临时文件，存储临时数据                                           | Temporary file                                                |
    | .ltx        | LaTeX源文件，存储LaTeX代码                                        | LaTeX source file                                             |
    | .los        | 图标目录文件，存储文档中的图标列表信息                            | List of Symbols file                                          |
    | .lol        | 行目录文件，存储文档中的行列表信息                                | List of Lines file                                            |
    | .loc        | 位置文件，存储位置信息                                            | Location file                                                 |
    | .listing    | 代码列表文件，存储文档中的代码列表信息                            | Listing file                                                  |
    | .gz         | 压缩文件，通常是.synctex文件的压缩格式                            | Gzip compressed file                                          |
    | .userbak    | 用户备份文件，通常是用户手动创建的备份文件                        | User Backup file                                              |
    | .nav        | Beamer导航文件，用于存储Beamer幻灯片的导航信息                    | Beamer Navigation file                                        |
    | .snm        | Beamer会话文件，用于存储Beamer幻灯片的会话信息                    | Beamer Session file                                           |
    | .vrb        | Beamer注释文件，用于存储Beamer幻灯片的注释信息                    | Beamer Verbatim file                                          |
    | .fls        | LaTeX外部引用文件，记录LaTeX编译过程中引用的外部文件              | LaTeX File List file                                          |
    | .xdv        | XeLaTeX生成的 DVI 文件，用于存储XeLaTeX编译结果                   | XeLaTeX DVI file                                              |
    | .fdb_latexmk| LaTeXmk数据库文件，用于存储LaTeXmk编译过程中的数据库信息          | LaTeXmk File Database file                                     |
    | .run.xml    | Biber运行时配置文件，用于存储Biber运行时的配置信息                | Biber Run XML file                                             |
    """
    out_files = [f"{project_name}{suffix}" for suffix in suffixes_out]
    aux_files = [f"{project_name}{suffix}" for suffix in suffixes_aux]
    aux_regex_files = [f".*\\{suffix}" for suffix in suffixes_aux]

    if project_name: # 如果存在 project_name 
        if args.clean:
            MRC.remove_files(aux_files, auxdir)
            MRC.remove_files(aux_files, '.')
            print('[bold green]已完成清除所有主文件的辅助文的件指令')
        elif args.Clean:
            MRC.remove_files(aux_files, auxdir)
            MRC.remove_files(aux_files, '.')
            MRC.remove_files(out_files, outdir)
            print('[bold green]已完成清除所有主文件的辅助文件和输出文件的指令')
        elif args.clean_any:
            MRC.remove_files(aux_regex_files, '.')
            print('[bold green]已完成清除所有带辅助文件后缀的文件的指令')
        elif args.Clean_any:
            MRC.remove_files(aux_regex_files, '.')
            MRC.remove_files(out_files, outdir)
            print('[bold green]已完成清除所有带辅助文件后缀的文件和主文件输出文件的指令')
        elif args.pdf_repair:
            MRC.pdf_repair(project_name, '.', outdir)
        else:
            RUN(start_time, compiler_engine, project_name, out_files, aux_files, outdir, auxdir, args.unquiet)
    checker = UpdateChecker()
    checker.check_for_updates()

if __name__ == "__main__":
    main()
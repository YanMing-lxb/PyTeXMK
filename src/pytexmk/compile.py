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
Date         : 2024-02-29 15:43:26 +0800
LastEditTime : 2025-01-29 22:03:15 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /PyTeXMK/src/pytexmk/compile_module.py
Description  : 
 -----------------------------------------------------------------------
'''
# -*- coding: utf-8 -*-
import re
import logging
import subprocess
from pathlib import Path  # 导入Path模块
from rich import console  # 导入rich库的console模块
from itertools import chain  # 导入chain,用于将多个迭代器连接成一个迭代器
from collections import defaultdict  # 导入defaultdict,用于创建带有默认值的字典

from pytexmk.language import set_language
from pytexmk.additional import MoveRemoveOperation, exit_pytexmk

console = console.Console()

_ = set_language('compile')


# 定义正则表达式模式
BIBER_PATTERN = re.compile(r'\\abx@aux@refcontext')  # 匹配 biber 命令
BIBTEX_PATTERN = re.compile(r'\\bibdata')  # 匹配 bibtex 命令

BIBER_BIB_PATTERN = re.compile(r'<bcf:datasource[^>]*>\s*(.*?)\s*</bcf:datasource>')  # 匹配<bcf:datasource>标签中的内容
BIBTEX_BIB_PATTERN = re.compile(r'\\bibdata\{(.*)\}')  # 匹配\bibdata{}命令

BIBER_CITE_PATTERN = re.compile(r'\\abx@aux@cite{.*?}\{(.*)\}')  # 匹配\abx@aux@cite{任意字符}{}命令
BIBTEX_CITE_PATTERN = re.compile(r'\\citation\{(.*)\}')  # 匹配\citation{}命令

BIBCITE_PATTERN = re.compile(r'\\bibcite\{(.*)\}\{(.*)\}')  # 匹配\bibcite{}命令
BIBENTRY_PATTERN = re.compile(r'@.*\{(.*),\s')  # 匹配@entry{}命令

ERROR_PATTTERN = re.compile(r'(?:^! (.*\nl\..*)$)|(?:^! (.*)$)|'
                            '(No pages of output.)', re.M)  # 匹配错误信息
LATEX_RERUN_PATTERNS = [re.compile(pattr) for pattr in
                        [r'LaTeX Warning: Reference .* undefined',
                         r'LaTeX Warning: There were undefined references\.',
                         r'LaTeX Warning: Label\(s\) may have changed\.',
                         r'No file .*(\.toc|\.lof)\.']]  # 匹配需要重新运行的LaTeX警告

class CompileLaTeX(object):

    def __init__(self, project_name, compiled_program, out_files, aux_files, outdir, auxdir, non_quiet):
        """
        初始化 CompileModel 类实例.

        参数:
        - project_name (str): 项目的名称.
        - compiled_program (str): 编译引擎的名称.
        - LaTeXDiff (bool): 是否使用LaTeXDiff.
        - out_files (list): 输出文件列表.
        - aux_files (list): 辅助文件列表.
        - outdir (str): 输出文件的目录路径.
        - auxdir (str): 辅助文件的目录路径.
        - non_quiet (bool): 是否非静默模式运行.

        行为:
        - 初始化输出文件名为空字符串,调用_setup_logger方法设置日志记录器,
        - 初始化编译引擎、项目名称、输出文件、辅助文件、辅助目录、输出目录、静默模式等属性,
        - 初始化参考文献文件路径为空字符串,初始化 MoveRemoveOperationtion 类对象.
        """
        self.out = ''  # 初始化输出文件名为空字符串
        self.logger = logging.getLogger(__name__)  # 调用_setup_logger方法设置日志记录器

        self.project_name = project_name
        self.compiled_program = compiled_program
        self.out_files = out_files
        self.aux_files = aux_files
        self.auxdir = auxdir
        self.outdir = outdir
        self.non_quiet = non_quiet 
        self.bib_file = ''  # 初始化参考文献文件路径为空字符串

        self.MRO = MoveRemoveOperation()  # 初始化 MoveRemoveOperation 类对象

    # --------------------------------------------------------------------------------
    # 定义日志检查函数
    # --------------------------------------------------------------------------------
    def check_errors(self, log_content):
        """
        检查编译日志中的错误.

        参数:
        - log_content (str): 包含编译日志内容的字符串.

        行为:
        1. 使用正则表达式模式查找所有错误.
        2. 如果有错误,记录错误信息并提示查看日志文件以获取详细信息.
        3. 移动辅助文件和输出文件到指定目录.
        4. 打印退出信息并退出程序.

        错误处理:
        - 如果发现错误,程序将记录错误信息并退出.
        """
        self.out = log_content
        errors = ERROR_PATTTERN.findall(self.out)  # 使用正则表达式模式查找所有错误
        # "errors"是一个元组列表
        if errors:  # 如果有错误
            self.logger.error(_('编译过程发生错误: '))  # 记录错误信息

            self.logger.error('\n'.join(
                [error.replace('\r', '').strip() for error
                    in chain(*errors) if error.strip()]
            ))  # 将错误信息逐行记录,去除多余的空格和换行符

            self.logger.error(_("请查看日志文件以获取详细信息: ") + f'{self.auxdir}{self.project_name}.log')  # 提示查看日志文件以获取详细信息
            self.MRO.move_specific_files(self.aux_files, '.', self.auxdir)
            self.MRO.move_specific_files(self.out_files, '.', self.outdir)
            exit_pytexmk()
    
    # --------------------------------------------------------------------------------
    # 定义信息获取函数
    # --------------------------------------------------------------------------------
    def prepare_LaTeX_output_files(self):
        """
        准备LaTeX输出文件的相关信息.

        返回值:
        - cite_counter: 引用计数器,包含引用信息的字典.
        - toc_file: toc文件内容,字符串类型.
        - index_aux_content_dict_old: 词汇表文件内容,字典类型.

        行为说明:
        - 检查是否存在项目名称对应的.aux文件.如果存在,生成引用计数器并读取词汇表内容.
        - 如果不存在.aux文件,初始化引用计数器为默认值,词汇表内容为空字典.
        - 检查是否存在.toc文件.如果存在,读取.toc文件内容.
        - 如果不存在.toc文件,初始化toc_file为空字符串.
        - 返回引用计数器、toc文件内容和词汇表文件内容.
        """
        # 使用Path对象创建项目名称对应的.aux文件路径
        aux_file_path = Path(f'{self.project_name}.aux')
        # 检查是否存在项目名称对应的.aux文件
        if aux_file_path.exists():
            # 生成引用计数器
            cite_counter = self._generate_citation_counter()
            # 读取词汇表
            index_aux_content_dict_old = self._index_aux_content_get()
        else:
            # 如果不存在.aux文件,初始化引用计数器为默认值
            cite_counter = {f'{self.project_name}.aux' : defaultdict(int)}
            index_aux_content_dict_old = dict()
        # 使用Path对象创建项目名称对应的.toc文件路径
        toc_file_path = Path(f'{self.project_name}.toc')
        # 检查是否存在.toc文件
        if toc_file_path.exists():
            # 读取.toc文件内容
            with open(toc_file_path, 'r', encoding='utf-8') as fobj:
                toc_file = fobj.read()
        else:
            # 如果不存在.toc文件,初始化toc_file为空字符串
            toc_file = ''

        # 返回引用计数器、toc文件内容和词汇表文件内容
        return cite_counter, toc_file, index_aux_content_dict_old
    
    # --------------------------------------------------------------------------------
    # 定义参考文献引用次数获取函数
    # --------------------------------------------------------------------------------
    def _generate_citation_counter(self):
        """
        生成并返回一个字典,该字典包含每个aux文件的引用数量.

        返回值:
        - cite_counter: 一个字典,键为aux文件名,值为该文件中的引用文献key和引用数量组成的字典.

        行为说明:
        - 初始化一个空的字典,用于存储每个aux文件的引用数量.
        - 构造主aux文件的文件名,格式为项目名加上.aux后缀.
        - 打开主aux文件并读取其内容.
        - 计算主aux文件中的引用数量,并将其存储在cite_counter字典中.
        - 使用正则表达式查找所有包含的aux文件,并尝试计算每个aux文件中的引用数量.
        - 如果某个aux文件不存在或无法读取,则跳过该文件.
        - 返回包含所有aux文件引用数量的字典.
        """
        cite_counter = dict()
        file_name = f'{self.project_name}.aux'
        with open(file_name, 'r', encoding='utf-8') as fobj:
            main_aux_content = fobj.read()
        cite_counter[file_name] = _count_citations(file_name)
    
        for match in re.finditer(r'\\@input\{(.*.aux)\}', main_aux_content):
            file_name = match.groups()[0]
            try:
                counter = _count_citations(file_name)
            except IOError:
                self.logger.info(_("文件不存在或无法读取,跳过文件: %(args)s") % {'args': file_name})
                pass
            else:
                cite_counter[file_name] = counter
    
        return cite_counter

    # --------------------------------------------------------------------------------
    # 定义旧的符号索引辅助文件内容获取函数
    # --------------------------------------------------------------------------------
    def _index_aux_content_get(self): 
        """
        获取项目中所有索引辅助文件的内容,并将其存储在一个字典中.

        返回:
        - index_aux_content_dict_old (dict): 包含所有辅助文件内容的字典.

        行为逻辑说明:
        1. 构造主aux文件的文件名,格式为项目名加上.aux后缀.
        2. 定义一个字典,用于存储旧的索引辅助文件内容.
        3. 检查主aux文件是否存在.
        4. 如果主aux文件存在,则进一步检查并获取glossaries、nomencl和makeidx宏包的辅助文件内容.
        5. 对于每个宏包,检查其对应的输入和输出扩展文件是否同时存在,如果存在则读取其内容并存储在字典中.
        6. 如果没有找到主aux文件,则记录警告信息.
        7. 返回存储了所有辅助文件内容的字典.
        """
        file_name = Path(f'{self.project_name}.aux')  # 使用pathlib构造主aux文件的文件名,格式为项目名加上.aux后缀
        index_aux_content_dict_old = dict()  # 定义一个字典,用于存储旧的索引辅助文件内容

        # 读取主aux文件
        if file_name.exists():  # 使用pathlib检查主aux文件是否存在
            # 判断并获取 glossaries 宏包的辅助文件内容
            if any(Path(f"{self.project_name}{ext}").exists() for ext in [".glo", ".acn", ".slo"]):
                with open(file_name, 'r', encoding='utf-8') as fobj:
                    main_aux = fobj.read()
                pattern = r'\\@newglossary\{(.*)\}\{.*\}\{(.*)\}\{(.*)\}'  # 定义正则表达式模式,用于匹配词汇表条目
                for match in re.finditer(pattern, main_aux):  # 使用正则表达式查找所有匹配的词汇表条目
                    name, ext_o, ext_i = match.groups()  # 提取匹配的组,分别是词汇表名称、输出扩展和输入扩展
                    if Path(f"{self.project_name}{ext_i}").exists() and Path(f"{self.project_name}{ext_o}").exists():  # 使用pathlib判断输出和输入扩展文件是否同时存在
                        with open(Path(f"{self.project_name}{ext_o}"), 'r', encoding='utf-8') as fobj:
                            index_ext_i_content = fobj.read()
                        index_aux_content_dict_old[f'{self.project_name}.{ext_i}'] = index_ext_i_content 
            # 判断并获取 nomencl 宏包的辅助文件内容
            if Path(f"{self.project_name}.nlo").exists():
                if Path(f"{self.project_name}.nlo").exists() and Path(f"{self.project_name}.nls").exists():  # 使用pathlib判断输出和输入扩展文件是否同时存在
                    with open(Path(f"{self.project_name}.nlo"), 'r', encoding='utf-8') as fobj:
                        index_ext_i_content = fobj.read()
                    index_aux_content_dict_old[f'{self.project_name}.nlo'] = index_ext_i_content

            # 判断并获取 makeidx 宏包的辅助文件内容
            if Path(f"{self.project_name}.idx").exists():
                if Path(f"{self.project_name}.idx").exists() and Path(f"{self.project_name}.ind").exists():  # 使用pathlib判断输出和输入扩展文件是否同时存在
                    with open(Path(f"{self.project_name}.idx"), 'r', encoding='utf-8') as fobj:
                        index_ext_i_content = fobj.read()
                    index_aux_content_dict_old[f'{self.project_name}.{ext_i}'] = index_ext_i_content
        else:
            self.logger.warning(_("未找到辅助文件: ") + f"{self.project_name}.aux")

        return index_aux_content_dict_old
    
    # --------------------------------------------------------------------------------
    # 定义目录更新判断函数
    # --------------------------------------------------------------------------------
    def toc_changed_judgment(self, toc_file):
        """
        判断toc文件内容是否发生变化.

        参数:
        - toc_file: 传入的toc文件内容,用于与当前项目中的toc文件内容进行比较.

        行为逻辑:
        1. 生成toc文件的完整路径.
        2. 检查toc文件是否存在.
        3. 如果存在,打开toc文件并读取其内容.
        4. 比较toc文件内容与传入的toc_file内容.
        5. 如果内容不同,返回True表示toc文件已变化.
        """
        file_name = Path(self.project_name).with_suffix('.toc')  # 使用pathlib生成toc文件的完整路径
        if file_name.exists():  # 使用pathlib检查toc文件是否存在
            with open(file_name, 'r', encoding='utf-8') as fobj:  # 打开toc文件
                if fobj.read() != toc_file:  # 比较toc文件内容与传入的toc_file内容
                    return True  # 如果内容不同,返回True表示toc文件已变化

    # --------------------------------------------------------------------------------
    # 定义 TeX 编译函数
    # --------------------------------------------------------------------------------
    def compile_tex(self):
        """
        编译 LaTeX 文档的方法.

        参数:
        - self: 当前对象实例,包含编译所需的配置和状态信息.

        行为逻辑:
        1. 根据编译引擎和其他配置选项构建编译命令.
        2. 如果编译引擎是 'XeLaTeX',则添加 '-no-pdf' 选项.
        3. 根据是否静默编译,添加 '-interaction=batchmode' 或 '-interaction=nonstopmode' 选项.
        4. 打印将要运行的命令.
        5. 使用 subprocess.run 执行编译命令.
        6. 如果编译失败,记录错误信息,移动辅助文件和输出文件到指定目录,并退出程序.
        """
        
        options = [self.compiled_program.lower(), "-shell-escape", "-file-line-error", "-halt-on-error", "-synctex=1", f'{self.project_name}.tex']
        if self.compiled_program == 'XeLaTeX':
            options.insert(5, "-no-pdf")
        if self.non_quiet:
            options.insert(4, "-interaction=nonstopmode") # 非静默编译
        else:
            options.insert(4, "-interaction=batchmode") # 静默编译
        console.print(_("[bold]运行命令: [/bold]") + f"[cyan]{' '.join(options)}\n")

        try:
            subprocess.run(options, check=True, text=True, capture_output=False)
        except Exception as e:
            self.logger.error(_("%(args)s 编译失败,请查看日志文件以获取详细信息: ") %{'args': self.compiled_program} + f"{self.auxdir}{self.project_name}.log\n{e}")
            self.MRO.move_specific_files(self.aux_files, '.', self.auxdir)
            self.MRO.move_specific_files(self.out_files, '.', self.outdir)
            exit_pytexmk()

    # --------------------------------------------------------------------------------
    # 定义参考文献判断函数
    # --------------------------------------------------------------------------------
    def bib_judgment(self, old_cite_counter):
        """
        判断是否需要使用biber或bibtex进行参考文献编译,并返回相应的编译引擎、LaTeX 额外编译次数、编译信息和目标名称.
        
        参数:
        - old_cite_counter (int): 之前的引用计数.
        
        返回:
        tuple: 包含以下四个元素的元组: 
            - bib_engine (str): 参考文献编译引擎,可能为'biber'或'bibtex',如果不需要编译则为None.
            - Latex_compilation_times (int): 需要额外进行的LaTeX编译次数.
            - print_bib (str): 编译信息,描述编译过程中遇到的情况.
            - name_target (str): 编译目标名称,描述编译的具体目标.
        
        行为逻辑:
        1. 检查项目目录下是否存在aux文件,如果不存在则记录警告并返回.
        2. 读取aux文件内容,检查是否存在biber或bibtex的特征命令.
        3. 如果存在biber特征命令,则进一步检查bcf文件中是否存在bib文件名,并设置相应的编译引擎和 LaTeX 额外编译次数.
        4. 如果存在bibtex特征命令,则直接从aux文件中提取bib文件名,并设置相应的编译引擎和 LaTeX 额外编译次数.
        5. 检查bib文件是否存在,如果不存在则更新编译信息.
        6. 获取新的引用计数,如果引用计数没有变化,则更新编译信息并设置 LaTeX 额外编译次数为0.
        7. 检查LaTeX输出中是否有bbl文件缺失或引用未定义的提示,如果有则更新编译信息并设置 LaTeX 额外编译次数.
        8. 如果没有找到biber或bibtex特征命令,但存在bibcite命令,则更新编译信息为使用thebibliography环境排版,设置 LaTeX 额外编译次数.
        9. 如果没有引用参考文献或编译工具不属于bibtex或biber,则更新编译信息.
        10. 返回编译引擎、 LaTeX 额外编译次数、编译信息和目标名称.
        """
        bib_engine = None  # 初始化参考文献编译引擎为None
        name_target = None  # 初始化目标名称为None
        Latex_compilation_times = 0  # 初始化LaTeX编译次数为0
        aux_file_path = Path(f"{self.project_name}.aux")  # 使用pathlib创建aux文件路径
        if aux_file_path.exists():  # 检查aux文件是否存在
            with aux_file_path.open('r', encoding='utf-8') as fobj:  # 打开aux文件
                aux_content = fobj.read()  # 读取aux文件内容
            match_biber = BIBER_PATTERN.search(aux_content)  # 检索aux辅助文件中是否存在biber特征命令
            match_bibtex = BIBTEX_PATTERN.search(aux_content)  # 检索aux辅助文件中是否存在bibtex特征命令
            if match_biber or match_bibtex:  # 判断是否使用biber或bibtex编译
                if match_biber:  # 判断应使用 biber 引擎编译
                    bcf_file_path = Path(f"{self.project_name}.bcf")  # 使用pathlib创建bcf文件路径
                    with bcf_file_path.open('r', encoding='utf-8') as fobj:  # 打开bcf文件
                        match_biber_bib = BIBER_BIB_PATTERN.search(fobj.read())  # 检索bcf文件中是否存在bib文件名
                    if not match_biber_bib:
                        print_bib = _("未设置参考文献数据库文件: ") + self.bib_file
                    else:
                        self.bib_file = match_biber_bib.group(1)  # 获取bib文件名
                        bib_engine = 'biber'  # 设置参考文献编译引擎为biber
                        Latex_compilation_times = 2  # LaTeX 额外编译次数 
                
                elif match_bibtex:  # 判断应使用 bibtex 引擎编译
                    match_bibtex_bib = BIBTEX_BIB_PATTERN.search(aux_content)  # 检索aux文件中是否存在bib文件名
                    if not match_bibtex_bib:
                        print_bib =  _("未设置参考文献数据库文件: ") + self.bib_file
                    else:
                        self.bib_file = match_bibtex_bib.group(1)  # 获取bib文件名
                        bib_engine = 'bibtex'  # 设置参考文献编译引擎为bibtex
                        Latex_compilation_times = 2  # LaTeX 额外编译次数 

                print_bib = bib_engine + _("编译参考文献")
                name_target = bib_engine

                bib_file_path = Path(self.bib_file)  # 使用pathlib创建bib文件路径
                if not bib_file_path.exists():  # 检查bib文件是否存在
                    print_bib = _("未找到参考文献数据库文件: ") + self.bib_file
                    Latex_compilation_times = 2
                
                new_cite_counter = self._generate_citation_counter()  # 获取新的引用数目
                if old_cite_counter == new_cite_counter:  # 如果引用数量没有发生变化
                    print_bib = _("参考文献引用数量没有变化")
                    Latex_compilation_times = 0

                if (re.search(f'No file {self.project_name}.bbl.', self.out) or  # 检查LaTeX输出中是否有bbl文件缺失的提示
                    re.search('LaTeX Warning: Citation .* undefined', self.out)):  # 检查LaTeX输出中是否有引用未定义的提示
                    print_bib = _("LaTeX 编译日志中存在 bbl 文件缺失或引用未定义的提示")
                    Latex_compilation_times = 2

            elif re.search(r'\\bibcite', aux_content):
                print_bib = _("thebibliography 环境实现排版")
                Latex_compilation_times = 1

            else:
                print_bib = _("没有引用参考文献或编译工具不属于 bibtex 或 biber")
        else:
            self.logger.warning(_("未找到辅助文件: ") + f"{self.project_name}.aux")
        return bib_engine, Latex_compilation_times, print_bib, name_target  # 返回参考文献编译引擎、LaTeX编译次数、打印信息和目标名称
    
    # --------------------------------------------------------------------------------
    # 定义参考文献编译函数
    # --------------------------------------------------------------------------------
    def compile_bib(self, bib_engine):
        """
        使用指定的参考文献管理引擎编译项目中的参考文献.

        参数:
        - bib_engine (str): 参考文献管理引擎的名称,例如 'bibtex' 或 'biber'.

        行为逻辑:
        1. 构建运行参考文献管理引擎的命令行选项.
        2. 如果设置了静默编译且引擎为 'biber',则在选项中添加 '-quiet' 参数.
        3. 在控制台中打印将要运行的命令.
        4. 尝试运行构建的命令.
        5. 如果命令运行失败,记录错误信息,移动辅助文件和输出文件到指定目录,并退出程序.
        """
        # self.logger.info('Running bibtex...')  # 记录日志,显示正在运行bibtex
        options = [bib_engine, self.project_name]

        if not self.non_quiet and bib_engine == 'biber':
            options.insert(1, "-quiet") # 静默编译
                
        console.print(_("[bold]运行命令: [/bold]") + f"[cyan]{' '.join(options)}\n")
        try:
            subprocess.run(options, check=True, text=True, capture_output=False)
        except Exception as e:
            self.logger.error(_("%(args)s 编译失败,请查看日志文件以获取详细信息: ") % {'args': bib_engine} + f"{self.auxdir}{self.project_name}.log\n{e}")
            self.MRO.move_specific_files(self.aux_files, '.', self.auxdir)
            self.MRO.move_specific_files(self.out_files, '.', self.outdir)
            exit_pytexmk()

    # --------------------------------------------------------------------------------
    # 定义索引更新判断函数
    # --------------------------------------------------------------------------------
    def _index_changed_judgment(self, index_aux_content_dict_old, index_aux_infile, index_aux_outfile):
        """
        判断是否需要重新生成索引文件.
        
        参数:
        - index_aux_content_dict_old: 旧的索引文件内容字典
        - index_aux_infile: 输入的索引文件路径
        - index_aux_outfile: 输出的索引文件路径

        返回:
        - print_index: 打印的索引信息
        - make_index: 是否需要重新生成索引的标志
        
        行为逻辑:
        1. 初始化是否需要重新生成索引的标志.
        2. 检查输出中是否包含"没有该输入文件"的信息,如果包含,则需要重新生成索引.
        3. 判断输出和输入扩展文件是否同时存在,如果同时存在,则比较词汇表文件内容与记录的内容,如果不一致,则需要重新生成词汇表.
        4. 如果输入和输出文件没有同时存在,则需要重新生成索引.
        """
        make_index = False  # 初始化是否需要重新生成索引的标志
        if re.search(f'No file {index_aux_infile}.', self.out):  # 检查输出中是否包含"没有该输入文件"的信息
            print_index = _('重新编译索引,因日志文件提示没有输入文件')
            make_index = True  # 如果包含,则需要重新生成词汇表
        elif Path(index_aux_infile).exists() and Path(index_aux_outfile).exists():  # 使用pathlib判断输出和输入扩展文件是否同时存在
            with open(index_aux_infile, 'r', encoding='utf-8') as fobj:  # 打开输入文件
                file_content = fobj.read()  # 读取文件内容并存储在变量中
            if file_content is not None:
                if str(index_aux_content_dict_old[index_aux_infile]) != file_content:  # 比较词汇表文件内容与记录的内容
                    print_index = _('重新编译索引,因词汇表文件内容发生变化')
                    make_index = True  # 如果不一致,则需要重新生成词汇表
                else:
                    print_index = _('无需编译索引,因词汇表文件内容没有变化')
            else:
                print_index = _('无需编译索引,因没有索引内容')
        else:
            make_index = True
            print_index = _("重新编译索引,因以下索引辅助文件之一存在缺失: ") + f'{index_aux_infile}, {index_aux_outfile}'
        return print_index, make_index
    
    # --------------------------------------------------------------------------------
    # 定义索引编译函数
    # --------------------------------------------------------------------------------
    def index_judgment(self, index_aux_content_dict_old): 
        """
        判断并生成需要运行索引的命令列表.
        
        参数:
        - index_aux_content_dict_old: 旧的索引辅助内容字典,用于判断索引文件是否需要重新生成.
        
        返回:
        - print_index: 打印的索引信息,用于提示用户当前使用的索引宏包或状态.
        - run_index_list_cmd: 需要运行的索引命令列表,每个元素是一个包含命令描述和具体命令的列表.
        
        行为逻辑:
        1. 构造主aux文件的文件名.
        2. 初始化需要运行索引的命令列表.
        3. 判断并获取 glossaries 宏包的辅助文件名称,如果存在则读取主aux文件,使用正则表达式匹配词汇表条目,并根据匹配结果生成相应的索引命令.
        4. 判断并获取 nomencl 宏包的辅助文件名称,如果存在则生成相应的索引命令.
        5. 判断并获取 makeidx 宏包的辅助文件名称,如果存在则生成相应的索引命令.
        6. 如果以上宏包都不存在,则提示用户采用其他宏包制作索引.
        7. 返回打印的索引信息和需要运行的索引命令列表.
        """
        file_name = Path(f'{self.project_name}.aux') # 构造主aux文件的文件名,格式为项目名加上.aux后缀
        run_index_list_cmd = [] # 初始化需要运行 index 的命令列表
        # 判断并获取 glossaries 宏包的辅助文件名称
        if any(Path(f"{self.project_name}{ext}").exists() for ext in [".glo", ".acn", ".slo"]):
            with open(file_name, 'r', encoding='utf-8') as fobj:
                main_aux = fobj.read()
            pattern = r'\\@newglossary\{(.*)\}\{.*\}\{(.*)\}\{(.*)\}'  # 定义正则表达式模式,用于匹配词汇表条目
            for match in re.finditer(pattern, main_aux):  # 使用正则表达式查找所有匹配的词汇表条目
                name, ext_o, ext_i = match.groups()  # 提取匹配的组,分别是词汇表名称、输出扩展和输入扩展
                print_index, make_index = self._index_changed_judgment(index_aux_content_dict_old, f"{self.project_name}{ext_i}", f"{self.project_name}{ext_o}")
                if make_index:
                    run_index_list_cmd.append([f'glossaries {name}', f"makeindex -s {self.project_name}.ist -o {self.project_name}{ext_o} {self.project_name}{ext_i}"])
        # 判断并获取 nomencl 宏包的辅助文件名称
        elif Path(f"{self.project_name}.nlo").exists():
            print_index, make_index = self._index_changed_judgment(index_aux_content_dict_old, f"{self.project_name}.nlo", f"{self.project_name}.nls")
            if make_index:
                run_index_list_cmd.append(['nomencl', f"makeindex -s nomencl.ist -o {self.project_name}.nls {self.project_name}.nlo"])

        # 判断并获取 makeidx 宏包的辅助文件名称
        elif Path(f"{self.project_name}.idx").exists():
            print_index, make_index = self._index_changed_judgment(index_aux_content_dict_old, f"{self.project_name}.idx", f"{self.project_name}.ind")
            if make_index:
                run_index_list_cmd.append(['makeidx', f"makeindex {self.project_name}.idx"])
        else:
            print_index = _("使用 glossaries、nomencl 和 makeidx 以外宏包或未设置索引,因此不编译索引")
        return print_index, run_index_list_cmd

    # --------------------------------------------------------------------------------
    # 定义索引编译函数
    # --------------------------------------------------------------------------------
    def compile_index(self, cmd): 
        """
        运行 makeindex 命令以生成索引文件.

        参数:
        - cmd (list): 包含两个元素的列表,第一个元素是命令名称,第二个元素是命令字符串.

        返回:
        - str: 命令名称,格式为 "命令名称 宏包".

        行为逻辑:
        1. 打印将要运行的命令.
        2. 尝试运行命令,如果成功则返回命令名称.
        3. 如果命令运行失败,捕获异常并记录错误信息.
        4. 将辅助文件和输出文件移动到指定目录.
        5. 打印退出信息并退出程序.
        """
        # 运行 makeindex 命令
        name_target = f"{cmd[0]}"
        console.print(_("[bold]运行命令: [/bold]") + f"[cyan]{cmd[1]}\n")
        try:
            subprocess.run(cmd[1], check=True, text=True, capture_output=False, shell=True) # 使用shell=True:告诉subprocess.run使用shell来执行命令,这样可以利用shell的功能来搜索PATH中的命令.
            return name_target
        except Exception as e:
            self.logger.error(_("%(args)s 编译失败,请查看日志文件以获取详细信息: ") % {'args': cmd[0]} + f"{self.auxdir}{self.project_name}.log\n{e}")
            self.MRO.move_specific_files(self.aux_files, '.', self.auxdir)
            self.MRO.move_specific_files(self.out_files, '.', self.outdir)
            exit_pytexmk()

    # --------------------------------------------------------------------------------
    # 定义 xdv 编译函数
    # --------------------------------------------------------------------------------
    def compile_xdv(self):
        """
        编译xdv文件为pdf文件.

        行为逻辑:
        1. 构建编译命令选项列表.
        2. 如果设置了静默编译,则在命令选项中添加"-q"参数.
        3. 打印将要运行的命令.
        4. 尝试运行编译命令.
        5. 如果编译失败,记录错误信息,移动辅助文件和输出文件到指定目录,并退出程序.
        """
        options = ["dvipdfmx", "-V", "2.0", f"{self.project_name}"]
        if not self.non_quiet:
            options.insert(1, "-q") # 静默编译
        console.print(_("[bold]运行命令: [/bold]") + f"[cyan]{' '.join(options)}\n")
        try:
            subprocess.run(options, check=True, text=True, capture_output=False)
        except Exception as e:
            self.logger.error(_("DVIPDFMX 编译失败,请查看日志文件以获取详细信息: ") + f"{self.auxdir}{self.project_name}.log\n{e}")
            self.MRO.move_specific_files(self.aux_files, '.', self.auxdir)
            self.MRO.move_specific_files(self.out_files, '.', self.outdir)
            exit_pytexmk()


# --------------------------------------------------------------------------------
# 定义 统计参考文献次数的函数
# --------------------------------------------------------------------------------
def _count_citations(file_name):
    """
    统计给定aux文件中所有citation的出现次数.

    参数:
    - file_name (str): 包含citation信息的aux文件路径.

    返回:
    - dict: 一个字典,键为citation名称,值为该citation在文件中出现的次数.

    行为逻辑:
    1. 打开并读取aux文件的内容.
    2. 使用正则表达式模式BIBER_CITE_PATTERN查找所有的\\abx@aux@cite,并统计每个citation的出现次数.
    3. 使用正则表达式模式BIBTEX_CITE_PATTERN查找所有的\\citation,并统计每个citation的出现次数.
    4. 返回包含所有citation计数的字典.
    """
    # 创建一个默认值为int的字典,用于存储每个citation出现的次数
    counter = defaultdict(int) # 使用 int 作为工厂函数,默认值为 0

    # 打开aux文件并读取其内容
    with open(file_name, 'r', encoding='utf-8') as aux_file:
        aux_content = aux_file.read()
    match = BIBER_CITE_PATTERN.search(aux_content)
    if match:
        # 使用正则表达式模式 BIBER_CITE_PATTERN 查找所有的\abx@aux@cite
        for match in BIBER_CITE_PATTERN.finditer(aux_content):
            # 获取匹配到的citation名称
            name = match.groups()[0]
            # 增加该citation在字典中的计数, 如果 citation 出现多次,则计数会累加
            counter[name] += 1 # counter[name] = counter[name] + 1
    match = BIBTEX_CITE_PATTERN.search(aux_content)
    if match:
        # 使用正则表达式模式 BIBTEX_CITE_PATTERN 查找所有的 \citation
        for match in BIBTEX_CITE_PATTERN.finditer(aux_content):
            # 获取匹配到的citation名称
            name = match.groups()[0]
            # 增加该citation在字典中的计数
            counter[name] += 1
    # 返回包含所有citation计数的字典
    return counter
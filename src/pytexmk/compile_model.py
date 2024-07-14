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
LastEditTime : 2024-07-15 00:11:06 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : \PyTeXMK\src\pytexmk\compile_model.py
Description  : 
 -----------------------------------------------------------------------
'''
# -*- coding: utf-8 -*-
import os
import re
import logging
import subprocess
from collections import defaultdict
from .info_print import print_message
from rich import console
console = console.Console()  # 设置宽度为80


# 定义正则表达式模式
BIBER_PATTERN = re.compile(r'\\abx@aux@refcontext')  # 匹配 biber 命令
BIBTEX_PATTERN = re.compile(r'\\bibdata')  # 匹配 bibtex 命令

BIBER_BIB_PATTERN = re.compile(r'<bcf:datasource[^>]*>\s*(.*?)\s*</bcf:datasource>')  # 
BIBTEX_BIB_PATTERN = re.compile(r'\\bibdata\{(.*)\}')  # 匹配\bibdata{}命令

BIBER_CITE_PATTERN = re.compile(r'\\abx@aux@cite\{(.*)\}')  # 匹配\abx@aux@cite{}命令
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
TEXLIPSE_MAIN_PATTERN = re.compile(r'^mainTexFile=(.*)(?:\.tex)$', re.M)  # 匹配TeXlipse主文件

class CompileModel(object):
    def __init__(self, compiler_engine, project_name, quiet):
        self.compiler_engine = compiler_engine
        self.project_name = project_name
        self.quiet = quiet 
        self.bib_file = ''  # 初始化参考文献文件路径为空字符串

    # --------------------------------------------------------------------------------
    # 定义日志记录器
    # --------------------------------------------------------------------------------
    def _setup_logger(self):
        '''设置日志记录器。'''
        # 获取名为'latexmk.py'的日志记录器实例
        log = logging.getLogger('_main_.py')

        # 创建一个流处理器，用于将日志输出到控制台
        handler = logging.StreamHandler()
        # 将流处理器添加到日志记录器中
        log.addHandler(handler)

        # 如果设置了verbose选项，则将日志级别设置为INFO，以便输出更多信息
        if self.opt.verbose:
            log.setLevel(logging.INFO)  # 设置日志级别为INFO
        # 返回设置好的日志记录器实例
        return log
    
    # --------------------------------------------------------------------------------
    # 定义信息获取函数
    # --------------------------------------------------------------------------------
    def prepare_latex_output_files(self):
        '''
        这个函数用于在LaTeX编译过程开始前，检查并处理已存在的 LaTeX 输出文件，并进行处理。
            - 解析*.aux文件以获取引用计数。
            - 获取文件内容以检测更改。
                - *.toc文件
                - 所有可用的符号索引宏包名称和对应的辅助文件
        '''
        # 检查是否存在项目名称对应的.aux文件
        if os.path.isfile(f'{self.project_name}.aux'):
            # 生成引用计数器
            cite_counter = self._generate_citation_counter()
            # 读取词汇表
            makeindex_aux_content_dict_old = self._makeindex_aux_content_get()
        else:
            # 如果不存在.aux文件，初始化引用计数器为默认值
            cite_counter = {f'{self.project_name}.aux' : defaultdict(int)}

        # 检查是否存在.toc文件
        if os.path.isfile(f'{self.project_name}.toc'):
            # 读取.toc文件内容
            with open(f'{self.project_name}.toc', 'r', encoding='utf-8') as fobj:
                toc_file = fobj.read()
        else:
            # 如果不存在.toc文件，初始化toc_file为空字符串
            toc_file = ''

        # 返回引用计数器、toc文件内容和词汇表文件内容
        return cite_counter, toc_file, makeindex_aux_content_dict_old

    # --------------------------------------------------------------------------------
    # 定义参考文献引用次数获取函数
    # --------------------------------------------------------------------------------
    def _generate_citation_counter(self):
        '''
        获取主aux文件及所有辅助aux文件中的引用次数。
        '''
        # 初始化一个空的字典，用于存储每个aux文件的引用数量
        cite_counter = dict()
        # 构造主aux文件的文件名，格式为项目名加上.aux后缀
        file_name = f'{self.project_name}.aux'
        # 打开主aux文件并读取其内容
        with open(file_name, 'r', encoding='utf-8') as fobj:
            main_aux = fobj.read()
        # 计算主aux文件中的引用数量，并将其存储在cite_counter字典中
        cite_counter[file_name] = _count_citations(file_name)

        # 使用正则表达式查找所有包含的aux文件
        for match in re.finditer(r'\\@input\{(.*.aux)\}', main_aux):
            # 获取匹配到的aux文件名
            file_name = match.groups()[0]
            try:
                # 尝试计算该aux文件中的引用数量
                counter = _count_citations(file_name)
            except IOError:
                # 如果文件不存在或无法读取，则跳过该文件
                pass
            else:
                # 如果成功计算引用数量，则将其存储在cite_counter字典中
                cite_counter[file_name] = counter

        # 返回包含所有aux文件引用数量的字典
        return cite_counter

    # --------------------------------------------------------------------------------
    # 定义旧的符号索引辅助文件内容获取函数
    # --------------------------------------------------------------------------------
    def _makeindex_aux_content_get(self): 
        '''
        判断两个索引辅助文件是否同时存在
        获取索引辅助文件内容
        '''

        file_name = f'{self.project_name}.aux' # 构造主aux文件的文件名，格式为项目名加上.aux后缀
        makeindex_aux_content_dict_old = dict()  # 定义一个字典，用于存储旧的索引辅助文件内容

        # 读取主aux文件
        if os.path.isfile(file_name):  # 检查主aux文件是否存在
            # 判断并获取 glossaries 宏包的辅助文件内容
            if any(os.path.exists(f"{self.project_name}{ext}") for ext in [".glo", ".acn", ".slo"]):
                with open(file_name, 'r', encoding='utf-8') as fobj:
                    main_aux = fobj.read()
                pattern = r'\\@newglossary\{(.*)\}\{.*\}\{(.*)\}\{(.*)\}'  # 定义正则表达式模式，用于匹配词汇表条目
                for match in re.finditer(pattern, main_aux):  # 使用正则表达式查找所有匹配的词汇表条目
                    name, ext_o, ext_i = match.groups()  # 提取匹配的组，分别是词汇表名称、输出扩展和输入扩展
                    if os.path.exists(f"{self.project_name}{ext_i}") and os.path.exists(f"{self.project_name}{ext_o}"):  # 判断输出和输入扩展文件是否同时存在
                        with open(f"{self.project_name}{ext_o}", 'r', encoding='utf-8') as fobj:
                            makeindex_ext_i_content = fobj.read()
                        makeindex_aux_content_dict_old[f'{self.project_name}.{ext_i}'] = [makeindex_ext_i_content]

            # 判断并获取 nomencl 宏包的辅助文件内容
            if os.path.isfile(f"{self.project_name}.nlo"):
                if os.path.exists(f"{self.project_name}.nlo") and os.path.exists(f"{self.project_name}.nls"):  # 判断输出和输入扩展文件是否同时存在
                    with open(f"{self.project_name}.nlo", 'r', encoding='utf-8') as fobj:
                        makeindex_ext_i_content = fobj.read()
                    makeindex_aux_content_dict_old[f'{self.project_name}.nlo'] = [makeindex_ext_i_content]

            # 判断并获取 makeidx 宏包的辅助文件内容
            if os.path.isfile(f"{self.project_name}.idx"):
                if os.path.exists(f"{self.project_name}.idx") and os.path.exists(f"{self.project_name}.ind"):  # 判断输出和输入扩展文件是否同时存在
                    with open(f"{self.project_name}.idx", 'r', encoding='utf-8') as fobj:
                        makeindex_ext_i_content = fobj.read()
                    makeindex_aux_content_dict_old[f'{self.project_name}.{ext_i}'] = [makeindex_ext_i_content]
        else:
            print(f"没有找到名为{self.project_name}.aux 的文件", 'error')

        return makeindex_aux_content_dict_old

    # --------------------------------------------------------------------------------
    # 定义目录更新判断函数
    # --------------------------------------------------------------------------------
    def toc_changed_judgment(self, toc_file):
        '''
        判断*.toc文件在第一次latex运行期间是否发生了变化。
        '''
        file_name = f'{self.project_name}.toc'   # 生成toc文件的完整路径
        if os.path.isfile(file_name):  # 检查toc文件是否存在
            with open(file_name, 'r', encoding='utf-8') as fobj:  # 打开toc文件
                if fobj.read() != toc_file:  # 比较toc文件内容与传入的toc_file内容
                    return True  # 如果内容不同，返回True表示toc文件已变化


    # --------------------------------------------------------------------------------
    # 定义 TeX 编译函数
    # --------------------------------------------------------------------------------
    def compile_tex(self, compiler_times):
        options = [self.compiler_engine, "-shell-escape", "-file-line-error", "-halt-on-error", "-synctex=1", f'{self.project_name}.tex']
        print_message(f"{compiler_times} 次 {self.compiler_engine} 编译")
        if self.compiler_engine == 'xelatex':
            options.insert(5, "-no-pdf")
        if self.quiet:
            options.insert(4, "-interaction=batchmode") # 静默编译
        else:
            options.insert(4, "-interaction=nonstopmode") # 非静默编译
        console.print(f"[bold]运行命令：[/bold][red][cyan]{' '.join(options)}[/cyan][/red]\n")
        
        try:
            subprocess.run(options, check=True, text=True, capture_output=False)
            return True
        except subprocess.CalledProcessError as e:
            print(e.output)
            return False


    # --------------------------------------------------------------------------------
    # 定义参考文献判断函数
    # --------------------------------------------------------------------------------
    def bib_judgment(self, old_cite_counter):
        '''
        1. 检查是否存在 *.bib 文件。
        2. 判断是否需要运行 "biber" 或 "bibtex"。
        3. 判断是否设置 bib 参考文献数据库文件。
        4. 判断 bib 参考文献数据库文件是否存在。
        5. 判断第一次 LaTeX 运行期间引用数量是否发生变化。
        6. 检查 LaTeX 输出日志中的提示。
        '''
        bib_engine = None
        name_target = None
        Latex_compilation_times = 0
        if os.path.exists(f"{self.project_name}.aux"):
            with open(f"{self.project_name}.aux", 'r', encoding='utf-8') as fobj:
                aux_content = fobj.read()
            match_biber = BIBER_PATTERN.search(aux_content) # 检索aux辅助文件中是否存在biber特征命令
            match_bibtex = BIBTEX_PATTERN.search(aux_content)
            if match_biber and match_bibtex: # 判断是否使用biber或bibtex编译
                if match_biber: # 判断应使用 biber 引擎编译
                    with open(f"{self.project_name}.bcf", 'r', encoding='utf-8') as fobj:
                        match_biber_bib = BIBER_BIB_PATTERN.search(fobj.read()) # 检索bcf文件中是否存在bib文件名
                    if not match_biber_bib:
                        print_bib = f"没有设置名为{self.bib_file} 的参考文献数据库文件"
                    else:
                        self.bib_file = match_biber_bib.group(1)
                        bib_engine = 'biber'
                        Latex_compilation_times = 2 # LaTeX 额外编译次数 
                
                elif match_bibtex: # 判断应使用 bibtex 引擎编译
                    match_bibtex_bib = BIBTEX_BIB_PATTERN.search(aux_content)
                    if not match_bibtex_bib:
                        print_bib =  f"没有设置名为{self.bib_file} 的参考文献数据库文件"
                    else:
                        self.bib_file = match_bibtex_bib.group(1)
                        bib_engine = 'bibtex'
                        Latex_compilation_times = 2 # LaTeX 额外编译次数 

                if not os.path.isfile('%s.bib' % self.bib_file):  # 检查 bib 文件是否存在
                    print_bib = f"没有找到名为{self.bib_file}.bib的参考文献数据库文件"
                    Latex_compilation_times = 0 # LaTeX 额外编译次数 
                
                if old_cite_counter != self._generate_citation_counter():  # 比较引用数量是否发生变化
                    print_bib = "参考文献引用数量发生变化"
                    Latex_compilation_times = 2

                if (re.search(f'No file {self.project_name}.bbl.', self.out) or  # 检查latex输出中是否有bbl文件缺失的提示
                    re.search('LaTeX Warning: Citation .* undefined', self.out)):  # 检查latex输出中是否有引用未定义的提示
                    print_bib = "LaTeX 编译日志中存在bbl文件缺失或引用未定义的提示"
                    Latex_compilation_times = 2

                print_message(f'{bib_engine} 文献编译')
                print_bib = f"{bib_engine} 编译参考文献"
                name_target = f"{bib_engine} 编译"

            elif re.search(r'\\bibcite', aux_content):
                print_bib = "thebibliography 环境实现排版 "

            else:
                print_bib = "没有引用参考文献或编译工具不属于 bibtex 或 biber "
        else:
            print_bib = "文档没有参考文献"
        return bib_engine, Latex_compilation_times, print_bib, name_target

    # --------------------------------------------------------------------------------
    # 定义参考文献编译函数
    # --------------------------------------------------------------------------------
    def compile_bib(self, bib_engine):
        options = [bib_engine, self.project_name]

        if self.quiet and bib_engine == 'biber':
            options.insert(1, "-self.quiet") # 静默编译
                
        console.print(f"[bold]运行命令：[/bold][cyan]{' '.join(options)}[/cyan]\n")
        try:
            subprocess.run(options, check=True, text=True, capture_output=False)
            return True
        except subprocess.CalledProcessError as e:
            print(e.output)
            return False

    # --------------------------------------------------------------------------------
    # 定义索引更新判断函数
    # --------------------------------------------------------------------------------
    def _index_changed_judgment(self, makeindex_aux_content_dict_old, makeindex_aux_infile, makeindex_aux_outfile):
        make_index = False  # 初始化是否需要重新生成索引的标志
        if re.search(f'No file {makeindex_aux_infile}.', self.out):  # 检查输出中是否包含“没有该输入文件”的信息
            make_index = True  # 如果包含，则需要重新生成词汇表
        if not os.path.isfile(makeindex_aux_outfile):  # 检查输出文件是否存在
            make_index = True  # 如果不存在，则需要重新生成词汇表
        else:
            with open(makeindex_aux_infile, 'r', encoding='utf-8') as fobj:  # 打开输出文件
                try:
                    if makeindex_aux_content_dict_old[makeindex_aux_infile] != fobj.read():  # 比较词汇表文件内容与记录的内容
                        make_index = True  # 如果不一致，则需要重新生成词汇表"
                except KeyError:  # 如果词汇表文件内容未记录，则需要重新生成词汇表
                    make_index = True
        return make_index
    
    # --------------------------------------------------------------------------------
    # 定义索引编译函数
    # --------------------------------------------------------------------------------
    def makeindex_judgment(self, makeindex_aux_content_dict_old): 
        file_name = f'{self.project_name}.aux' # 构造主aux文件的文件名，格式为项目名加上.aux后缀
        run_makeindex_list_cmd = [] # 初始化需要运行 makeindex 的命令列表

        # 判断并获取 glossaries 宏包的辅助文件名称
        if any(os.path.exists(f"{self.project_name}{ext}") for ext in [".glo", ".acn", ".slo"]):
            with open(file_name, 'r', encoding='utf-8') as fobj:
                main_aux = fobj.read()
            pattern = r'\\@newglossary\{(.*)\}\{.*\}\{(.*)\}\{(.*)\}'  # 定义正则表达式模式，用于匹配词汇表条目
            for match in re.finditer(pattern, main_aux):  # 使用正则表达式查找所有匹配的词汇表条目
                name, ext_o, ext_i = match.groups()  # 提取匹配的组，分别是词汇表名称、输出扩展和输入扩展
                if os.path.exists(f"{self.project_name}{ext_i}"):  # 判断输入扩展文件是否存在
                    if self._index_changed_judgment(makeindex_aux_content_dict_old, f"{self.project_name}{ext_i}", f"{self.project_name}{ext_o}"):
                        run_makeindex_list_cmd.append([f'glossaries {name}', f"makeindex -s {self.project_name}.ist -o {self.project_name}{ext_o} {self.project_name}{ext_i}"])
        
        # 判断并获取 nomencl 宏包的辅助文件名称
        if os.path.isfile(f"{self.project_name}.nlo"):
            if os.path.exists(f"{self.project_name}.nlo") and os.path.exists(f"{self.project_name}.nls"):  # 判断输出和输入扩展文件是否同时存在
                if self._index_changed_judgment(makeindex_aux_content_dict_old, f"{self.project_name}.nlo", f"{self.project_name}.nls"):
                    run_makeindex_list_cmd.append(['nomencl', f"makeindex -s nomencl.ist -o {self.project_name}.nls {self.project_name}.nlo"])

        # 判断并获取 makeidx 宏包的辅助文件名称
        if os.path.isfile(f"{self.project_name}.idx"):
            if os.path.exists(f"{self.project_name}.idx") and os.path.exists(f"{self.project_name}.ind"):  # 判断输出和输入扩展文件是否同时存在
                if self._index_changed_judgment(makeindex_aux_content_dict_old, f"{self.project_name}.idx", f"{self.project_name}.ind"):
                    run_makeindex_list_cmd.append(['makeidx', f"makeindex {self.project_name}.idx"])

        return run_makeindex_list_cmd
    
    # --------------------------------------------------------------------------------
    # 定义索引编译函数
    # --------------------------------------------------------------------------------
    def compile_makeindex(self, run_makeindex_list_cmd): 
        # 运行 makeindex 命令
        for cmd in run_makeindex_list_cmd:
            print_message(f"{cmd[0]} 编译")
            name_target = f"{cmd[0]} 宏包"
            console.print(f"[bold]运行命令：[/bold][cyan]{cmd[1]}[/cyan]\n")
            print_index = f"{cmd[0]} 生成索引"
            print(print_index,"\n")
            try:
                subprocess.run(cmd, check=True, text=True, capture_output=False)
                return print_index, name_target, True
            except subprocess.CalledProcessError as e:
                print(e.output)
                return print_index, name_target, False
        

    # --------------------------------------------------------------------------------
    # 定义 xdv 编译函数
    # --------------------------------------------------------------------------------
    def compile_xdv(self):
        print_message("dvipdfmx 编译")
        options = ["dvipdfmx", "-V", "2.0", f"{self.project_name}"]
        if self.quiet:
            options.insert(1, "-q") # 静默编译
        console.print(f"[bold]运行命令：[/bold][cyan]{' '.join(options)}[/cyan]\n")
        try:
            subprocess.run(options, check=True, text=True, capture_output=False)
            return True
        except subprocess.CalledProcessError as e:
            print(e.output)
            return False


def _count_citations(file_name):
        '''
        统计 aux 文件中所有参考文献引用的次数。
        '''
        # 导入defaultdict用于创建一个默认值为int的字典
        from collections import defaultdict

        # 创建一个默认值为int的字典，用于存储每个citation出现的次数
        counter = defaultdict(int)

        # 打开aux文件并读取其内容
        with open(file_name, 'r', encoding='utf-8') as aux_file:
            aux_content = aux_file.read()
        match = BIBER_CITE_PATTERN.search(aux_content)
        if match:
            # 使用正则表达式模式 BIBER_CITE_PATTERN 查找所有的\abx@aux@cite
            for match in BIBER_CITE_PATTERN.finditer(aux_content):
                # 获取匹配到的citation名称
                name = match.groups()[0]
                # 增加该citation在字典中的计数
                counter[name] += 1
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
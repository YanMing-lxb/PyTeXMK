��    P      �  k         �  �   �  2   Y     �     �     �     �     �     �          )     B     `     ~  $   �  Q   �  B   
	  `   M	  H   �	  )   �	  +   !
  D   M
  �   �
  �   ,     �     �     �  B      )   C  �   m  �   S  �  �     �     �     �          &     C  '   X  $   �  -   �     �  6   �  6     *   T  $     H   �  *   �  W        p     �     �     �  $   �  $        3  4   N  D   �  �   �  �   i     �       4   #  1   X  1   �  (   �  +   �  )     ,   ;  5   h  5   �  &   �  )   �  )   %  )   O  #   y  &   �  &   �     �  ;       =  �   U  "     "   @     c     |     �     �     �     �     �          %     A  #   V  d   z  S   �  p   3  U   �  "   �  -     F   K  X   �  X   �     D     R     l  J   �  :   �      �   ,   l  �      N#     f#     }#     �#     �#     �#  *   �#  +   $  4   A$     v$  <   �$  <   �$  9   %  *   ?%  V   j%  ,   �%  b   �%     Q&  #   k&      �&  +   �&  *   �&  0   '     8'  @   M'  N   �'  �   �'  �   �(     )     -)  6   B)  /   y)  /   �)  (   �)  '   *  '   **  ,   R*  4   *  5   �*  %   �*  0   +  -   A+  )   o+  $   �+  0   �+  -   �+     ,  I   7,             0   H          :   7   P       )   9       @   E       C      '   4                ,   G              !   
   N      *   .   K      6       A      F      I   3   $   &           B                     8          ?      #   L   ;   "   M              %       2   O   /             +         <   >                              1                        D   -   5   =   J       (   	           
PyTeXMK-支持使用魔法注释来定义待编译主文件、编译程序、编译结果存放位置等（仅支持检索文档前 50 行）
 %(args)s 的辅助文件不存在, 请检查编译 %(args)s 的辅助文件存在 LaTeXDiff 后处理 LaTeXDiff 编译出错:  LaTeXDiff 运行 LaTeXDiff 预处理 LuaLaTeX 进行编译 PdfLaTeX 进行编译 PyTeXMK 版本: %(args)s README 本地路径: %(args)s README.html 文件未找到:  XeLaTeX 进行编译 [bold green]PyTeXMK 开始运行...
 [bold green]已完成清除所有主文件的辅助文件和输出文件的指令 [bold green]已完成清除所有主文件的辅助文的件指令 [bold green]已完成清除所有带辅助文件后缀的文件和主文件输出文件的指令 [bold green]已完成清除所有带辅助文件后缀的文件的指令 [bold green]正在打开 README 文件... [i]LaTeX 辅助编译程序  ---- 焱铭[/] 不能对同一个文件进行比较, 请检查文件名是否正确 使用 LaTeXDiff 进行编译, 生成改动对比文件并编译新文件，当在配置文件中配置相关参数时可省略 'OLD_FILE' 和 'NEW_FILE' 使用 LaTeXDiff 进行编译, 生成改动对比文件，当在配置文件中配置相关参数时可省略 'OLD_FILE' 和 'NEW_FILE' 修复 PDF 文件 全辅助文件->根目录 删除 Flatten 后的文件... 启用草稿模式进行编译，提高编译速度 (无图显示) 命令行未指定 LaTeXDiff 相关参数 如欲了解魔法注释以及其他详细说明信息请运行 -r 参数，阅读 README 文件。发现 BUG 请及时更新到最新版本，欢迎在 Github 仓库中提交 Issue：https://github.com/YanMing-lxb/PyTeXMK/issues 尝试修复所有根目录以外的 PDF 文件, 当 LaTeX 编译过程中警告 invalid X X R object 时, 可使用此参数尝试修复所有 pdf 文件 尝试编译结束后调用 Web 浏览器或者本地 PDF 阅读器预览生成的PDF文件 (如需指定在命令行中指定待编译主文件, 则 -pv 命令, 需放置 document 后面并无需指定参数, 示例: pytexmk main -pv; 如无需在命令行中指定待编译主文件, 则直接输入 -pv 即可, 示例: pytexmk -pv), 如有填写 [dark_cyan]FILE_NAME[/dark_cyan] 则不进行编译打开指定文件 (注意仅支持输出目录下的 PDF 文件, 示例: pytexmk -pv main) 开始后处理 开始预处理 开始预处理命令 待编译主文件名 打开 README 文件出错:  提取魔法注释:  显示 PyTeXMK 的帮助信息并退出 显示 PyTeXMK 的版本号并退出 显示 PyTeXMK 运行过程中的详细信息 显示README文件 根据配置文件设置 LaTeXDiff 新 TeX 文件为:  根据配置文件设置 LaTeXDiff 旧 TeX 文件为:  检测并移动辅助文件到根目录... 清除所有主文件的辅助文件 清除所有主文件的辅助文件（包含根目录）和输出文件 清除所有带辅助文件后缀的文件 清除所有带辅助文件后缀的文件（包含根目录）和主文件输出文件 清除所有的辅助文件 清除文件夹内辅助文件 清除文件夹内输出文件 清除根目录内辅助文件 移动结果文件到输出目录... 移动辅助文件到辅助目录... 结果文件->输出目录 请同时指定 LaTeXDiff 所需的新旧 TeX 文件 请指定在命令行或配置文件中指定两个新旧 TeX 文件 请输入 LaTeXDiff 的显示风格：
  1 - 显示参考文献/符号说明的修改
  2 - 不显示参考文献/符号说明的修改
请选择 (1 或者 2):  请输入正确的选项 (1 或者 2)
  1 - 显示参考文献/符号说明的修改
  2 - 不显示参考文献/符号说明的修改 辅助文件->根目录 辅助文件->辅助目录 通过配置文件设置 LaTeXDiff 对比文件为:  通过配置文件设置 LaTeXDiff 新文件为:  通过配置文件设置 LaTeXDiff 旧文件为:  通过配置文件设置 PDF 预览为:  通过配置文件设置 PDF 预览器为:  通过配置文件设置安静模式为:  通过配置文件设置索引文件名为:  通过配置文件设置索引输入文件后缀为:  通过配置文件设置索引输出文件后缀为:  通过配置文件设置编译器为:  通过配置文件设置辅助目录为:  通过配置文件设置输出目录为:  通过配置文件设置默认文件为:  通过魔法注释设置程序为:  通过魔法注释设置辅助目录:  通过魔法注释设置输出目录:  非安静模式运行 非安静模式运行, 此模式下终端显示日志信息 Project-Id-Version: PACKAGE VERSION
Report-Msgid-Bugs-To: 
PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE
Last-Translator: FULL NAME <EMAIL@ADDRESS>
Language-Team: LANGUAGE <LL@li.org>
Language: 
MIME-Version: 1.0
Content-Type: text/plain; charset=UTF-8
Content-Transfer-Encoding: 8bit
 
PyTeXMK - supports using magic comments to define the main file to be compiled, compiler, storage location of compilation results, etc. (only supports retrieving the first 50 lines of the document)
 Auxiliary file for %(args)s exists Auxiliary file for %(args)s exists LaTeXDiff postprocessing LaTeXDiff compile error:  LaTeXDiff running LaTeXDiff preprocessing Compile with LuaLaTeX Compile with PdfLaTeX PyTeXMK version: %(args)s Local path of README: %(args)s README.html file not found. Compile with XeLaTeX [bold green]PyTeXMK is starting...
 [bold green]Completed the instruction to clear all auxiliary files and output files of the main file [bold green]Completed the instruction to clear all auxiliary files of the main file [bold green]Completed the instruction to clear all files with auxiliary file suffixes and main file output files [bold green]Completed the instruction to clear all files with auxiliary file suffixes [bold green]Opening README file... [i]LaTeX Auxiliary Compiler  ---- Yan Ming[/] Cannot compare the same file, please check if the file name is correct Compile using LaTeXDiff, generate a comparison file for changes and compile the new file Compile using LaTeXDiff, generate a comparison file for changes and compile the new file Fix PDF files All AUX files -> Root dir Deleting flattened files... Enable draft mode for compilation to improve compilation speed (not shown) LaTeXDiff related parameters not specified in command line To learn about magic comments and other detailed instructions, please run the -r parameter to read the README file. If you find a BUG, please update to the latest version promptly, and feel free to submit an Issue in the Github repository: https://github.com/YanMing-lxb/PyTeXMK/issues Attempt to fix all PDF files outside the root directory, when LaTeX compilation process warns about invalid X X R object, this parameter can be used to attempt to fix all pdf files Attempt to call a web browser or local PDF reader to preview the generated PDF file after compilation (if you need to specify the main file to be compiled in the command line, then the -pv command, needs to be placed after document and does not need to specify parameters, example: pytexmk main -pv; if you do not need to specify the main file to be compiled in the command line, then simply enter -pv, example: pytexmk -pv), if [dark_cyan]FILE_NAME[/dark_cyan] is filled in, it will not compile and will open the specified file (note that only PDF files in the output directory are supported, example: pytexmk -pv main) Starting postprocessing Starting preprocessing Starting preprocessing Main file name to be compiled Error opening README file:  Extracting magic comments:  Show help information for PyTeXMK and exit Show the version number of PyTeXMK and exit Show detailed information during the PyTeXMK runtime Show the README file Set LaTeXDiff new TeX file according to configuration file:  Set LaTeXDiff old TeX file according to configuration file:  Detecting and moving auxiliary files to root directory... Clear all auxiliary files of the main file Clear all auxiliary files of the main file (including root directory) and output files Clear all files with auxiliary file suffixes Clear all files with auxiliary file suffixes (including root directory) and main file output files Clear all auxiliary files Clear auxiliary files in the folder Clear output files in the folder Clear auxiliary files in the root directory Moving result files to output directory... Moving auxiliary files to auxiliary directory... RES files -> OUT dir Please specify both new and old TeX files required for LaTeXDiff Please specify two new and old TeX files in command line or configuration file Please enter a display style for LaTeXDiff:
 1 - Show changes in reference/symbol description
 2 - Do not show changes in reference/symbol description
Please select (1 or 2): Please enter the correct option (1 or 2)
 1 - Show changes in reference/symbol description 
 2 - Do not show changes in references/symbols AUX files -> Root dir AUX files -> AUX dir Set LaTeXDiff comparison file via configuration file:  Set LaTeXDiff new file via configuration file:  Set LaTeXDiff old file via configuration file:  Set PDF preview via configuration file:  Set PDF viewer via configuration file:  Set quiet mode via configuration file:  Set index file name via configuration file:  Set index input file suffix via configuration file:  Set index output file suffix via configuration file:  Set compiler via configuration file:  Set auxiliary directory via configuration file:  Set output directory via configuration file:  Set default file via configuration file:  Setting program via magic comments:  Setting auxiliary directory via magic comments:  Setting output directory via magic comments:  Running in non-quiet mode Run in non-quiet mode, where log information is displayed in the terminal 
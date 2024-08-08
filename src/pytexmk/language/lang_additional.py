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
Date         : 2024-08-08 09:18:49 +0800
LastEditTime : 2024-08-08 10:42:31 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /PyTeXMK/src/pytexmk/language/lang_additional.py
Description  : 
 -----------------------------------------------------------------------
'''

mrc_lang_zh = {
    'del-success': '删除成功',
    'del-failed': '删除失败',
    'move-success': '移动成功',
    'move-failed': '移动失败',
}
mrc_lang_en = {
    'del-success': 'Delete successful',
    'del-failed': 'Delete failed',
    'move-success': 'Move successful',
    'move-failed': 'Move failed',
}

mfj_lang_zh = {
    'cannot-contain-path': '文件名中不能存在路径',
    'not-in-root': '文件不存在于当前路径下',
    'file-not-tex': '文件类型非 tex',
    'search-result': '搜索到',
    'file_num': '文件数目',
    'path-error': '文件不存在于当前路径下，请检查终端显示路径是否是项目路径',
    'terminal-path': '当前终端路径',
    'search-file-error': '文件搜索失败',
    'search-file-feature': '通过特征命令检索到主文件',
    'read-file-error': '文件读取失败',
    'find-main-file-num': '发现主文件数量',
    'terminal-path-error': '终端路径下不存在主文件！请检查终端显示路径是否是项目路径！',
}
mfj_lang_en = {
    'cannot-contain-path': 'Filename cannot contain path',
    'not-in-root': 'File does not exist in the current path',
    'file-not-tex': 'File type is not tex',
    'search-result': 'Found',
    'file_num': 'Number of files',
    'path-error': 'File does not exist in the current path, please check if the terminal path is the project path',
    'terminal-path': 'Current terminal path',
    'search-file-error': 'File search failed',
    'search-file-feature': 'Retrieved main file by feature command',
    'read-file-error': 'File read failed',
    'find-main-file-num': 'Number of main files found',
    'terminal-path-error': 'Main file does not exist under the terminal path! Please check if the terminal path is the project path!',
}

pfo_lang_zh = {
    'file-openning': '正在打开文件 ...',
    'file-path': '文件路径',
    'file-open-error': '打开文件失败',
    'pdf-not-found': '当前路径下未找到 PDF 文件',
    'pdf-found-num': '找到 PDF 文件数量',
    'repairs-success': '修复成功',
    'repairs-failed': '修复失败',
    'repair-finished': '修复 PDF 结束',
    }
pfo_lang_en = {
    'file-openning': 'Opening file...',
    'file-path': 'File path',
    'file-open-error': 'Failed to open file',
    'pdf-not-found': 'No PDF file found in the current path',
    'pdf-found-num': 'Number of PDF files found',
    'repairs-success': 'Repair successful',
    'repairs-failed': 'Repair failed',
    'repair-finished': 'PDF repair finished',
    }

exit_lang_zh = {
    'exiting': '正在退出 PyTeXMK ...',
    }
exit_lang_en = {
    'exiting': 'Exiting PyTeXMK...',
    }
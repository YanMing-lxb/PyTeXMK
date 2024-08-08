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
    'del_success': '删除成功',
    'del_failed': '删除失败',
    'move_success': '移动成功',
    'move_failed': '移动失败',
}
mrc_lang_en = {
    'del_success': 'Delete successful',
    'del_failed': 'Delete failed',
    'move_success': 'Move successful',
    'move_failed': 'Move failed',
}

mfj_lang_zh = {
    'cannot_contain_path': '文件名中不能存在路径',
    'not_in_root': '文件不存在于当前路径下',
    'file_not_tex': '文件类型非 tex',
    'search_result': '搜索到',
    'file_num': '文件数目',
    'path_error': '文件不存在于当前路径下，请检查终端显示路径是否是项目路径',
    'terminal_path': '当前终端路径',
    'search_file_error': '文件搜索失败',
    'search_file_feature': '通过特征命令检索到主文件',
    'read_file_error': '文件读取失败',
    'find_main_file_num': '发现主文件数量',
    'terminal_path_error': '终端路径下不存在主文件！请检查终端显示路径是否是项目路径！',
}
mfj_lang_en = {
    'cannot_contain_path': 'Filename cannot contain path',
    'not_in_root': 'File does not exist in the current path',
    'file_not_tex': 'File type is not tex',
    'search_result': 'Found',
    'file_num': 'Number of files',
    'path_error': 'File does not exist in the current path, please check if the terminal path is the project path',
    'terminal_path': 'Current terminal path',
    'search_file_error': 'File search failed',
    'search_file_feature': 'Retrieved main file by feature command',
    'read_file_error': 'File read failed',
    'find_main_file_num': 'Number of main files found',
    'terminal_path_error': 'Main file does not exist under the terminal path! Please check if the terminal path is the project path!',
}

pfo_lang_zh = {
    'file_openning': '正在打开文件...',
    'file_path': '文件路径',
    'file_open_error': '打开文件失败',
    'pdf_not_found': '当前路径下未找到 PDF 文件',
    'pdf_found_num': '找到 PDF 文件数量',
    'repairs_success': '修复成功',
    'repairs_failed': '修复失败',
    'repair_finished': '修复 PDF 结束',
    }
pfo_lang_en = {
    'file_openning': 'Opening file...',
    'file_path': 'File path',
    'file_open_error': 'Failed to open file',
    'pdf_not_found': 'No PDF file found in the current path',
    'pdf_found_num': 'Number of PDF files found',
    'repairs_success': 'Repair successful',
    'repairs_failed': 'Repair failed',
    'repair_finished': 'PDF repair finished',
    }

exit_lang_zh = {
    'exiting': '正在退出 PyTeXMK...',
    }
exit_lang_en = {
    'exiting': 'Exiting PyTeXMK...',
    }
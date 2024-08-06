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
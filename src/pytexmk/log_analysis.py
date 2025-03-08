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
Date         : 2024-07-28 13:22:26 +0800
LastEditTime : 2024-07-28 13:22:53 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /PyTeXMK/src/pytexmk/log_analysis.py
Description  : 
 -----------------------------------------------------------------------
'''

import re

from pytexmk.language import set_language

_ = set_language('log_analysis')

# TODO: 完善LogAnalyzer类 这个只是一个大概的样子
class LogAnalyzer:
    def __init__(self):
        self.warnings = []
        self.errors = []
        self.other_messages = []

    def analyze_log(self, log_content):
        """
        分析日志内容,提取警告和错误信息.

        :param log_content: 日志文件的内容,字符串格式
        """
        # 使用正则表达式匹配警告和错误信息
        warning_pattern = re.compile(r'warning: (.+)')
        error_pattern = re.compile(r'error: (.+)')

        for line in log_content.splitlines():
            if warning_match := warning_pattern.search(line):
                self.warnings.append(warning_match.group(1))
            elif error_match := error_pattern.search(line):
                self.errors.append(error_match.group(1))
            else:
                self.other_messages.append(line)

    def read_log_file(self, file_path):
        """
        读取日志文件并分析其内容.

        :param file_path: 日志文件的路径
        """
        with open(file_path, 'r', encoding='utf-8') as file:
            log_content = file.read()
        self.analyze_log(log_content)

    def get_summary(self):
        """
        获取分析结果的摘要.

        :return: 包含警告和错误信息的字典
        """
        return {
            'warnings': self.warnings,
            'errors': self.errors,
            'other_messages': self.other_messages
        }

# 示例使用
if __name__ == "__main__":
    analyzer = LogAnalyzer()
    analyzer.read_log_file('path_to_your_log_file.log')  # 替换为你的日志文件路径
    summary = analyzer.get_summary()
    print("Warnings:", summary['warnings'])
    print("Errors:", summary['errors'])
    print("Other Messages:", summary['other_messages'])

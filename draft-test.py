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
Date         : 2024-09-07 13:51:27 +0800
LastEditTime : 2024-09-08 23:09:26 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /PyTeXMK/draft-test.py
Description  : 
 -----------------------------------------------------------------------
'''
import re
import logging
from pathlib import Path

# 配置日志记录
logging.basicConfig(level=logging.INFO)

def draft_model(project_name, draft_run, draft_judgement):
    logger = logging.getLogger(__name__)  # 调用_setup_logger方法设置日志记录器
    if draft_run:
        project_name = f"{project_name}.tex"  # 确保文件名以.tex 结尾
        
        try:
            # 定义正则表达式模式来匹配 \documentclass[args1, args2, ...]{class} 命令
            pattern = re.compile(r'(?<!%)(?<!% )(?<!%  )\\documentclass(?:\[([^\]]*)\])?\{([^\}]*)\}')
            
            # 根据 draft_judgement 的值决定是否添加或移除 "draft,"
            def replace_draft(match):
                options = match.group(1) or ''
                class_type = match.group(2)

                if draft_judgement:
                    if 'draft' not in options:
                        options = 'draft' if not options else 'draft, ' + options
                else:
                    options = re.sub(r'\bdraft\b,?', '', options)

                options = options.strip()
                options = f'[{options}]' if options else ''

                return f'\\documentclass{options}{{{class_type}}}'

            # 获取文件大小
            file_path = Path(project_name)
            file_size = file_path.stat().st_size
            size_threshold = 1 * 1024**2  # 1 MB 作为阈值

            logger.info(f"开始处理文件: {project_name}, 文件大小: {file_size / 1024**2:.3f} MB")

            if file_size < size_threshold:
                # 小文件,直接读取到内存处理
                logger.info("文件较小,直接读取到内存处理")
                with file_path.open('r', encoding='utf-8') as file_in:
                    content = file_in.read()

                modified_content = pattern.sub(replace_draft, content)

                with file_path.open('w', encoding='utf-8') as file_out:
                    file_out.write(modified_content)
            else:
                # 大文件,逐行处理
                logger.info("文件较大,逐行处理")
                temp_file = file_path.with_suffix('.tmp')

                with file_path.open('r', encoding='utf-8') as file_in, temp_file.open('w', encoding='utf-8') as file_out:
                    for line in file_in:
                        modified_line = pattern.sub(replace_draft, line)
                        file_out.write(modified_line)

                temp_file.replace(file_path)

            logger.info("草稿模式更新成功.")
        except FileNotFoundError:
            logger.error(f"文件未找到: {project_name}")
        except PermissionError:
            logger.error(f"权限错误: 无法读取或写入文件 {project_name}")
        except Exception as e:
            logger.error(f"更新草稿模式时出错: {e}")
    else:
        logger.info("草稿模式未启用, 跳过.")

draft_model("main", False, True)

# draft_model("main", False)
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
Date         : 2024-03-11 22:56:29 +0800
LastEditTime : 2024-03-21 23:08:46 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /PyTeXMK/src/pytexmk/clean_pdf.py
Description  : 
 -----------------------------------------------------------------------
'''


import fitz
import os

# 递归获取当前目录及子目录下的所有PDF文件
def get_all_pdf_files(root_dir):
    pdf_files = []
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith('.pdf'):
                pdf_files.append(os.path.join(root, file))
    return pdf_files


def clean(pdf_files):
    # 遍历PDF文件列表
    if pdf_files:
        print(f"共发现 {len(pdf_files)} 个PDF文件。")
        for pdf_file in pdf_files:
            # 使用pymupdf库处理PDF文件
            try:
                doc = fitz.open(pdf_file)
                clean_doc = fitz.open()
                
                for page_num in range(doc.page_count):
                    page = doc.load_page(page_num)
                    clean_doc.insert_page(page_num, width=page.rect.width, height=page.rect.height)
                    clean_doc[page_num].show_pdf_page(page.rect, doc, page_num)
                
                output_path = f"{pdf_file}.cleancopied.pdf"
                clean_doc.save(output_path)
                clean_doc.close()
                
                # 如果处理成功，替换原文件
                os.replace(output_path, pdf_file)
                print(f"已处理: {pdf_file}")
            except Exception as e:
                print(f"处理出错 {pdf_file}: {e}")
        print("所有PDF文件已处理完成。")
    else:
        print("未发现PDF文件。")
    

# 获取当前目录及子目录下的所有PDF文件
pdf_files = get_all_pdf_files('.')

# 调用clean函数处理PDF文件
clean(pdf_files)
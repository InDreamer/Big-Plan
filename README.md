import tkinter as tk
from tkinter import filedialog
import os
import re

def extract_date_from_line(line):
    # 假设日期在每行的开头，可能的格式有YYYY-MM-DD、YYYY/MM/DD、DD-MM-YYYY等
    match = re.match(r'^(\d{4}-\d{2}-\d{2})', line)
    if match:
        return match.group(1)
    match = re.match(r'^(\d{4}/\d{2}/\d{2})', line)
    if match:
        return match.group(1).replace('/', '-')
    match = re.match(r'^(\d{2}-\d{2}-\d{4})', line)
    if match:
        day, month, year = match.group(1).split('-')
        return f"{year}-{month}-{day}"
    # 其他日期格式需要根据实际情况添加
    return None

def split_txt_file():
    MB_size = 100 * 1024 * 1024  # 100 MB

    # 创建隐藏的Tkinter根窗口
    root = tk.Tk()
    root.withdraw()

    # 选择源txt文件
    source_file = filedialog.askopenfilename(title="选择txt文件", filetypes=[("Text files", "*.txt")])
    if not source_file:
        print("未选择文件。")
        return

    # 选择目标路径
    output_dir = filedialog.askdirectory(title="选择输出目录")
    if not output_dir:
        print("未选择输出目录。")
        return

    # 检查文件大小
    file_size = os.path.getsize(source_file)
    if file_size < MB_size:
        print("文件小于100MB，无需拆分。")
        return

    print("正在拆分文件，请稍候...")

    with open(source_file, "r", encoding='utf-8') as f_in:
        chunk_size = 0
        chunk_index = 1
        f_out = None
        for line in f_in:
            # 如果需要开始新的文件
            if chunk_size == 0:
                # 提取日期作为文件名
                date_prefix = extract_date_from_line(line)
                if not date_prefix:
                    date_prefix = f"chunk{chunk_index}"
                output_file = os.path.join(output_dir, f"{date_prefix}.txt")
                # 如果文件名已存在，添加索引避免覆盖
                while os.path.exists(output_file):
                    output_file = os.path.join(output_dir, f"{date_prefix}_{chunk_index}.txt")
                    chunk_index += 1
                if f_out:
                    f_out.close()
                f_out = open(output_file, 'w', encoding='utf-8')
                chunk_size = 0
            f_out.write(line)
            line_size = len(line.encode('utf-8'))
            chunk_size += line_size
            if chunk_size >= MB_size:
                chunk_size = 0  # 下次循环将开启新文件
        if f_out:
            f_out.close()
    print("文件拆分完成。")

if __name__ == "__main__":
    split_txt_file()
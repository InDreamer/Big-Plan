import tkinter as tk
from tkinter import filedialog
import os
from datetime import datetime

def extract_datetime_from_line(line):
    """
    从行中提取日期时间，格式为 [YYYY-MM-DD HH:MM:SS,mmm]
    """
    try:
        # 查找第一个 '[' 和 随后的 ']'
        start_idx = line.find('[')
        if start_idx != -1:
            end_idx = line.find(']', start_idx)
            if end_idx != -1:
                datetime_str = line[start_idx + 1:end_idx]
                # 尝试解析日期时间
                try:
                    # 定义可能的日期时间格式
                    datetime_formats = [
                        '%Y-%m-%d %H:%M:%S,%f',
                        '%Y/%m/%d %H:%M:%S,%f',
                        '%Y-%m-%d %H:%M:%S',
                        '%Y/%m/%d %H:%M:%S',
                    ]
                    for fmt in datetime_formats:
                        try:
                            dt = datetime.strptime(datetime_str, fmt)
                            # 格式化日期时间以用于文件名
                            datetime_prefix = dt.strftime('%Y-%m-%d_%H-%M-%S')
                            return datetime_prefix
                        except ValueError:
                            continue
                except Exception as e:
                    pass
    except Exception as e:
        pass
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

    with open(source_file, 'r', encoding='utf-8') as f_in:
        chunk_size = 0
        chunk_index = 1
        chunk_lines = []
        datetime_prefix = None
        for line in f_in:
            line_size = len(line.encode('utf-8'))
            chunk_size += line_size
            chunk_lines.append(line)

            # 如果还没有获取到日期时间，从当前行尝试提取
            if datetime_prefix is None:
                datetime_prefix = extract_datetime_from_line(line)

            if chunk_size >= MB_size:
                # 如果没有找到日期时间，使用默认命名
                if not datetime_prefix:
                    datetime_prefix = f"chunk{chunk_index}"
                # 生成输出文件路径
                output_file = os.path.join(output_dir, f"{datetime_prefix}.txt")
                # 如果文件名已存在，添加索引避免覆盖
                temp_index = 1
                while os.path.exists(output_file):
                    output_file = os.path.join(output_dir, f"{datetime_prefix}_{temp_index}.txt")
                    temp_index += 1
                # 写入文件
                with open(output_file, 'w', encoding='utf-8') as f_out:
                    f_out.writelines(chunk_lines)
                # 重置参数，准备下一块内容
                chunk_size = 0
                chunk_lines = []
                datetime_prefix = None
                chunk_index += 1

        # 处理最后一块内容
        if chunk_lines:
            if not datetime_prefix:
                datetime_prefix = f"chunk{chunk_index}"
            output_file = os.path.join(output_dir, f"{datetime_prefix}.txt")
            temp_index = 1
            while os.path.exists(output_file):
                output_file = os.path.join(output_dir, f"{datetime_prefix}_{temp_index}.txt")
                temp_index += 1
            with open(output_file, 'w', encoding='utf-8') as f_out:
                f_out.writelines(chunk_lines)

    print("文件拆分完成。")

if __name__ == '__main__':
    split_txt_file()
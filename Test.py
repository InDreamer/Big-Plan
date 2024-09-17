import tkinter as tk
from tkinter import filedialog
import os
from datetime import datetime

def extract_time_from_line(line):
    """
    Extracts the time (HH_MM_SS) from a line containing a datetime string.
    Expected formats within the line:
    - [YYYY-MM-DD HH:MM:SS,mmm]
    - YYYY-MM-DD HH:MM:SS,mmm
    """
    try:
        # Attempt to find the datetime string within brackets
        start_idx = line.find('[')
        end_idx = line.find(']', start_idx) if start_idx != -1 else -1

        if start_idx != -1 and end_idx != -1:
            datetime_str = line[start_idx + 1:end_idx]
        else:
            # If brackets are not found, assume the datetime starts at the beginning of the line
            # Adjust this if your datetime appears elsewhere in the line
            datetime_str = line.strip().split(',')[0]

        # Define possible datetime formats
        datetime_formats = [
            '%Y-%m-%d %H:%M:%S,%f',
            '%Y/%m/%d %H:%M:%S,%f',
            '%Y-%m-%d %H:%M:%S',
            '%Y/%m/%d %H:%M:%S',
        ]

        for fmt in datetime_formats:
            try:
                dt = datetime.strptime(datetime_str, fmt)
                # Format time as HH_MM_SS for the filename
                time_prefix = dt.strftime('%H_%M_%S')
                return time_prefix
            except ValueError:
                continue
    except Exception:
        pass
    return None

def split_txt_file():
    MB_size = 100 * 1024 * 1024  # 100 MB

    # Create a hidden Tkinter root window
    root = tk.Tk()
    root.withdraw()

    # Select the source txt file
    source_file = filedialog.askopenfilename(title="选择txt文件", filetypes=[("Text files", "*.txt")])
    if not source_file:
        print("未选择文件。")
        return

    # Select the output directory
    output_dir = filedialog.askdirectory(title="选择输出目录")
    if not output_dir:
        print("未选择输出目录。")
        return

    # Check file size
    file_size = os.path.getsize(source_file)
    if file_size < MB_size:
        print("文件小于100MB，无需拆分。")
        return

    print("正在拆分文件，请稍候...")

    with open(source_file, 'r', encoding='utf-8') as f_in:
        chunk_size = 0
        chunk_index = 1
        chunk_lines = []
        time_prefix = None

        for line in f_in:
            line_size = len(line.encode('utf-8'))
            chunk_size += line_size
            chunk_lines.append(line)

            # If time_prefix is not yet set, attempt to extract it from the current line
            if time_prefix is None:
                extracted_time = extract_time_from_line(line)
                if extracted_time:
                    time_prefix = extracted_time

            # Check if the chunk has reached or exceeded the specified size
            if chunk_size >= MB_size:
                # If no time was found in the chunk, use a default naming convention
                if not time_prefix:
                    time_prefix = f"chunk{chunk_index:04d}"  # Zero-padded index for better sorting

                # Generate the output file path
                output_file = os.path.join(output_dir, f"{time_prefix}.txt")

                # Ensure the file name is unique to avoid overwriting
                temp_index = 1
                while os.path.exists(output_file):
                    output_file = os.path.join(output_dir, f"{time_prefix}_{temp_index}.txt")
                    temp_index += 1

                # Write the chunk to the output file
                with open(output_file, 'w', encoding='utf-8') as f_out:
                    f_out.writelines(chunk_lines)

                print(f"Created: {output_file}")

                # Reset for the next chunk
                chunk_size = 0
                chunk_lines = []
                time_prefix = None
                chunk_index += 1

        # Handle the last chunk if it has any remaining lines
        if chunk_lines:
            if not time_prefix:
                time_prefix = f"chunk{chunk_index:04d}"
            output_file = os.path.join(output_dir, f"{time_prefix}.txt")
            temp_index = 1
            while os.path.exists(output_file):
                output_file = os.path.join(output_dir, f"{time_prefix}_{temp_index}.txt")
                temp_index += 1
            with open(output_file, 'w', encoding='utf-8') as f_out:
                f_out.writelines(chunk_lines)
            print(f"Created: {output_file}")

    print("文件拆分完成。")

if __name__ == '__main__':
    split_txt_file()
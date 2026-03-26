# -*- coding: utf-8 -*-
"""
Excel 写入工具 (双语版)
"""

import pandas as pd
import os

def append_to_excel(data_dict, excel_path):
    """
    将单次分析的结果字典追加到 Excel 文件。
    如果文件不存在，则创建新文件并写入。
    """
    df_new = pd.DataFrame([data_dict])
    if os.path.exists(excel_path):
        existing = pd.read_excel(excel_path)
        df_combined = pd.concat([existing, df_new], ignore_index=True)
    else:
        df_combined = df_new
    df_combined.to_excel(excel_path, index=False)
    print(f"结果已追加至 {excel_path} / Results appended to {excel_path}")
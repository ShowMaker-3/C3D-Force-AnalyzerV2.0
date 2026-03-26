# -*- coding: utf-8 -*-
"""
交互式力板检测脚本 (check_forceplate_interactive.py) 双语版
功能：遍历指定文件夹内所有C3D文件，显示每个文件的力板类型、校准矩阵、
      处理后的Fz最大值，以及原始通道的最大值（用于对比）。
使用方法：
    python check_forceplate_interactive.py
    然后按提示输入文件夹路径。
"""

import os
import sys
import btk
import numpy as np
import c3d_utils

def clean_path(path):
    return path.strip().lstrip('\u202a').lstrip('\u200e').lstrip('\u200f')

def get_raw_channel_max(acq, label):
    for i in range(acq.GetAnalogs().GetItemNumber()):
        analog = acq.GetAnalog(i)
        if analog.GetLabel() == label:
            values = analog.GetValues()
            if values.ndim == 2 and values.shape[1] > 1:
                return np.nanmax(np.abs(values))
            else:
                return np.nanmax(np.abs(values.flatten()))
    return None

def main():
    print("力板校准检测工具（交互式）/ Force Plate Calibration Checker (Interactive)")
    folder = input("请输入包含C3D文件的文件夹路径: ").strip()
    print("Enter folder path containing C3D files:")
    folder = clean_path(folder)
    if not os.path.isdir(folder):
        print("文件夹不存在或路径无效。/ Folder does not exist or invalid path.")
        return

    c3d_files = [f for f in os.listdir(folder) if f.lower().endswith('.c3d')]
    if not c3d_files:
        print("文件夹中没有C3D文件。/ No C3D files in folder.")
        return

    print(f"\n共找到 {len(c3d_files)} 个C3D文件，开始分析...")
    print(f"Found {len(c3d_files)} C3D files, starting analysis...\n")

    for filename in sorted(c3d_files):
        file_path = os.path.join(folder, filename)
        print(f"文件: {filename} / File: {filename}")
        try:
            acq = c3d_utils.read_c3d(file_path)
            cal, ftype = c3d_utils.get_force_plate_calibration(acq, plate_index=0)
            print(f"  力板类型: {ftype} / Force plate type: {ftype}")
            if cal is not None:
                if cal.shape == (6,6):
                    print(f"  校准矩阵 (对角线): {np.diag(cal)} / Calibration matrix (diagonal): {np.diag(cal)}")
                else:
                    print(f"  校准矩阵: {cal} / Calibration matrix: {cal}")
            else:
                print("  校准矩阵: 无 (可能为 TYPE-2 预缩放) / No calibration matrix (may be TYPE-2 pre-scaled)")

            force_dict, fs = c3d_utils.get_force_data(acq, file_path)
            fz_calibrated = np.max(force_dict['Fz'])
            print(f"  校准后 Fz 最大值: {fz_calibrated:.1f} N / Calibrated Fz max: {fz_calibrated:.1f} N")

            config_data = c3d_utils.get_project_config(file_path)
            channel_map = config_data.get('channels', {})
            fz_label = channel_map.get('force_vz')
            if fz_label:
                raw_max = get_raw_channel_max(acq, fz_label)
                if raw_max is not None:
                    print(f"  原始通道 ({fz_label}) 最大值: {raw_max:.1f} / Raw channel ({fz_label}) max: {raw_max:.1f}")
                else:
                    print(f"  原始通道 {fz_label} 未找到 / Raw channel {fz_label} not found")
            else:
                print("  未配置垂直力通道，跳过原始值对比 / No vertical force channel configured, skipping raw value comparison")
        except Exception as e:
            print(f"  处理出错: {e} / Error: {e}")
        print("-" * 40)

if __name__ == '__main__':
    main()
# -*- coding: utf-8 -*-
"""
自动配置文件生成工具 (auto_config.py) 交互式双语版
功能：运行时先询问文件夹路径，然后自动为文件夹内所有C3D文件配置垂直力通道
      （排除力矩通道），并自动匹配同板的其他分量（Fx, Fy, Mx, My, Mz, COPx, COPy），
      同时根据原始力数据自动判断是否需要翻转坐标系（使向上为正），
      并将翻转标志写入配置文件。
使用方式：
    python auto_config.py
    然后按提示输入文件夹路径
"""

import os
import sys
import json
import btk
import numpy as np
import c3d_utils
import re
import config

def clean_path(path):
    """清理路径中的不可见字符 / Clean invisible characters from path"""
    return path.strip().lstrip('\u202a').lstrip('\u200e').lstrip('\u200f')

def get_channel_info(acq):
    labels = []
    max_vals = []
    for i in range(acq.GetAnalogs().GetItemNumber()):
        analog = acq.GetAnalog(i)
        label = analog.GetLabel()
        values = analog.GetValues()
        if values.ndim == 2 and values.shape[1] > 1:
            max_val = np.max(np.abs(values))
        else:
            max_val = np.max(np.abs(values.flatten()))
        labels.append(label)
        max_vals.append(max_val)
    return labels, max_vals

def is_momentum(label):
    """判断是否为力矩通道（根据常见力矩关键词）"""
    upper = label.upper()
    return any(kw in upper for kw in ['MX', 'MY', 'MZ'])

def extract_plate_number(label):
    numbers = re.findall(r'\d+', label)
    return numbers[-1] if numbers else None

def get_analog_data_dict(acq):
    """
    从 acq 对象中构建所有模拟通道的标签到数据的映射。
    返回字典 {label: array}，数组为一维（若原有多列则取第一列）。
    """
    analog_data = {}
    for i in range(acq.GetAnalogs().GetItemNumber()):
        analog = acq.GetAnalog(i)
        label = analog.GetLabel()
        values = analog.GetValues()
        if values.ndim == 2 and values.shape[1] > 1:
            analog_data[label] = values[:, 0]
        else:
            analog_data[label] = values.flatten()
    return analog_data

def main():
    print("自动配置工具（交互式双语版） / Auto Configuration Tool (Interactive Bilingual)")
    folder = input("请输入要处理的文件夹路径: ").strip()
    print("Enter the folder path to process:")
    folder = clean_path(folder)
    if not os.path.isdir(folder):
        print(f"文件夹不存在: {folder} / Folder does not exist: {folder}")
        return

    c3d_files = [f for f in os.listdir(folder) if f.lower().endswith('.c3d')]
    if not c3d_files:
        print("文件夹中没有 .c3d 文件 / No .c3d files in folder")
        return

    file_channels = {}
    for filename in sorted(c3d_files):
        file_path = os.path.join(folder, filename)
        print(f"\n处理: {filename} / Processing: {filename}")
        acq = c3d_utils.read_c3d(file_path)
        labels, max_vals = get_channel_info(acq)

        candidate_indices = [i for i, label in enumerate(labels) if not is_momentum(label)]
        if not candidate_indices:
            print(f"警告: {filename} 中未找到非力矩通道，跳过 / Warning: No non‑momentum channels found in {filename}, skipping")
            continue

        best_idx = max(candidate_indices, key=lambda i: max_vals[i])
        fz_label = labels[best_idx]

        chan = {
            'force_vz': fz_label,
            'force_vx': None,
            'force_vy': None,
            'torque_x': None,
            'torque_y': None,
            'torque_z': None,
            'cop_x': None,
            'cop_y': None
        }

        plate_num = extract_plate_number(fz_label)
        all_labels_set = set(labels)

        if plate_num:
            # 匹配 Fx, Fy, Mx, My, Mz
            candidates = {
                'force_vx': [f'FX{plate_num}', f'Fx{plate_num}'],
                'force_vy': [f'FY{plate_num}', f'Fy{plate_num}'],
                'torque_x': [f'MX{plate_num}', f'Mx{plate_num}'],
                'torque_y': [f'MY{plate_num}', f'My{plate_num}'],
                'torque_z': [f'MZ{plate_num}', f'Mz{plate_num}'],
            }
            for comp, cand_list in candidates.items():
                for cand in cand_list:
                    if cand in all_labels_set:
                        chan[comp] = cand
                        break

            # 匹配 COP X 和 Y
            cop_candidates_x = [
                f'COP{plate_num}.X',
                f'COP{plate_num}_X',
                f'Force.COPx{plate_num}',
                f'COP_X{plate_num}'
            ]
            cop_candidates_y = [
                f'COP{plate_num}.Y',
                f'COP{plate_num}_Y',
                f'Force.COPy{plate_num}',
                f'COP_Y{plate_num}'
            ]
            for cand in cop_candidates_x:
                if cand in all_labels_set:
                    chan['cop_x'] = cand
                    break
            for cand in cop_candidates_y:
                if cand in all_labels_set:
                    chan['cop_y'] = cand
                    break

            print(f"自动匹配结果 / Auto-matched components:")
            print(f"  Fz = {chan['force_vz']}")
            if chan['force_vx']: print(f"  Fx = {chan['force_vx']}")
            if chan['force_vy']: print(f"  Fy = {chan['force_vy']}")
            if chan['torque_x']: print(f"  Mx = {chan['torque_x']}")
            if chan['torque_y']: print(f"  My = {chan['torque_y']}")
            if chan['torque_z']: print(f"  Mz = {chan['torque_z']}")
            if chan['cop_x']: print(f"  COPx = {chan['cop_x']}")
            if chan['cop_y']: print(f"  COPy = {chan['cop_y']}")
        else:
            print("警告：无法从标签中提取板号，其他分量将保持为空。")
            print("Warning: Could not extract plate number from label, other components will be left empty.")

        # ========== 方向检测与翻转标志 ==========
        # 仅在配置开关开启时进行自动判断
        if config.AUTO_ORIENT_FORCE:
            try:
                # 构建模拟通道数据字典
                analog_data = get_analog_data_dict(acq)
                if fz_label in analog_data:
                    fz_raw = analog_data[fz_label]
                    fz_min = np.min(fz_raw)
                    fz_max = np.max(fz_raw)
                    # 判断是否需要翻转：如果最小值的绝对值大于最大值，则可能坐标系相反
                    if abs(fz_min) > fz_max:
                        chan['flip_orientation'] = True
                        print(f"  方向检测：检测到负向力较大（最小 {fz_min:.2f}, 最大 {fz_max:.2f}），将自动翻转坐标系。")
                        print(f"  Orientation detection: larger negative force detected (min {fz_min:.2f}, max {fz_max:.2f}), will flip orientation.")
                    else:
                        chan['flip_orientation'] = False
                        print(f"  方向检测：方向正常（最小 {fz_min:.2f}, 最大 {fz_max:.2f}），不翻转。")
                        print(f"  Orientation detection: orientation normal (min {fz_min:.2f}, max {fz_max:.2f}), no flip.")
                else:
                    print(f"  方向检测：无法获取垂直力通道 '{fz_label}' 的原始数据，跳过翻转判断。")
                    print(f"  Orientation detection: cannot get raw data for vertical channel '{fz_label}', skipping.")
                    chan['flip_orientation'] = False
            except Exception as e:
                print(f"  方向检测失败: {e}，跳过翻转判断。 / Orientation detection failed: {e}, skipping.")
                chan['flip_orientation'] = False
        else:
            # 如果自动方向检测被关闭，默认不翻转
            chan['flip_orientation'] = False
        # =====================================

        file_channels[filename] = chan

    config_dict = {'file_channels': file_channels}
    output_path = os.path.join(folder, 'project_config.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(config_dict, f, indent=4, ensure_ascii=False)
    print(f"\n配置文件已生成: {output_path} / Configuration file generated: {output_path}")

if __name__ == '__main__':
    main()
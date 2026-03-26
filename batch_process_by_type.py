# -*- coding: utf-8 -*-
"""
按动作类型批量处理脚本 (增强版：自动整理输出文件，双语版)
功能：指定包含C3D文件的文件夹和动作类型，自动调用对应分析脚本处理所有文件，
      并生成总结果汇总表，输出整理到时间戳子文件夹。
"""

import os
import glob
import pandas as pd
import datetime
import shutil
import config

def get_analysis_function(action_type):
    if action_type == 'gait':
        from gait_analysis_finals import analyze_gait
        return analyze_gait
    elif action_type == 'single_jump':
        from run_single_leg_jump_finals import analyze_single_leg_jump
        return analyze_single_leg_jump
    elif action_type == 'double_jump':
        from run_double_leg_jump_finals import analyze_double_leg_jump
        return analyze_double_leg_jump
    elif action_type == 'cmj':
        from jump_analysis_finals import analyze_countermovement_jump
        return analyze_countermovement_jump
    elif action_type == 'cut':
        from cutting_analysis_finals import analyze_cutting
        return analyze_cutting
    else:
        raise ValueError(f"不支持的动作类型: {action_type}，可选: gait, single_jump, double_jump, cmj, cut / Unsupported movement type: {action_type}, options: gait, single_jump, double_jump, cmj, cut")

def process_folder_by_type(data_folder, action_type):
    # ========== 新增：检查项目配置文件 ==========
    config_file = os.path.join(data_folder, 'project_config.json')
    if not os.path.exists(config_file):
        print(f"提示：文件夹 {data_folder} 下没有找到 project_config.json。")
        print(f"Tip: No project_config.json found in folder {data_folder}.")
        print("如果数据格式特殊，建议先运行 configure.py 进行配置。")
        print("If the data format is non‑standard, consider running configure.py first.")
        print("继续使用默认参数...\nContinuing with default parameters...\n")

    data_folder = os.path.normpath(data_folder)
    if not os.path.isdir(data_folder):
        print(f"文件夹不存在: {data_folder} / Folder does not exist: {data_folder}")
        return None

    # 创建时间戳子文件夹
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_subdir = os.path.join(data_folder, f"output_{timestamp}")
    os.makedirs(output_subdir, exist_ok=True)
    print(f"本次运行输出文件夹: {output_subdir}")
    print(f"Output folder for this run: {output_subdir}")

    c3d_files = glob.glob(os.path.join(data_folder, '*.c3d'))
    c3d_files = [os.path.normpath(f) for f in c3d_files]

    if not c3d_files:
        print(f"文件夹 {data_folder} 中没有找到 .c3d 文件。")
        print(f"No .c3d files found in folder {data_folder}.")
        return None

    print(f"找到 {len(c3d_files)} 个 C3D 文件，动作类型: {action_type}")
    print(f"Found {len(c3d_files)} C3D file(s), movement type: {action_type}")

    analyze_func = get_analysis_function(action_type)

    all_results = []
    for f in c3d_files:
        print(f"正在处理: {os.path.basename(f)}")
        print(f"Processing: {os.path.basename(f)}")
        try:
            result = analyze_func(f, output_dir=output_subdir, export_opensim=config.EXPORT_OPENSIM)
            if result:
                result['文件名 Filename'] = os.path.basename(f)
                result['动作类型 Movement type'] = action_type
                all_results.append(result)
        except Exception as e:
            print(f"处理文件 {f} 时出错: {e}")
            print(f"Error processing file {f}: {e}")
            continue

    # ---------- 文件整理 ----------
    # 1. 创建 images 子文件夹并移动图片
    images_dir = os.path.join(output_subdir, 'images')
    os.makedirs(images_dir, exist_ok=True)
    for png in glob.glob(os.path.join(output_subdir, '*.png')):
        shutil.move(png, os.path.join(images_dir, os.path.basename(png)))
    print(f"图片已整理至 {images_dir}")
    print(f"Images moved to {images_dir}")

    # 2. 创建 opensim_files 子文件夹并分类存放 .trc/.mot
    opensim_dir = os.path.join(output_subdir, 'opensim_files')
    os.makedirs(opensim_dir, exist_ok=True)
    for ext in ['*.trc', '*.mot']:
        for file in glob.glob(os.path.join(output_subdir, ext)):
            base = os.path.basename(file).replace('_markers.trc', '').replace('_grf.mot', '')
            file_dir = os.path.join(opensim_dir, base)
            os.makedirs(file_dir, exist_ok=True)
            shutil.move(file, os.path.join(file_dir, os.path.basename(file)))
    print(f"OpenSim 文件已整理至 {opensim_dir}")
    print(f"OpenSim files moved to {opensim_dir}")

    if all_results:
        df = pd.DataFrame(all_results)
        output_path = os.path.join(output_subdir, f'{action_type}_汇总.xlsx')
        df.to_excel(output_path, index=False)
        print(f"本次运行汇总表已保存至 {output_path}")
        print(f"Summary table for this run saved to {output_path}")
        return df
    else:
        print("没有成功处理任何文件。")
        print("No files were successfully processed.")
        return None

if __name__ == '__main__':
    folder = input("请输入C3D文件夹路径: ").strip()
    folder = folder.strip().lstrip('\u202a').lstrip('\u200e').lstrip('\u200f')
    if not os.path.isdir(folder):
        print("路径无效！/ Invalid path!")
        exit()

    print("可选动作类型：gait, single_jump, double_jump, cmj, cut")
    print("Available movement types: gait, single_jump, double_jump, cmj, cut")
    action = input("请输入动作类型: ").strip().lower()
    print("Enter movement type: " + action)  # 用户输入后显示
    try:
        process_folder_by_type(folder, action)
    except ValueError as e:
        print(e)
# -*- coding: utf-8 -*-
"""
动作特征提取器 (action_features.py) 双语版
功能：读取C3D文件，提取垂直力信号的关键特征（腾空时间、峰数量、最小力等），
      并生成归一化力曲线图，供用户人工判断动作类型。
支持批量处理文件夹内所有C3D文件，生成特征汇总表。
使用方式：
    1. 命令行参数：python action_features.py [--plot] <C3D文件或文件夹路径>
         --plot  生成力曲线图（保存在输入路径下的 pred_images 文件夹）
    2. 无参数运行：python action_features.py  # 交互式输入路径，支持多次查询
依赖：btk, numpy, scipy, pandas (可选), matplotlib, plot_utils, c3d_utils
"""

import btk
import numpy as np
from scipy.signal import butter, filtfilt, find_peaks
import os
import glob
import sys

# 尝试导入绘图相关库
try:
    import matplotlib.pyplot as plt
    import plot_utils
    HAS_PLOT = True
except ImportError:
    HAS_PLOT = False
    print("警告：未安装 matplotlib 或 plot_utils，将无法生成曲线图。")
    print("Warning: matplotlib or plot_utils not installed. Plots will not be generated.")

# 尝试导入pandas，如果失败则禁用Excel生成功能
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    print("警告：未安装 pandas，将无法生成Excel汇总表，但仍可打印结果。")
    print("Warning: pandas not installed. Excel summary will not be generated, but results can still be printed.")

# 导入 c3d_utils 以使用其力通道识别和配置功能
import c3d_utils

# ========== 可调参数（用于特征提取） ==========
FORCE_THRESHOLD = 15          # 腾空阈值（N），用于判断力是否归零
PEAK_HEIGHT_RATIO = 0.3       # 峰值高度相对于最大力的比例（降低以检出更多峰）
MIN_PEAK_DISTANCE = 0.1       # 峰间最小距离（秒），可根据需要调整

def extract_features(c3d_file, force_threshold=FORCE_THRESHOLD,
                     peak_height_ratio=PEAK_HEIGHT_RATIO,
                     min_peak_distance=MIN_PEAK_DISTANCE,
                     plot=False):
    """
    分析C3D文件中的垂直力信号，提取特征。
    返回字典，包含以下字段：
        - 'min_force': 力信号最小值 (N)
        - 'max_force': 力信号最大值 (N)
        - 'num_peaks': 检测到的峰数量
        - 'max_flight_duration': 最长腾空持续时间 (s)
        - 'flight_count': 腾空次数
        - 'flight_exists': 是否存在腾空（bool）
    如果 plot=True，将生成归一化力曲线图并保存。
    """
    try:
        reader = btk.btkAcquisitionFileReader()
        reader.SetFilename(c3d_file)
        reader.Update()
        acq = reader.GetOutput()
    except Exception as e:
        print(f"读取C3D失败: {c3d_file} - {e} / Failed to read C3D: {c3d_file} - {e}")
        return None

    # ---------- 获取垂直力数据（通过 c3d_utils，自动适配项目配置）----------
    try:
        force_data, fs = c3d_utils.find_force_channel(acq, c3d_file)
    except ValueError as e:
        # 增强错误提示
        print(f"力通道识别失败: {c3d_file} / Force channel identification failed: {c3d_file}")
        config_data = c3d_utils.get_project_config(c3d_file)
        if config_data:
            channel_map = config_data.get('channels', {})
            if 'force_vz' in channel_map:
                print(f"  配置文件指定了垂直力通道: {channel_map['force_vz']}，但未找到或数据无效")
                print(f"  Config specified vertical force channel: {channel_map['force_vz']}, but not found or invalid")
            else:
                print("  配置文件中未指定垂直力通道 (force_vz)")
                print("  No vertical force channel (force_vz) specified in config")
        else:
            print("  未找到项目配置文件 (project_config.json)，使用自动识别失败")
            print("  No project config file (project_config.json) found, automatic identification failed")
        return None

    # force_data 可能是多维的，提取垂直力列（假设第三列是垂直力，如有多列）
    if force_data.ndim == 2 and force_data.shape[1] >= 3:
        force_raw = force_data[:, 2]
    else:
        force_raw = force_data.flatten()

    force_raw = np.abs(force_raw)  # 取绝对值

    # 低通滤波（50Hz），复用 c3d_utils 的滤波函数
    try:
        force_filt = c3d_utils.lowpass_filter(force_raw, fs)
    except:
        # 如果 c3d_utils 中没有 lowpass_filter，则自己实现
        cutoff = 50
        nyq = 0.5 * fs
        if cutoff < nyq:
            normal_cutoff = cutoff / nyq
            b, a = butter(4, normal_cutoff, btype='low')
            force_filt = filtfilt(b, a, force_raw)
        else:
            force_filt = force_raw

    # ---------- 提取特征 ----------
    min_force = np.min(force_filt)
    max_force = np.max(force_filt)
    if max_force == 0:
        print(f"力信号全零，无法提取特征: {c3d_file} / Force signal all zero, cannot extract features: {c3d_file}")
        return None

    min_distance = max(1, int(min_peak_distance * fs))
    peaks, _ = find_peaks(force_filt, height=max_force * peak_height_ratio, distance=min_distance)
    num_peaks = len(peaks)

    # 检测腾空区域（力低于阈值），统计次数和最长持续时间
    below_thresh = force_filt < force_threshold
    flight_regions = []
    start = None
    for i, val in enumerate(below_thresh):
        if val and start is None:
            start = i
        elif not val and start is not None:
            flight_regions.append((start, i-1))
            start = None
    if start is not None:
        flight_regions.append((start, len(below_thresh)-1))

    flight_count = len(flight_regions)
    max_flight_duration = 0
    for (s, e) in flight_regions:
        duration = (e - s + 1) / fs
        if duration > max_flight_duration:
            max_flight_duration = duration

    features = {
        'min_force': min_force,
        'max_force': max_force,
        'num_peaks': num_peaks,
        'max_flight_duration': max_flight_duration,
        'flight_count': flight_count,
        'flight_exists': flight_count > 0
    }

    # ---------- 可选绘图 ----------
    if plot and HAS_PLOT:
        plot_utils.setup_chinese_font()  # 确保中文显示
        from scipy import interpolate
        original_time = np.arange(len(force_filt)) / fs
        interp_func = interpolate.interp1d(original_time, force_filt, kind='cubic',
                                           fill_value='extrapolate', bounds_error=False)
        norm_time = np.linspace(0, 100, 101)
        norm_force = interp_func(norm_time / 100 * original_time[-1])

        plt.figure(figsize=(8, 4))
        plt.plot(norm_time, norm_force, 'b-', linewidth=1.5)
        plt.xlabel('归一化时间 (%) / Normalized time (%)')
        plt.ylabel('垂直力 (N) / Vertical force (N)')
        plt.title(f'力曲线 - {os.path.basename(c3d_file)}')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        if os.path.isfile(c3d_file):
            base_dir = os.path.dirname(c3d_file)
        else:
            base_dir = c3d_file
        img_dir = os.path.join(base_dir, 'pred_images')
        os.makedirs(img_dir, exist_ok=True)
        img_name = os.path.basename(c3d_file).replace('.c3d', '_features.png')
        img_path = os.path.join(img_dir, img_name)
        plt.savefig(img_path, dpi=150)
        plt.close()
        print(f"  曲线图已保存: {img_path} /  Plot saved: {img_path}")

    return features

def clean_path(path):
    cleaned = path.strip().lstrip('\u202a').lstrip('\u200e').lstrip('\u200f')
    if cleaned.startswith('"') and cleaned.endswith('"'):
        cleaned = cleaned[1:-1]
    return cleaned

def process_single_file(file_path, plot=False):
    if not os.path.isfile(file_path):
        print(f"文件不存在: {file_path} / File does not exist: {file_path}")
        return
    features = extract_features(file_path, plot=plot)
    if features:
        print(f"\n{os.path.basename(file_path)} 特征 / Features:")
        print(f"  最小力 Minimum force: {features['min_force']:.1f} N")
        print(f"  最大力 Maximum force: {features['max_force']:.1f} N")
        print(f"  峰数量 Number of peaks: {features['num_peaks']}")
        print(f"  最长腾空时间 Max flight duration: {features['max_flight_duration']:.3f} s")
        print(f"  腾空次数 Flight count: {features['flight_count']}")
        print(f"  是否存在腾空 Flight exists: {'是 Yes' if features['flight_exists'] else '否 No'}")

def process_folder(folder_path, plot=False):
    folder_path = clean_path(folder_path)
    if not os.path.isdir(folder_path):
        print("文件夹不存在，请检查路径。 / Folder does not exist, please check the path.")
        return

    c3d_files = glob.glob(os.path.join(folder_path, '*.c3d'))
    if not c3d_files:
        print("该文件夹下没有找到 .c3d 文件。 / No .c3d files found in the folder.")
        return

    results = []
    for f in c3d_files:
        print(f"正在处理: {os.path.basename(f)} / Processing: {os.path.basename(f)}")
        features = extract_features(f, plot=plot)
        if features:
            results.append({
                '文件名 Filename': os.path.basename(f),
                '最小力_N Min force (N)': features['min_force'],
                '最大力_N Max force (N)': features['max_force'],
                '峰数量 Number of peaks': features['num_peaks'],
                '最长腾空时间_s Max flight time (s)': features['max_flight_duration'],
                '腾空次数 Flight count': features['flight_count'],
                '是否存在腾空 Flight exists': features['flight_exists']
            })

    if results:
        print("\n特征汇总：/ Feature summary:")
        for res in results:
            print(f"{res['文件名 Filename']}: 最小力Min={res['最小力_N Min force (N)']:.1f}, 峰数Peaks={res['峰数量 Number of peaks']}, 腾空时间Flight={res['最长腾空时间_s Max flight time (s)']:.3f}s, 腾空次数Flight count={res['腾空次数 Flight count']}")

        if HAS_PANDAS:
            df = pd.DataFrame(results)
            output_path = os.path.join(folder_path, '动作特征汇总.xlsx')
            df.to_excel(output_path, index=False)
            print(f"\n特征汇总表已保存至：{output_path} / Feature summary saved to: {output_path}")
        else:
            print("\n（未安装 pandas，未生成Excel文件） / (pandas not installed, Excel file not generated)")
    else:
        print("没有成功提取任何文件的特征。 / No features successfully extracted from any file.")

def interactive_loop():
    print("动作特征提取器（批量处理）/ Action Feature Extractor (Batch)")
    print("输入文件或文件夹路径，输入 'q' 退出。/ Enter file or folder path, enter 'q' to quit.")
    while True:
        path = input("\n请输入路径: ").strip()
        if path.lower() in ('q', 'quit', 'exit'):
            break
        path = clean_path(path)
        if not (os.path.isfile(path) or os.path.isdir(path)):
            print("路径无效，请重新输入。/ Invalid path, please try again.")
            continue

        plot_choice = input("是否生成力曲线图？(y/n, 默认 n): ").strip().lower()
        plot = plot_choice == 'y'

        if os.path.isfile(path):
            process_single_file(path, plot=plot)
        else:
            process_folder(path, plot=plot)

if __name__ == '__main__':
    args = sys.argv[1:]
    plot = False
    path = None

    if '--plot' in args or '-p' in args:
        plot = True
        args = [a for a in args if a not in ('--plot', '-p')]

    if len(args) > 0:
        path = clean_path(args[0])
        if os.path.isfile(path):
            process_single_file(path, plot=plot)
        elif os.path.isdir(path):
            process_folder(path, plot=plot)
        else:
            print("指定的路径无效。/ Invalid path specified.")
    else:
        interactive_loop()
# -*- coding: utf-8 -*-
"""
步态分析脚本 (适配3.0核心模块，包含曲线保存)
功能：读取C3D，调用新模块获取校准后的垂直力数据，检测触地/离地事件，
      计算支撑时间、峰值力，绘图，保存归一化曲线，可选导出OpenSim文件，并自动保存结果到Excel汇总表。
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import interpolate

import config
import c3d_utils
import plot_utils
import excel_utils
from c3d_to_opensim_finals import c3d_to_trc, c3d_to_grf_mot

plot_utils.setup_chinese_font()

def analyze_gait(c3d_file_path, output_dir='.', export_opensim=False):
    acq = c3d_utils.read_c3d(c3d_file_path)
    print("文件读取成功！File loaded successfully!")
    print("="*30)

    force_dict, fs = c3d_utils.get_force_data(acq, c3d_file_path)
    force_raw = force_dict['Fz']
    print(f"垂直力采样率: {fs} Hz / Vertical force sampling rate: {fs} Hz")

    force_raw = np.abs(force_raw)
    force_filt = c3d_utils.lowpass_filter(force_raw, fs)

    # ---------- 保存归一化曲线 ----------
    time = np.arange(len(force_filt)) / fs
    interp_func = interpolate.interp1d(time, force_filt, kind='cubic', fill_value='extrapolate')
    norm_time = np.linspace(0, 100, 101)
    norm_force = interp_func(norm_time / 100 * time[-1])
    curve_path = os.path.join(output_dir, os.path.basename(c3d_file_path).replace('.c3d', '_curve.npy'))
    np.save(curve_path, norm_force)

    # 事件检测
    hs, to = c3d_utils.detect_gait_events(force_filt, fs)
    threshold = config.GAIT_THRESHOLD_RATIO * np.max(force_filt)
    print(f"动态阈值 ({threshold:.1f} N) 检测到 {len(hs)} 次触地，{len(to)} 次离地。")
    print(f"Dynamic threshold ({threshold:.1f} N) detected {len(hs)} foot strikes and {len(to)} toe-offs.")

    if len(hs) > 0 and len(to) > 0:
        n_steps = min(len(hs), len(to))
        stance_times = (to[:n_steps] - hs[:n_steps]) / fs
        avg_stance = np.mean(stance_times)
        print(f"平均支撑时间: {avg_stance:.3f} s / Mean stance time: {avg_stance:.3f} s")
    else:
        avg_stance = None

    peak_force = np.max(force_filt)
    print(f"峰值力: {peak_force:.1f} N / Peak force: {peak_force:.1f} N")

    # 绘图
    events = {'触地 HS': hs, '离地 TO': to}
    save_path = os.path.join(output_dir, os.path.basename(c3d_file_path).replace('.c3d', '_gait.png'))
    plot_utils.plot_force_with_events(
        force=force_filt,
        fs=fs,
        events=events,
        title='Gait Event Detection 步态事件检测',
        save_path=save_path
    )
    print(f"力曲线图已保存至: {save_path} / Force curve plot saved to: {save_path}")

    # OpenSim导出
    if export_opensim:
        trc_path = os.path.join(output_dir, os.path.basename(c3d_file_path).replace('.c3d', '_markers.trc'))
        mot_path = os.path.join(output_dir, os.path.basename(c3d_file_path).replace('.c3d', '_grf.mot'))
        try:
            c3d_to_trc(c3d_file_path, trc_path)
            c3d_to_grf_mot(c3d_file_path, mot_path)
            print("OpenSim 文件导出成功 / OpenSim files exported successfully")
        except Exception as e:
            print(f"OpenSim 导出失败: {e} / OpenSim export failed: {e}")

    # 累积Excel
    raw_folder = os.path.dirname(c3d_file_path)
    result = {
        '文件名 Filename': os.path.basename(c3d_file_path),
        '动作类型 Movement type': '步态 Gait',
        '平均支撑时间_s Mean stance time (s)': avg_stance,
        '峰值力_N Peak force (N)': peak_force,
        '触地次数 Foot strikes': len(hs),
        '离地次数 Toe-offs': len(to),
        '阈值_N Threshold (N)': threshold,
    }
    excel_path = os.path.join(raw_folder, '步态分析累计版 Gait cumulative.xlsx')
    excel_utils.append_to_excel(result, excel_path)
    print(f"结果已追加至: {excel_path} / Results appended to: {excel_path}")

    return result

if __name__ == '__main__':
    test_file = r'你的测试文件路径.c3d'
    test_output = '.'
    result = analyze_gait(test_file, test_output, export_opensim=config.EXPORT_OPENSIM)
    print("分析完成，结果：", result)
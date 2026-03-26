# -*- coding: utf-8 -*-
"""
侧切分析脚本 (适配3.0核心模块，包含曲线保存)
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
from scipy import interpolate

import config
import c3d_utils
import plot_utils
import excel_utils
from c3d_to_opensim_finals import c3d_to_trc, c3d_to_grf_mot

plot_utils.setup_chinese_font()

def analyze_cutting(c3d_file_path, output_dir='.', export_opensim=False):
    acq = c3d_utils.read_c3d(c3d_file_path)
    print("文件读取成功！File loaded successfully!")
    print("="*30)

    force_dict, fs = c3d_utils.get_force_data(acq, c3d_file_path)
    force_raw = force_dict['Fz']
    print(f"垂直力采样率: {fs} Hz / Vertical force sampling rate: {fs} Hz")

    force_raw = np.abs(force_raw)
    force_filt = c3d_utils.lowpass_filter(force_raw, fs)
    time = np.arange(len(force_filt)) / fs

    # ---------- 保存归一化曲线 ----------
    interp_func = interpolate.interp1d(time, force_filt, kind='cubic', fill_value='extrapolate')
    norm_time = np.linspace(0, 100, 101)
    norm_force = interp_func(norm_time / 100 * time[-1])
    curve_path = os.path.join(output_dir, os.path.basename(c3d_file_path).replace('.c3d', '_curve.npy'))
    np.save(curve_path, norm_force)

    min_height = config.FORCE_THRESHOLD
    peaks, _ = find_peaks(force_filt, height=min_height)
    if len(peaks) == 0:
        print("未检测到冲击峰，可能不是侧切动作 / No impact peak detected. Possibly not a cutting movement.")
        return None

    peak_frame = peaks[0]
    peak_force = force_filt[peak_frame]

    left = peak_frame
    while left > 0 and force_filt[left] > min_height:
        left -= 1
    right = peak_frame
    while right < len(force_filt)-1 and force_filt[right] > min_height:
        right += 1
    impulse = np.trapz(force_filt[left:right+1], dx=1/fs)

    print(f"检测到冲击峰: 力值={peak_force:.1f} N, 帧号={peak_frame}, 冲量={impulse:.2f} N·s")
    print(f"Impact peak detected: force={peak_force:.1f} N, frame={peak_frame}, impulse={impulse:.2f} N·s")

    events = {'冲击峰 Impact peak': peak_frame}
    save_path = os.path.join(output_dir, os.path.basename(c3d_file_path).replace('.c3d', '_cutting.png'))
    plot_utils.plot_force_with_events(
        force=force_filt,
        fs=fs,
        events=events,
        title='Cutting Movement Analysis 侧切动作分析',
        save_path=save_path
    )
    print(f"力曲线图已保存至: {save_path} / Force curve plot saved to: {save_path}")

    if export_opensim:
        trc_path = os.path.join(output_dir, os.path.basename(c3d_file_path).replace('.c3d', '_markers.trc'))
        mot_path = os.path.join(output_dir, os.path.basename(c3d_file_path).replace('.c3d', '_grf.mot'))
        try:
            c3d_to_trc(c3d_file_path, trc_path)
            c3d_to_grf_mot(c3d_file_path, mot_path)
            print("OpenSim 文件导出成功 / OpenSim files exported successfully")
        except Exception as e:
            print(f"OpenSim 导出失败: {e} / OpenSim export failed: {e}")

    raw_folder = os.path.dirname(c3d_file_path)
    result = {
        '文件名 Filename': os.path.basename(c3d_file_path),
        '动作类型 Movement type': '侧切 Cutting',
        '峰值力_N Peak force (N)': peak_force,
        '冲量_Ns Impulse (N·s)': impulse,
        '峰值帧 Peak frame': peak_frame,
        '左边界帧 Left boundary': left,
        '右边界帧 Right boundary': right,
    }
    excel_path = os.path.join(raw_folder, '侧切累计版 Cutting cumulative.xlsx')
    excel_utils.append_to_excel(result, excel_path)
    print(f"结果已追加至: {excel_path} / Results appended to: {excel_path}")

    return result

if __name__ == '__main__':
    test_file = r'你的测试文件路径.c3d'
    test_output = '.'
    res = analyze_cutting(test_file, test_output, export_opensim=config.EXPORT_OPENSIM)
    if res:
        print("分析完成，结果：", res)
# -*- coding: utf-8 -*-
"""
跑动单腿跳分析脚本 (适配3.0核心模块，包含曲线保存)
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

def analyze_single_leg_jump(c3d_file_path, output_dir='.', export_opensim=False):
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

    threshold = config.JUMP_THRESHOLD_RATIO * np.max(force_filt)
    in_flight = force_filt < threshold
    flight_starts = np.where(np.diff(in_flight.astype(int)) == 1)[0] + 1
    flight_ends   = np.where(np.diff(in_flight.astype(int)) == -1)[0] + 1

    if len(flight_starts) == 0 or len(flight_ends) == 0:
        print("未检测到腾空区间，可能不是跳跃动作 / No flight phase detected. Possibly not a jump movement.")
        return None

    takeoff_frame = flight_starts[0]
    landing_frame = flight_ends[0]
    print(f"检测到腾空区间：离地帧 {takeoff_frame}，落地帧 {landing_frame}")
    print(f"Flight phase detected: takeoff frame {takeoff_frame}, landing frame {landing_frame}")

    pre_window = min(config.JUMP_PRE_WINDOW, takeoff_frame)
    segment_before = force_filt[takeoff_frame - pre_window : takeoff_frame]
    peaks_before, _ = find_peaks(segment_before,
                                 height=np.max(segment_before)*0.3,
                                 distance=fs*0.1)
    if len(peaks_before) > 0:
        takeoff_peak_idx = peaks_before[-1]
        takeoff_peak_frame = takeoff_frame - pre_window + takeoff_peak_idx
        takeoff_peak_force = force_filt[takeoff_peak_frame]
    else:
        takeoff_peak_frame = takeoff_frame - pre_window + np.argmax(segment_before)
        takeoff_peak_force = force_filt[takeoff_peak_frame]
    print(f"起跳蹬伸峰: {takeoff_peak_force:.1f} N，帧号 {takeoff_peak_frame}")
    print(f"Takeoff push‑off peak: {takeoff_peak_force:.1f} N, frame {takeoff_peak_frame}")

    post_window = min(config.JUMP_POST_WINDOW, len(force_filt) - landing_frame)
    segment_after = force_filt[landing_frame : landing_frame + post_window]
    landing_peak_frame = landing_frame + np.argmax(segment_after)
    landing_peak_force = force_filt[landing_peak_frame]
    print(f"落地冲击峰: {landing_peak_force:.1f} N，帧号 {landing_peak_frame}")
    print(f"Landing impact peak: {landing_peak_force:.1f} N, frame {landing_peak_frame}")

    flight_time = (landing_frame - takeoff_frame) / fs
    print(f"腾空时间: {flight_time:.3f} s / Flight time: {flight_time:.3f} s")

    events = {
        '离地 Takeoff': takeoff_frame,
        '落地 Landing': landing_frame,
        '起跳蹬伸峰 Takeoff peak': takeoff_peak_frame,
        '落地冲击峰 Landing peak': landing_peak_frame,
    }
    save_path = os.path.join(output_dir,
                             os.path.basename(c3d_file_path).replace('.c3d', '_single_jump.png'))
    plot_utils.plot_force_with_events(
        force=force_filt,
        fs=fs,
        events=events,
        title='Single‑Leg Jump Analysis 跑动单腿跳分析',
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
        '动作类型 Movement type': '跑动单腿跳 Single‑leg jump',
        '起跳蹬伸峰_N Takeoff push‑off peak (N)': takeoff_peak_force,
        '腾空时间_s Flight time (s)': flight_time,
        '落地冲击峰_N Landing impact peak (N)': landing_peak_force,
        '离地帧 Takeoff frame': takeoff_frame,
        '落地帧 Landing frame': landing_frame,
    }
    excel_path = os.path.join(raw_folder, '单腿跳累计版 Single‑leg cumulative.xlsx')
    excel_utils.append_to_excel(result, excel_path)
    print(f"结果已追加至: {excel_path} / Results appended to: {excel_path}")

    return result

if __name__ == '__main__':
    test_file = r'你的测试文件路径.c3d'
    test_output = '.'
    res = analyze_single_leg_jump(test_file, test_output, export_opensim=config.EXPORT_OPENSIM)
    if res:
        print("分析完成，结果：", res)
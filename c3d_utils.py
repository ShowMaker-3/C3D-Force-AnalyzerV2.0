# -*- coding: utf-8 -*-
"""
C3D文件通用处理函数（含项目配置支持、矩阵校准、多分量数据获取）
版本：3.1 增加坐标轴方向翻转
依赖：btk, numpy, scipy, json, os
"""

import btk
import numpy as np
from scipy.signal import butter, filtfilt
import config
import json
import os

def get_project_config(c3d_file_path):
    """
    从 C3D 文件所在目录向上查找 project_config.json，并提取针对该文件的通道映射。
    返回配置字典（仅包含该文件的通道信息）。
    """
    folder = os.path.dirname(c3d_file_path)
    config_path = os.path.join(folder, 'project_config.json')
    file_config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            file_channels = config_data.get('file_channels', {})
            filename = os.path.basename(c3d_file_path)
            if filename in file_channels:
                file_config = {'channels': file_channels[filename]}
        except Exception as e:
            print(f"读取配置文件失败: {e}")
    return file_config

def read_c3d(file_path):
    """读取C3D文件，返回acq对象"""
    reader = btk.btkAcquisitionFileReader()
    reader.SetFilename(file_path)
    reader.Update()
    return reader.GetOutput()

def get_force_plate_calibration(acq, plate_index=0):
    try:
        meta = acq.GetMetaData()
        fp_group = meta.GetChild('FORCE_PLATFORM')
        if not fp_group:
            return None, 0
        used = fp_group.GetChild('USED').GetInfo().ToDouble()[0]
        if plate_index >= used:
            return None, 0
        types = fp_group.GetChild('TYPE').GetInfo().ToDouble()
        if len(types) <= plate_index:
            return None, 0
        ftype = int(types[plate_index])
        cal_matrix_param = fp_group.GetChild('CAL_MATRIX')
        if not cal_matrix_param:
            return None, ftype
        cal_data = cal_matrix_param.GetInfo().ToDouble()
        dims = cal_matrix_param.GetInfo().GetDimensions()
        if len(dims) == 2 and dims[0] == 6 and dims[1] == 6:
            cal_matrix = np.array(cal_data).reshape(6,6)
        elif len(dims) == 1 and dims[0] == 6:
            cal_matrix = np.diag(cal_data)
        else:
            cal_matrix = None
        return cal_matrix, ftype
    except Exception as e:
        print(f"解析力板校准矩阵失败: {e}")
        return None, 0

def get_force_data(acq, c3d_file_path=None):
    frames = acq.GetAnalogFrameNumber()
    fs = acq.GetAnalogFrequency()
    zero_arr = np.zeros(frames)
    result = {
        'Fx': zero_arr.copy(),
        'Fy': zero_arr.copy(),
        'Fz': zero_arr.copy(),
        'Mx': zero_arr.copy(),
        'My': zero_arr.copy(),
        'Mz': zero_arr.copy(),
        'COPx': zero_arr.copy(),
        'COPy': zero_arr.copy()
    }

    # 获取按文件配置
    config_data = {}
    if c3d_file_path:
        config_data = get_project_config(c3d_file_path)
    channel_map = config_data.get('channels', {})
    print(f"[力数据] 使用的通道映射: {channel_map}")

    # 构建标签到数据的映射
    analog_data = {}
    for i in range(acq.GetAnalogs().GetItemNumber()):
        analog = acq.GetAnalog(i)
        label = analog.GetLabel()
        values = analog.GetValues()
        analog_data[label] = values

    # 定义分量与配置键的对应
    components = [
        ('Fx', 'force_vx'),
        ('Fy', 'force_vy'),
        ('Fz', 'force_vz'),
        ('Mx', 'torque_x'),
        ('My', 'torque_y'),
        ('Mz', 'torque_z'),
        ('COPx', 'cop_x'),
        ('COPy', 'cop_y')
    ]

    # 从配置中读取各分量
    for comp, key in components:
        label = channel_map.get(key)
        if label and label in analog_data:
            data = analog_data[label]
            if data.ndim == 2 and data.shape[1] > 1:
                # 多列数据取第一列（简化处理）
                result[comp] = data[:, 0]
            else:
                result[comp] = data.flatten()
        # 若未配置，保持零

    # 自动识别 Fz（如果未配置且为零）
    if 'force_vz' not in channel_map or not channel_map.get('force_vz'):
        if np.all(result['Fz'] == 0):
            for label, data in analog_data.items():
                if 'FZ' in label.upper():
                    if data.ndim == 2 and data.shape[1] > 1:
                        result['Fz'] = data[:, 0]
                    else:
                        result['Fz'] = data.flatten()
                    print(f"[力数据] 自动识别垂直力通道: {label}")
                    break

    # 应用力板校准矩阵
    try:
        cal_matrix, ftype = get_force_plate_calibration(acq, plate_index=0)
        if cal_matrix is not None:
            raw = np.column_stack([
                result['Fx'],
                result['Fy'],
                result['Fz'],
                result['Mx'],
                result['My'],
                result['Mz']
            ])
            calibrated = raw @ cal_matrix.T
            result['Fx'] = calibrated[:, 0]
            result['Fy'] = calibrated[:, 1]
            result['Fz'] = calibrated[:, 2]
            result['Mx'] = calibrated[:, 3]
            result['My'] = calibrated[:, 4]
            result['Mz'] = calibrated[:, 5]
            print(f"[力数据] 应用力板校准矩阵成功，Fz 最大值变为: {np.max(result['Fz']):.1f}")
        else:
            print(f"[力数据] 无校准矩阵，使用原始值")
    except Exception as e:
        print(f"[力数据] 应用力板校准矩阵失败，将使用原始值: {e}")

    # ========== 坐标轴方向翻转 ==========
    # 从配置中读取 flip_orientation 标志
    flip_orientation = config_data.get('channels', {}).get('flip_orientation', False)
    if flip_orientation:
        for comp in ['Fx', 'Fy', 'Fz', 'Mx', 'My', 'Mz']:
            result[comp] = -result[comp]
        print(f"[力数据] 已根据配置翻转坐标系（使向上为正）。/ [Force data] Orientation flipped as configured (upward positive).")
    # ===================================

    return result, fs

# 保留旧函数 find_force_channel 供兼容
def find_force_channel(acq, c3d_file_path=None):
    data_dict, fs = get_force_data(acq, c3d_file_path)
    return data_dict['Fz'], fs

def lowpass_filter(data, fs, cutoff=None, order=None):
    if cutoff is None:
        cutoff = config.FILTER_CUTOFF
    if order is None:
        order = config.FILTER_ORDER
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype='low')
    y = filtfilt(b, a, data)
    return y

def detect_gait_events(force, fs):
    threshold = config.GAIT_THRESHOLD_RATIO * np.max(force)
    above = force > threshold
    hs = np.where(np.diff(above.astype(int)) == 1)[0] + 1
    to = np.where(np.diff(above.astype(int)) == -1)[0] + 1
    return hs, to

def detect_jump_events(force, fs):
    threshold = config.JUMP_THRESHOLD_RATIO * np.max(force)
    in_flight = force < threshold
    flight_starts = np.where(np.diff(in_flight.astype(int)) == 1)[0] + 1
    flight_ends = np.where(np.diff(in_flight.astype(int)) == -1)[0] + 1
    if len(flight_starts) == 0 or len(flight_ends) == 0:
        return None, None, None, None
    takeoff = flight_starts[0]
    landing = flight_ends[0]
    pre_window = min(config.JUMP_PRE_WINDOW, takeoff)
    pre_seg = force[takeoff - pre_window : takeoff]
    takeoff_peak_frame = takeoff - pre_window + np.argmax(pre_seg)
    post_window = min(config.JUMP_POST_WINDOW, len(force) - landing)
    post_seg = force[landing : landing + post_window]
    landing_peak_frame = landing + np.argmax(post_seg)
    return takeoff, landing, takeoff_peak_frame, landing_peak_frame
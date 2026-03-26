# -*- coding: utf-8 -*-
"""
C3D 转 OpenSim 格式模块 (双语版)
优先使用配置文件中的通道映射，并应用校准矩阵。
"""

import btk
import numpy as np
import pandas as pd
import os
import c3d_utils

def c3d_to_trc(c3d_file, trc_file, marker_units='mm'):
    """从 C3D 文件中提取所有标记点坐标，保存为 .trc 格式（OpenSim 逆运动学输入）。"""
    reader = btk.btkAcquisitionFileReader()
    reader.SetFilename(c3d_file)
    reader.Update()
    acq = reader.GetOutput()

    num_points = acq.GetPoints().GetItemNumber()
    frames = acq.GetPointFrameNumber()
    freq = acq.GetPointFrequency()

    point_labels = []
    point_data = []
    for i in range(num_points):
        point = acq.GetPoint(i)
        values = point.GetValues()
        if values.ndim == 2 and values.shape[1] == 3:
            point_labels.append(point.GetLabel())
            point_data.append(values)

    if len(point_data) == 0:
        raise ValueError("未找到任何标记点数据 / No marker data found")

    marker_array = np.stack(point_data, axis=1)
    frames = marker_array.shape[0]
    num_points = marker_array.shape[1]

    time = np.arange(frames) / freq

    columns = []
    for label in point_labels:
        columns.extend([f'{label}_X', f'{label}_Y', f'{label}_Z'])
    df = pd.DataFrame(marker_array.reshape(frames, -1), columns=columns)
    df.insert(0, 'Frame', np.arange(1, frames+1))
    df.insert(1, 'Time', time)

    with open(trc_file, 'w') as f:
        f.write('PathFileType\t4\t(X/Y/Z)\t{}\n'.format(os.path.basename(trc_file)))
        f.write('DataRate\tCameraRate\tNumFrames\tNumMarkers\tUnits\tOrigDataRate\tOrigDataStartFrame\tOrigNumFrames\n')
        f.write('{:.2f}\t{:.2f}\t{}\t{}\t{}\t{:.2f}\t1\t{}\n'.format(
            freq, freq, frames, num_points, marker_units, freq, frames))
        f.write('Frame#\tTime\t')
        for label in point_labels:
            f.write(f'{label}\t\t\t')
        f.write('\n')
        f.write('\t\t')
        for i in range(num_points):
            f.write(f'X{i+1}\tY{i+1}\tZ{i+1}\t')
        f.write('\n')

        for _, row in df.iterrows():
            line = f"{int(row['Frame'])}\t{row['Time']:.6f}\t"
            for col in columns:
                line += f"{row[col]:.6f}\t"
            f.write(line + '\n')

    print(f"已生成 .trc 文件: {trc_file} / .trc file generated: {trc_file}")


def c3d_to_grf_mot(c3d_file, mot_file):
    """
    从 C3D 文件中提取地面反作用力和力矩，保存为 .mot 文件（OpenSim 外部载荷）。
    使用校准后的数据，并从项目配置中读取通道映射。
    """
    reader = btk.btkAcquisitionFileReader()
    reader.SetFilename(c3d_file)
    reader.Update()
    acq = reader.GetOutput()

    force_dict, fs = c3d_utils.get_force_data(acq, c3d_file)
    frames = len(force_dict['Fz'])
    time = np.arange(frames) / fs

    df = pd.DataFrame({
        'time': time,
        'ground_force_vx': force_dict['Fx'],
        'ground_force_vy': force_dict['Fy'],
        'ground_force_vz': force_dict['Fz'],
        'ground_force_px': force_dict['COPx'],
        'ground_force_py': force_dict['COPy'],
        'ground_force_pz': np.zeros(frames),
        'ground_torque_x': force_dict['Mx'],
        'ground_torque_y': force_dict['My'],
        'ground_torque_z': force_dict['Mz'],
    })

    with open(mot_file, 'w') as f:
        f.write(f'name {os.path.basename(mot_file)}\n')
        f.write(f'datacolumns {len(df.columns)}\n')
        f.write(f'datarows {frames}\n')
        f.write(f'range {time[0]:.6f}\t{time[-1]:.6f}\n')
        f.write('endheader\n')
        f.write('\t'.join(df.columns) + '\n')
        for _, row in df.iterrows():
            f.write('\t'.join(['{:.6f}'.format(v) for v in row]) + '\n')

    print(f"已生成 .mot 文件: {mot_file} / .mot file generated: {mot_file}")
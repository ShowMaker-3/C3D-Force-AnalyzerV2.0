# -*- coding: utf-8 -*-
"""
统一绘图工具，处理中文字体和事件标记 (双语版)
"""

import matplotlib.pyplot as plt
import numpy as np

def setup_chinese_font():
    """设置 matplotlib 中文字体（黑体）"""
    plt.rcParams['font.sans-serif'] = ['SimHei']
    plt.rcParams['axes.unicode_minus'] = False

def plot_force_with_events(force, fs, events, title, save_path=None):
    """
    绘制力曲线，并在图上标记事件。
    events: 字典，键为事件名称，值为帧索引列表或单个帧。
    """
    time = np.arange(len(force)) / fs
    plt.figure(figsize=(10, 4))
    plt.plot(time, force, 'b-', label='垂直力 Vertical force')
    colors = {'hs': 'g', 'to': 'r', 'takeoff': 'g', 'landing': 'r',
              'takeoff_peak': 'go', 'landing_peak': 'ro'}
    for name, frames in events.items():
        if isinstance(frames, (int, np.integer)):
            frames = [frames]
        for f in frames:
            if name in colors:
                plt.axvline(time[f], color=colors[name][0], linestyle='--', alpha=0.7,
                            label=name if f==frames[0] else '')
            else:
                plt.plot(time[f], force[f], colors.get(name, 'ko'), markersize=8,
                         label=name if f==frames[0] else '')
    plt.xlabel('时间 (s) / Time (s)')
    plt.ylabel('力 (N) / Force (N)')
    plt.title(title)
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=300)
    plt.show()
# -*- coding: utf-8 -*-
"""
图像拟合脚本 (双语版)
功能：对同一文件夹下的归一化曲线进行平均，绘制带标准差带的平均曲线图。
使用方法：
    1. 直接运行：python average_curve_interactive.py
    2. 交互式输入文件夹路径
"""

import numpy as np
import glob
import matplotlib.pyplot as plt
import os
import sys
import plot_utils

def clean_path(path):
    return path.strip().lstrip('\u202a').lstrip('\u200e').lstrip('\u200f')

def main():
    plot_utils.setup_chinese_font()
    print("="*50)
    print("图像拟合脚本（平均曲线）/ Curve Averaging Script (Mean Curve)")
    print("="*50)

    folder = input("请输入包含 *_curve.npy 文件的文件夹路径: ").strip()
    print("Enter folder path containing *_curve.npy files:")
    folder = clean_path(folder)
    if not os.path.isdir(folder):
        print("文件夹不存在，请检查路径。/ Folder does not exist, please check the path.")
        return

    curve_files = glob.glob(os.path.join(folder, '*_curve.npy'))
    if not curve_files:
        print(f"在 {folder} 中没有找到任何 *_curve.npy 文件。")
        print(f"No *_curve.npy files found in {folder}.")
        return

    print(f"找到 {len(curve_files)} 条曲线。/ Found {len(curve_files)} curves.")

    curves = []
    for f in curve_files:
        curve = np.load(f)
        curves.append(curve)

    curves = np.array(curves)
    mean_curve = np.mean(curves, axis=0)
    std_curve = np.std(curves, axis=0)

    x = np.linspace(0, 100, len(mean_curve))

    plt.figure(figsize=(8, 5))
    plt.plot(x, mean_curve, 'b-', linewidth=2, label='平均曲线 Mean curve')
    plt.fill_between(x, mean_curve - std_curve, mean_curve + std_curve,
                     alpha=0.3, color='b', label='±1 标准差 SD')
    plt.xlabel('归一化时间 (%) / Normalized time (%)')
    plt.ylabel('垂直力 (N) / Vertical force (N)')
    plt.title(f'平均力曲线 (n={len(curves)}) / Mean force curve (n={len(curves)})')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    output_name = input("请输入输出图片文件名 (默认 average_curve.png): ").strip()
    if not output_name:
        output_name = 'average_curve.png'
    output_path = os.path.join(folder, output_name)
    plt.savefig(output_path, dpi=300)
    print(f"平均曲线图已保存至：{output_path} / Mean curve saved to: {output_path}")
    plt.show()

if __name__ == '__main__':
    main()
# -*- coding: utf-8 -*-
"""
配置文件，集中管理所有可调参数
Configuration file, centralized management of all adjustable parameters
"""

# 滤波参数 / Filter parameters
FILTER_CUTOFF = 50          # 低通滤波截止频率 (Hz) / Low‑pass cutoff frequency (Hz)
FILTER_ORDER = 4            # 滤波器阶数 / Filter order

# 力通道识别关键词 / Force channel keywords
FORCE_KEYWORDS = ['FZ', 'VGRF', 'Force.Fz']  # 用于自动识别垂直力通道 / Keywords for automatic vertical force channel identification

# 跳跃检测参数 / Jump detection parameters
JUMP_THRESHOLD_RATIO = 0.1  # 腾空阈值 = 最大力 × 该比例 / Flight threshold = max force × ratio
JUMP_PRE_WINDOW = 200        # 离地前搜索起跳峰的窗口（帧数） / Pre‑takeoff search window (frames)
JUMP_POST_WINDOW = 200       # 落地后搜索落地峰的窗口（帧数） / Post‑landing search window (frames)
MIN_FLIGHT_DURATION = 0.05   # 最小腾空时间（秒），用于判断是否为跳跃 / Minimum flight duration (s) to qualify as a jump

# 步态检测参数 / Gait detection parameters
GAIT_THRESHOLD_RATIO = 0.1   # 触地/离地阈值比例（相对于最大力） / Foot strike/toe‑off threshold ratio (relative to max force)
MIN_STANCE_DURATION = 0.1    # 最小支撑时间（秒），用于过滤噪声 / Minimum stance duration (s) for noise filtering

# OpenSim导出控制 / OpenSim export control
EXPORT_OPENSIM = True       # 全局开关：是否导出 OpenSim 文件 / Global switch: whether to export OpenSim files

# 阈值参数 / Threshold parameters
GAIT_THRESHOLD_RATIO = 0.1      # 步态触地/离地阈值比例 / Gait threshold ratio
JUMP_THRESHOLD_RATIO = 0.1      # 跳跃腾空阈值比例 / Jump threshold ratio
FORCE_THRESHOLD = 20             # 腾空绝对阈值 (N)，用于动作预测 / Absolute flight threshold (N) for action prediction

# ========== 坐标轴方向控制 ==========
# 手动配置时是否询问翻转坐标系（使向上为正）
# Ask whether to flip coordinate system (make upward positive) during manual configuration
ASK_FLIP_ORIENTATION = True

# 自动配置时是否自动检测并翻转坐标系（基于原始力数据判断）
# Automatically detect and flip coordinate system during automatic configuration (based on raw force data)
AUTO_ORIENT_FORCE = True
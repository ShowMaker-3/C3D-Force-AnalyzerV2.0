# C3D Force Analyzer / C3D 力数据分析工具箱
中文 | English

Chinese
简介
C3D Force Analyzer 是一个开源的 Python 工具箱，专为运动生物力学研究设计，用于自动化处理 C3D 文件中的力板数据。它支持步态、跳跃、侧切等五种动作分析，提供通道配置、事件检测、批量处理、统计分析以及 OpenSim 文件导出功能。当前稳定版专注于单力板数据，并新增自动坐标系方向检测与翻转功能，确保力信号符合“向上为正”的标准，与 OpenSim 无缝兼容。

主要功能
自动/手动通道配置 – 智能识别力板通道，支持手动交互式选择

五种动作分析 – 步态、单腿跳、双腿跳、原地纵跳、侧切

批量处理 – 一键处理文件夹内所有 C3D 文件

统计分析 – 描述统计、t 检验、方差分析、相关分析，自动生成图表

OpenSim 导出 – 生成 .trc（标记点轨迹）和 .mot（地面反作用力）文件

坐标系方向自动检测 – 判断力板方向并自动翻转，使数据符合“向上为正”标准

中英双语输出 – 所有提示和结果均为中英双语，方便国内外用户

安装

确保已安装 Python 3.7 或更高版本，然后运行以下命令安装所有依赖：

pip install -r requirements.txt

# 克隆仓库
git clone https://github.com/yourusername/C3D-Force-Analyzer-Stable.git
cd C3D-Force-Analyzer-Stable

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate   # Linux/macOS
venv\Scripts\activate      # Windows

# 安装依赖
pip install -r requirements.txt
快速开始
将 C3D 文件放入一个文件夹（例如 data/）。


运行自动配置（或手动配置）：


python auto_config.py
按提示输入文件夹路径，程序将自动生成 project_config.json。

批量处理所有文件：

python batch_process_by_type.py
选择动作类型（gait/single_jump/double_jump/cmj/cut），结果保存在时间戳文件夹中。

运行统计分析：

python stat_analysis.py
选择累积 Excel 文件和指标列，即可得到统计结果和图表。

示例数据
`examples/` 文件夹中提供了五个示例 C3D 文件和一个示例累积 Excel 文件，可用于测试工具箱的完整流程。您可以直接使用这些文件运行 `auto_config.py` 和 `batch_process_by_type.py`，体验通道配置、批量处理和统计分析功能。

文档
详细使用说明请参阅 docs/ 文件夹。

许可证
本项目采用 MIT 许可证 – 详见 LICENSE 文件。

引用
如果您在研究中使用本工具箱，请引用：

text
[Citation – 待添加]


# Introduction
C3D Force Analyzer is an open‑source Python toolbox for automated processing of force plate data in C3D files, designed for biomechanics research. It supports five movement types (gait, single‑leg jump, double‑leg jump, countermovement jump, cutting) and provides channel configuration, event detection, batch processing, statistical analysis, and OpenSim export. This stable version focuses on single‑force‑plate data and includes automatic orientation detection and flipping, ensuring that force signals follow the “upward positive” convention for seamless OpenSim compatibility.

Features
Automatic / manual channel configuration – intelligent channel identification with interactive option

Five movement types – gait, single‑leg jump, double‑leg jump, countermovement jump, cutting

Batch processing – process all C3D files in a folder with one command

Statistical analysis – descriptive stats, t‑tests, ANOVA, correlation, with automatic plots

OpenSim export – generate .trc (marker trajectories) and .mot (ground reaction forces) files

Automatic orientation detection – detects force plate direction and flips data to make upward positive

Bilingual output – all prompts and results are in both Chinese and English

Installation
bash
# Clone the repository
git clone https://github.com/yourusername/C3D-Force-Analyzer-Stable.git
cd C3D-Force-Analyzer-Stable

# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate   # Linux/macOS
venv\Scripts\activate      # Windows

# Install dependencies

Make sure Python 3.7 or higher is installed, then install all dependencies with:

pip install -r requirements.txt
pip install -r requirements.txt
Quick Start
Place your C3D files in a folder (e.g., data/).

Run automatic configuration (or manual):

bash
python auto_config.py
Enter the folder path; a project_config.json will be created.

Process all files:

bash
python batch_process_by_type.py
Choose the movement type (gait/single_jump/double_jump/cmj/cut). Results are saved in a timestamped folder.

Run statistical analysis:

bash
python stat_analysis.py
Select the cumulative Excel file and the metric column to obtain statistics and plots.

Example Data
The `examples/` folder contains five sample C3D files and an example cumulative Excel file to test the full pipeline. You can directly use these files with `auto_config.py` and `batch_process_by_type.py` to explore channel configuration, batch processing, and statistical analysis.
Documentation
For detailed instructions, see the docs/ folder.

License
This project is licensed under the MIT License – see the LICENSE file for details.

Citation
If you use this toolbox in your research, please cite:

text
[Citation – to be added]

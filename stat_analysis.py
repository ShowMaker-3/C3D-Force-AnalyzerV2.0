# -*- coding: utf-8 -*-
"""
交互式统计分析脚本 (双语版，支持无分组输入)
功能：读取累积Excel文件，根据用户指定的指标和分组进行统计分析，并生成图表。
      如果用户不输入分组列，则只输出描述统计和图表，不进行组间比较。
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import os
from statsmodels.stats.multicomp import pairwise_tukeyhsd
import sys
import io
import plot_utils

def clean_path(path):
    """清理路径中的不可见字符"""
    return path.strip().lstrip('\u202a').lstrip('\u200e').lstrip('\u200f')

def get_input(prompt, default=None, allow_none=False):
    """
    获取用户输入，可带默认值；若 allow_none=True，允许用户直接回车返回 None。
    """
    if default is not None:
        val = input(f"{prompt} (默认 {default}): ").strip()
        if val == '':
            return default
    else:
        val = input(f"{prompt}: ").strip()
        if val == '' and allow_none:
            return None
    return val

def main():
    plot_utils.setup_chinese_font()

    print("="*60)
    print("交互式统计分析脚本 / Interactive Statistical Analysis Script")
    print("="*60)

    # 获取文件路径
    file_path = get_input("请输入Excel文件路径 / Enter Excel file path")
    file_path = clean_path(file_path)
    if not os.path.exists(file_path):
        print("文件不存在，请检查路径。 / File does not exist, please check the path.")
        return

    try:
        df = pd.read_excel(file_path)
        print(f"成功读取数据，共 {len(df)} 行，列名：{list(df.columns)}")
        print(f"Data loaded successfully, {len(df)} rows, columns: {list(df.columns)}")
    except Exception as e:
        print(f"读取文件失败：{e} / Failed to read file: {e}")
        return

    print("\n可用列名：/ Available columns:", list(df.columns))
    metric_col = get_input("请输入要分析的指标列名 / Enter the column name for the metric to analyze")
    if metric_col not in df.columns:
        print(f"错误：列 '{metric_col}' 不存在。/ Error: Column '{metric_col}' does not exist.")
        return

    # 获取分组列名（允许为空）
    group_col = get_input("请输入分组列名（用于比较的组别，留空表示不分组）/ Enter the column name for the grouping variable (leave blank for no grouping)", allow_none=True)

    # 相关分析选项
    do_corr = get_input("是否进行相关分析？(y/n, 默认 n) / Perform correlation analysis? (y/n, default n)", default='n').lower()
    corr_x, corr_y = None, None
    if do_corr == 'y':
        corr_x = get_input("请输入相关分析的X列名 / Enter column name for X variable")
        corr_y = get_input("请输入相关分析的Y列名 / Enter column name for Y variable")
        if corr_x not in df.columns or corr_y not in df.columns:
            print("相关分析列名不存在，跳过相关分析。/ Correlation column(s) not found, skipping correlation.")
            corr_x = corr_y = None

    # 输出目录
    output_dir = get_input("请输入输出目录（默认为当前目录下的 stat_results）/ Enter output directory (default: ./stat_results)", default='./stat_results')
    output_dir = clean_path(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    # 设置日志
    log_path = os.path.join(output_dir, 'analysis_log.txt')
    log_file = open(log_path, 'w', encoding='utf-8')
    original_stdout = sys.stdout

    class Tee:
        def __init__(self, *files):
            self.files = files
        def write(self, obj):
            for f in self.files:
                f.write(obj)
                f.flush()
        def flush(self):
            for f in self.files:
                f.flush()

    sys.stdout = Tee(sys.stdout, log_file)
    print(f"日志文件已创建：{log_path} / Log file created: {log_path}")

    # ---------- 数据准备 ----------
    if group_col is not None:
        # 有分组：去除缺失值，保留指标和分组列
        df_clean = df[[metric_col, group_col]].dropna()
        if len(df_clean) < len(df):
            print(f"警告：已删除 {len(df)-len(df_clean)} 行包含缺失值的数据。")
            print(f"Warning: {len(df)-len(df_clean)} rows with missing values removed.")
        groups = df_clean[group_col].unique()
        print(f"分组情况：{groups} / Groups: {groups}")
        # 检查每组样本量
        group_sizes = df_clean.groupby(group_col)[metric_col].count()
        min_group_size = group_sizes.min()
        if min_group_size < 2:
            print(f"警告：某些组样本量不足（最小样本量 = {min_group_size}），无法进行统计检验。只输出描述统计和图表。")
            print(f"Warning: Some groups have insufficient sample size (min size = {min_group_size}). Statistical tests skipped. Only descriptive statistics and plots will be output.")
            perform_test = False
        else:
            perform_test = True
    else:
        # 无分组：直接使用所有数据
        df_clean = df[[metric_col]].dropna()
        print("未指定分组，仅输出描述统计和图表。/ No grouping variable provided. Outputting descriptive statistics and plots only.")
        groups = None
        perform_test = False

    # ---------- 描述统计 ----------
    print("\n描述统计 / Descriptive statistics:")
    if group_col is not None:
        desc = df_clean.groupby(group_col)[metric_col].describe()
        print(desc)
        desc.to_excel(os.path.join(output_dir, 'descriptive_stats.xlsx'))
    else:
        desc = df_clean[metric_col].describe()
        print(desc)
        desc.to_excel(os.path.join(output_dir, 'descriptive_stats.xlsx'))

    # ---------- 分组比较 ----------
    if group_col is not None:
        if len(groups) == 2 and perform_test:
            group1 = df_clean[df_clean[group_col] == groups[0]][metric_col]
            group2 = df_clean[df_clean[group_col] == groups[1]][metric_col]

            # 正态性检验
            if len(group1) < 5000:
                stat1, p1 = stats.shapiro(group1)
                normal1 = p1 > 0.05
            else:
                normal1 = True
            if len(group2) < 5000:
                stat2, p2 = stats.shapiro(group2)
                normal2 = p2 > 0.05
            else:
                normal2 = True

            if not (normal1 and normal2):
                print("数据不符合正态分布，使用 Mann-Whitney U 检验")
                print("Data not normally distributed, using Mann-Whitney U test")
                u_stat, p_value = stats.mannwhitneyu(group1, group2, alternative='two-sided')
                test_name = 'Mann-Whitney U'
                effect_size = u_stat / (len(group1)*len(group2))
                print(f"U 统计量 = {u_stat:.4f}, p = {p_value:.4f}")
            else:
                levene_stat, levene_p = stats.levene(group1, group2)
                equal_var = levene_p > 0.05
                t_stat, p_value = stats.ttest_ind(group1, group2, equal_var=equal_var)
                test_name = '独立样本t检验' + (' (Welch校正)' if not equal_var else '')
                test_name_en = 'Independent samples t-test' + (' (Welch correction)' if not equal_var else '')
                mean1, mean2 = group1.mean(), group2.mean()
                std1, std2 = group1.std(), group2.std()
                pooled_std = np.sqrt(((len(group1)-1)*std1**2 + (len(group2)-1)*std2**2) / (len(group1)+len(group2)-2))
                effect_size = (mean1 - mean2) / pooled_std
                print(f"{test_name} 结果：t = {t_stat:.4f}, p = {p_value:.4f}, 效应量 Cohen's d = {effect_size:.4f}")
                print(f"{test_name_en} result: t = {t_stat:.4f}, p = {p_value:.4f}, effect size Cohen's d = {effect_size:.4f}")

            # 箱线图（两组）
            plt.figure(figsize=(6,4))
            sns.boxplot(data=df_clean, x=group_col, y=metric_col)
            plt.title(f'{metric_col} 分组箱线图 / Boxplot of {metric_col} by {group_col}')
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, 'boxplot.png'), dpi=300)
            plt.show()

        elif len(groups) >= 3 and perform_test:
            data_groups = [df_clean[df_clean[group_col] == g][metric_col] for g in groups]

            levene_stat, levene_p = stats.levene(*data_groups)
            print(f"\n方差齐性检验 (Levene)：统计量 = {levene_stat:.4f}, p = {levene_p:.4f}")
            print(f"Levene's test for homogeneity of variance: statistic = {levene_stat:.4f}, p = {levene_p:.4f}")

            f_stat, p_value = stats.f_oneway(*data_groups)
            print(f"\n单因素方差分析结果：F = {f_stat:.4f}, p = {p_value:.4f}")
            print(f"One-way ANOVA result: F = {f_stat:.4f}, p = {p_value:.4f}")

            if p_value < 0.05:
                tukey = pairwise_tukeyhsd(df_clean[metric_col], df_clean[group_col], alpha=0.05)
                print("\n事后检验 (Tukey HSD)：/ Post-hoc test (Tukey HSD):")
                print(tukey)
                tukey_summary = pd.DataFrame(data=tukey.summary().data[1:], columns=tukey.summary().data[0])
                tukey_summary.to_excel(os.path.join(output_dir, 'tukey_results.xlsx'), index=False)
                print(f"事后检验结果已保存至 tukey_results.xlsx / Post-hoc results saved to tukey_results.xlsx")

            # 箱线图
            plt.figure(figsize=(8,5))
            sns.boxplot(data=df_clean, x=group_col, y=metric_col)
            plt.title(f'{metric_col} 分组箱线图 / Boxplot of {metric_col} by {group_col}')
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, 'boxplot.png'), dpi=300)
            plt.show()

            # 小提琴图
            plt.figure(figsize=(8,5))
            sns.violinplot(data=df_clean, x=group_col, y=metric_col)
            plt.title(f'{metric_col} 分组小提琴图 / Violin plot of {metric_col} by {group_col}')
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, 'violinplot.png'), dpi=300)
            plt.show()
        else:
            if perform_test is False:
                print("样本量不足或未进行检验，仅输出描述统计和箱线图。/ Insufficient sample size or no test performed. Only descriptive statistics and boxplot are shown.")
            # 即使不检验，仍可绘制箱线图（如有多组但样本不足，或单组）
            if len(groups) >= 1:
                plt.figure(figsize=(8,5))
                sns.boxplot(data=df_clean, x=group_col, y=metric_col)
                plt.title(f'{metric_col} 分组箱线图 / Boxplot of {metric_col} by {group_col}')
                plt.tight_layout()
                plt.savefig(os.path.join(output_dir, 'boxplot.png'), dpi=300)
                plt.show()
    else:
        # 无分组：绘制直方图或分布图
        plt.figure(figsize=(8,5))
        sns.histplot(df_clean[metric_col], kde=True)
        plt.title(f'{metric_col} 分布直方图 / Histogram of {metric_col}')
        plt.xlabel(metric_col)
        plt.ylabel('频数 / Frequency')
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'histogram.png'), dpi=300)
        plt.show()

    # ---------- 相关分析 ----------
    if corr_x and corr_y:
        if corr_x in df.columns and corr_y in df.columns:
            corr_data = df[[corr_x, corr_y]].dropna()
            if len(corr_data) > 0:
                r, p_corr = stats.pearsonr(corr_data[corr_x], corr_data[corr_y])
                print(f"\n相关分析：{corr_x} 与 {corr_y}")
                print(f"Correlation analysis: {corr_x} vs {corr_y}")
                print(f"Pearson r = {r:.4f}, p = {p_corr:.4f}")
                plt.figure(figsize=(5,4))
                sns.scatterplot(data=corr_data, x=corr_x, y=corr_y)
                plt.title(f'{corr_x} vs {corr_y} (r={r:.2f})')
                plt.tight_layout()
                plt.savefig(os.path.join(output_dir, 'scatter.png'), dpi=300)
                plt.show()
            else:
                print("相关分析：数据缺失，无法计算。/ Correlation analysis: missing data, cannot compute.")
        else:
            print("相关分析：指定的列不存在。/ Correlation analysis: specified column(s) do not exist.")

    # 恢复标准输出并关闭日志文件
    sys.stdout = original_stdout
    log_file.close()
    print(f"\n所有结果已保存至目录：{output_dir} / All results saved to directory: {output_dir}")

if __name__ == '__main__':
    main()
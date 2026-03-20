import sys
import os
import pandas as pd
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import DEFAULT_CONFIG
from engine.signals import run_analysis
from engine.backtest import run_backtest

# 设置回测天数覆盖 2024-2025
BACKTEST_DAYS = 650 

print("正在计算 [2024-2025] 年度分段收益...")

# 1. 运行分析
res_macro = run_analysis(period="daily", days=BACKTEST_DAYS, config=DEFAULT_CONFIG)

# 2. 纯技术面对比
from engine.signals import _build_score_history
score_tech_only = _build_score_history(
    res_macro["all_indicators"], DEFAULT_CONFIG, macro_engine=None
)

# 3. 执行回测
bt_macro = run_backtest(res_macro["score_history"], res_macro["all_hist"])
bt_tech = run_backtest(score_tech_only, res_macro["all_hist"])

def calc_yearly_return(daily_values_series):
    results = {}
    years = [2024, 2025]
    for year in years:
        year_data = daily_values_series[daily_values_series.index.year == year]
        if not year_data.empty:
            prev_year_data = daily_values_series[daily_values_series.index.year < year]
            base_val = prev_year_data.iloc[-1] if not prev_year_data.empty else year_data.iloc[0]
            end_val = year_data.iloc[-1]
            results[year] = (end_val / base_val) - 1
    return results

# 4. 计算与输出
macro_years = calc_yearly_return(bt_macro['daily_values'])
tech_years = calc_yearly_return(bt_tech['daily_values'])

print("\n" + "="*50)
print(f"{'年份':<10} | {'纯技术面收益':<15} | {'技术+宏观修正收益':<15}")
print("-"*50)
for year in [2024, 2025]:
    m_ret = macro_years.get(year, 0) * 100
    t_ret = tech_years.get(year, 0) * 100
    print(f"{year:<10} | {t_ret:>13.2f}% | {m_ret:>16.2f}%")
print("="*50)
cum_tech = ((1+tech_years.get(2024,0))*(1+tech_years.get(2025,0))-1)*100
cum_macro = ((1+macro_years.get(2024,0))*(1+macro_years.get(2025,0))-1)*100
print(f"{'2年累计':<10} | {cum_tech:>13.2f}% | {cum_macro:>16.2f}%")
print("="*50)

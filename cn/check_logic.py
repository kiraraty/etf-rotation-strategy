import sys
import os
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import DEFAULT_CONFIG
from engine.signals import run_analysis
from engine.backtest import run_backtest

# 使用 README/test_fee.py 建议的高弹性参数
TOP_N = 2
REBALANCE = 3
FEE = 0.00005  # 万0.5
BACKTEST_DAYS = 650

print(f"执行回测: Top{TOP_N}, {REBALANCE}日调仓, 费率{FEE}...")

# 1. 运行分析
res_macro = run_analysis(period="daily", days=BACKTEST_DAYS, config=DEFAULT_CONFIG)

# 2. 纯技术面评分
from engine.signals import _build_score_history
score_tech_only = _build_score_history(
    res_macro["all_indicators"], DEFAULT_CONFIG, macro_engine=None
)

# 3. 回测
bt_macro = run_backtest(res_macro["score_history"], res_macro["all_hist"], top_n=TOP_N, rebalance_days=REBALANCE, fee_rate=FEE)
bt_tech = run_backtest(score_tech_only, res_macro["all_hist"], top_n=TOP_N, rebalance_days=REBALANCE, fee_rate=FEE)

def calc_yearly(df):
    results = {}
    for year in [2024, 2025]:
        y_data = df[df.index.year == year]
        if not y_data.empty:
            prev = df[df.index.year < year]
            base = prev.iloc[-1] if not prev.empty else y_data.iloc[0]
            results[year] = (y_data.iloc[-1] / base) - 1
    return results

macro_y = calc_yearly(bt_macro['daily_values'])
tech_y = calc_yearly(bt_tech['daily_values'])

print("\n" + "="*50)
print(f"最近 2 年年度收益 (参数已修正)")
print("="*50)
print(f"{'年份':<10} | {'纯技术面':<12} | {'技术+宏观修正':<12}")
print("-"*50)
for year in [2024, 2025]:
    print(f"{year:<10} | {tech_y.get(year,0)*100:>10.2f}% | {macro_y.get(year,0)*100:>13.2f}%")
print("="*50)
cum_t = ((1+tech_y.get(2024,0))*(1+tech_y.get(2025,0))-1)*100
cum_m = ((1+macro_y.get(2024,0))*(1+macro_y.get(2025,0))-1)*100
print(f"{'2年累计':<10} | {cum_t:>10.2f}% | {cum_m:>13.2f}%")
print("="*50)

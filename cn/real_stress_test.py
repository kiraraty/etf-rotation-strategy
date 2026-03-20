import sys
import os
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import DEFAULT_CONFIG
from engine.signals import run_analysis
from engine.backtest import run_backtest

TOP_N = 2
REBALANCE = 3
REAL_FEE = 0.00005
SLIPPAGE = 0.001   # 单边0.1% 滑点
BACKTEST_DAYS = 650

print(f"执行 [实盘级] 压力测试...")

res = run_analysis(period="daily", days=BACKTEST_DAYS, config=DEFAULT_CONFIG)

from engine.signals import _build_score_history
score_tech_only = _build_score_history(res["all_indicators"], DEFAULT_CONFIG, macro_engine=None)

bt_macro = run_backtest(res["score_history"], res["all_hist"], top_n=TOP_N, rebalance_days=REBALANCE, fee_rate=REAL_FEE, slippage=SLIPPAGE)
bt_tech = run_backtest(score_tech_only, res["all_hist"], top_n=TOP_N, rebalance_days=REBALANCE, fee_rate=REAL_FEE, slippage=SLIPPAGE)

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

print("\n" + "="*55)
print(f"最近 2 年年度收益 (含0.1%单边滑点)")
print("="*55)
print(f"{'年份':<10} | {'纯技术面(含滑点)':<18} | {'技术+宏观(含滑点)':<18}")
print("-"*55)
for year in [2024, 2025]:
    print(f"{year:<10} | {tech_y.get(year,0)*100:>16.2f}% | {macro_y.get(year,0)*100:>19.2f}%")
print("="*55)
cum_t = ((1+tech_y.get(2024,0))*(1+tech_y.get(2025,0))-1)*100
cum_m = ((1+macro_y.get(2024,0))*(1+macro_y.get(2025,0))-1)*100
print(f"{'2年累计':<10} | {cum_t:>16.2f}% | {cum_m:>19.2f}%")
print(f"{'最大回撤':<10} | {bt_tech['max_drawdown']*100:>15.2f}% | {bt_macro['max_drawdown']*100:>18.2f}%")
print("="*55)

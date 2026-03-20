import sys
import os
import pandas as pd
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import DEFAULT_CONFIG
from engine.signals import run_analysis
from engine.backtest import run_backtest

# --- Optuna 黄金参数 ---
BEST_TOP_N = 2
BEST_REBALANCE = 6
BEST_MACRO_MULT = 1.56
REAL_FEE = 0.00005
SLIPPAGE = 0.0005
BACKTEST_DAYS = 700

print(f"执行 [黄金参数] 年度拆解...")

res = run_analysis(period="daily", days=BACKTEST_DAYS, config=DEFAULT_CONFIG)
macro_engine = res["macro_engine"]

def best_multiplier(date, etf_sector):
    if macro_engine.regimes is None or date not in macro_engine.regimes.index:
        return 1.0
    r = macro_engine.regimes.loc[date]
    mult = BEST_MACRO_MULT
    growth = ['科技', '芯片', '半导体', '恒生科技', '新能源', '光伏', '计算机', '科创50']
    bluechip = ['大盘', '沪深300', '消费', '酒', '证券', '基准']
    defensive = ['红利', '银行', '公用事业', '煤炭', '石油']
    if r['liquidity_on']:
        for s in growth:
            if s in etf_sector: return mult
    if r['capital_on']:
        for s in bluechip:
            if s in etf_sector: return mult
    if not r['liquidity_on'] and not r['capital_on']:
        for s in defensive:
            if s in etf_sector: return mult
    return 1.0

macro_engine.get_multiplier = best_multiplier
from engine.signals import _build_score_history
score_history = _build_score_history(res["all_indicators"], DEFAULT_CONFIG, macro_engine=macro_engine)

bt = run_backtest(score_history, res["all_hist"], top_n=BEST_TOP_N, rebalance_days=BEST_REBALANCE, fee_rate=REAL_FEE, slippage=SLIPPAGE)

def calc_yearly(df):
    results = {}
    for year in [2024, 2025]:
        y_data = df[df.index.year == year]
        if not y_data.empty:
            prev = df[df.index.year < year]
            base = prev.iloc[-1] if not prev.empty else y_data.iloc[0]
            results[year] = (y_data.iloc[-1] / base) - 1
    return results

yearly_ret = calc_yearly(bt['daily_values'])

print("\n" + "="*50)
print(f"黄金参数年度收益报告 (2024 - 2025)")
print("="*50)
print(f"{'年份':<10} | {'年度收益率':<15} | {'最大回撤':<10}")
print("-"*50)
for year in [2024, 2025]:
    y_vals = bt['daily_values'][bt['daily_values'].index.year == year]
    y_mdd = ((y_vals - y_vals.cummax()) / y_vals.cummax()).min() if not y_vals.empty else 0
    print(f"{year:<10} | {yearly_ret.get(year,0)*100:>13.2f}% | {y_mdd*100:>9.2f}%")
print("="*50)
print(f"2年累计收益: {bt['cumulative_return']*100:.2f}%")
print(f"全期夏普比率: {bt['sharpe_ratio']:.2f}")
print("="*50)

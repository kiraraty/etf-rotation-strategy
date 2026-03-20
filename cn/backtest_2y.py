import sys
import os
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import DEFAULT_CONFIG
from engine.signals import run_analysis
from engine.backtest import run_backtest

# 设置回测天数
BACKTEST_DAYS = 500 

print("正在计算 [最近 2 年] 专项回测...")

# 1. 运行带宏观修正的分析
res_macro = run_analysis(period="daily", days=BACKTEST_DAYS, config=DEFAULT_CONFIG)

# 2. 运行纯技术面分析
from engine.signals import _build_score_history
score_tech_only = _build_score_history(
    res_macro["all_indicators"], DEFAULT_CONFIG, macro_engine=None
)

# 3. 运行回测
bt_macro = run_backtest(res_macro["score_history"], res_macro["all_hist"])
bt_tech = run_backtest(score_tech_only, res_macro["all_hist"])

# 4. 输出对比
print("\n" + "="*45)
print("最近 2 年回测对比 (2024.03 - 2026.03)")
print("="*45)
print(f"{'指标':<12} | {'纯技术动能':<12} | {'技术+宏观修正':<12}")
print("-"*45)
print(f"{'累计收益':<12} | {bt_tech['cumulative_return']*100:>10.2f}% | {bt_macro['cumulative_return']*100:>13.2f}%")
print(f"{'夏普比率':<12} | {bt_tech['sharpe_ratio']:>11.2f} | {bt_macro['sharpe_ratio']:>14.2f}")
print(f"{'最大回撤':<12} | {bt_tech['max_drawdown']*100:>10.2f}% | {bt_macro['max_drawdown']*100:>13.2f}%")
print(f"{'胜率':<12} | {bt_tech['win_rate']*100:>11.1f}% | {bt_macro['win_rate']*100:>14.1f}%")
print("="*45)

import sys
import os
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import DEFAULT_CONFIG
from engine.signals import run_analysis
from engine.backtest import run_backtest

# 1. 运行带宏观修正的分析
print("正在计算 [技术+宏观修正] 评分...")
res_macro = run_analysis(period="daily", days=1250, config=DEFAULT_CONFIG)

# 2. 运行纯技术面分析 (Mock 宏观乘数为 1.0)
print("\n正在计算 [纯技术面动能] 评分 (Baseline)...")
# 我们通过清空宏观引擎的 regimes 来达到 mock 目的
res_tech_only = run_analysis(period="daily", days=1250, config=DEFAULT_CONFIG)
# 暴力清除 regimes，让其始终返回 1.0 乘数
if "macro_engine" in res_tech_only:
    res_tech_only["macro_engine"].regimes = None
    
# 重新计算 score_history (不带宏观)
from engine.signals import _build_score_history
res_tech_only["score_history"] = _build_score_history(
    res_tech_only["all_indicators"], DEFAULT_CONFIG, macro_engine=None
)

# 3. 运行回测
print("\n开始对比回测...")
bt_macro = run_backtest(res_macro["score_history"], res_macro["all_hist"])
bt_tech = run_backtest(res_tech_only["score_history"], res_tech_only["all_hist"])

# 4. 输出对比
print("\n" + "="*40)
print(f"{'指标':<10} | {'纯技术动能':<10} | {'技术+宏观修正':<10}")
print("-"*40)
print(f"{'累计收益':<10} | {bt_tech['cumulative_return']*100:>9.2f}% | {bt_macro['cumulative_return']*100:>11.2f}%")
print(f"{'夏普比率':<10} | {bt_tech['sharpe_ratio']:>10.2f} | {bt_macro['sharpe_ratio']:>12.2f}")
print(f"{'最大回撤':<10} | {bt_tech['max_drawdown']*100:>9.2f}% | {bt_macro['max_drawdown']*100:>11.2f}%")
print(f"{'胜率':<10} | {bt_tech['win_rate']*100:>9.1f}% | {bt_macro['win_rate']*100:>11.1f}%")
print("="*40)

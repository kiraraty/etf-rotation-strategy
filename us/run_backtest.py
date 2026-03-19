"""美股ETF轮动回测"""
import sys
import pandas as pd
from data.etf_universe import get_etf_codes, BENCHMARK
from data.fetcher import fetch_all_etfs, fetch_etf_data
from engine.indicators import calc_all_indicators
from engine.scorer import score_cross_section
from engine.backtest import run_backtest
from config import DEFAULT_CONFIG

print("=" * 60)
print("美股ETF轮动策略回测")
print("=" * 60)

# 获取数据
print("\n正在获取ETF数据（5年）...")
etf_codes = get_etf_codes()
all_hist = fetch_all_etfs(etf_codes, period="5y")
bench_df = fetch_etf_data(BENCHMARK, period="5y")

print(f"✓ 获取到{len(all_hist)}只ETF数据")

# 计算指标
print("正在计算指标...")
all_indicators = {}
for code, hist_df in all_hist.items():
    indicators = calc_all_indicators(hist_df, bench_df)
    all_indicators[code] = indicators

# 构建历史评分
print("正在计算评分...")
all_dates = bench_df.index
score_history = {}

for date in all_dates:
    cross_section = {}
    for code, ind_df in all_indicators.items():
        if date in ind_df.index:
            cross_section[code] = ind_df.loc[date]
    if len(cross_section) >= 3:
        cs_df = pd.DataFrame(cross_section).T
        day_scores = score_cross_section(cs_df, DEFAULT_CONFIG.weights)
        score_history[date] = day_scores

score_df = pd.DataFrame(score_history).T.sort_index()
print(f"✓ 共{len(score_df)}个交易日")

# 回测
print("\n正在回测...")
bt_result = run_backtest(score_df, all_hist, top_n=3, rebalance_days=5, fee_rate=0.001)

# 输出结果
print("\n" + "=" * 60)
print("回测结果")
print("=" * 60)
print(f"累计收益率: {bt_result['cumulative_return']*100:.2f}%")
print(f"夏普比率:   {bt_result['sharpe_ratio']:.2f}")
print(f"最大回撤:   {bt_result['max_drawdown']*100:.2f}%")
print(f"胜率:       {bt_result['win_rate']*100:.1f}%")
print("\n策略: 每5天调仓，持有评分Top3的ETF")
print("=" * 60)

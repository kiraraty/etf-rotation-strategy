"""测试修复后的A股回测"""
import sys
sys.path.insert(0, '/Users/kirara/Desktop/astocketf')

import pandas as pd
from engine.backtest import run_backtest

# 读取缓存数据
print("读取数据...")
etf_codes = ['512660', '512200', '512690', '516780', '512720']
all_hist = {}
for code in etf_codes:
    try:
        df = pd.read_parquet(f'.cache/etf_hist_{code}_daily_1250.parquet')
        all_hist[code] = df
    except:
        pass

if len(all_hist) < 3:
    print("数据不足")
    sys.exit(1)

# 构建简单的评分历史(用收益率作为评分)
dates = None
for df in all_hist.values():
    if dates is None:
        dates = df.index
    else:
        dates = dates.intersection(df.index)

scores_dict = {}
for date in sorted(dates):
    day_scores = {}
    for code, df in all_hist.items():
        if date in df.index:
            # 用过去20日收益率作为评分
            idx = df.index.get_loc(date)
            if idx >= 20:
                ret = df.iloc[idx]['close'] / df.iloc[idx-20]['close'] - 1
                day_scores[code] = ret * 100
    if day_scores:
        scores_dict[date] = pd.Series(day_scores)

score_df = pd.DataFrame(scores_dict).T

print(f"数据期间: {score_df.index[0].date()} 至 {score_df.index[-1].date()}")
print(f"交易日数: {len(score_df)}\n")

# 测试不同调仓频率
print("=" * 60)
print("A股ETF调仓频率对比 (Top2, 万0.5费率)")
print("=" * 60)

for days in [1, 2, 3, 4, 5, 7, 10]:
    result = run_backtest(score_df, all_hist, top_n=2, rebalance_days=days, fee_rate=0.00005)
    print(f"{days}天: 收益{result['cumulative_return']*100:.1f}% Sharpe{result['sharpe_ratio']:.2f} 回撤{result['max_drawdown']*100:.1f}%")

print("=" * 60)

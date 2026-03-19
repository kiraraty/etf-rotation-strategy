"""检查回测逻辑是否有问题"""
import sys
sys.path.insert(0, '/Users/kirara/Desktop/astocketf')

import pandas as pd
from engine.backtest import run_backtest

# 读取数据
etf_codes = ['512660', '512200', '512690']
all_hist = {}
for code in etf_codes:
    try:
        df = pd.read_parquet(f'.cache/etf_hist_{code}_daily_1250.parquet')
        all_hist[code] = df
    except:
        pass

# 构建评分
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
            idx = df.index.get_loc(date)
            if idx >= 20:
                ret = df.iloc[idx]['close'] / df.iloc[idx-20]['close'] - 1
                day_scores[code] = ret * 100
    if day_scores:
        scores_dict[date] = pd.Series(day_scores)

score_df = pd.DataFrame(scores_dict).T

print("=" * 60)
print("回测逻辑检查")
print("=" * 60)
print(f"\n数据期间: {score_df.index[0].date()} 至 {score_df.index[-1].date()}")
print(f"总交易日: {len(score_df)}")

# 手动模拟前10天的回测逻辑
print("\n前10天回测逻辑检查:")
print("-" * 60)

top_n = 2
rebalance_days = 3
holdings = {}
last_rebalance = 0
portfolio_value = 1.0

for i in range(min(10, len(score_df))):
    date = score_df.index[i]
    print(f"\n第{i}天 ({date.date()}):")

    # 调仓检查
    if i == 0:
        print("  [首日建仓]")
        day_scores = score_df.loc[date].dropna().sort_values(ascending=False)
        holdings = {code: 1.0/top_n for code in day_scores.head(top_n).index}
        print(f"  用当日评分: {day_scores.to_dict()}")
        print(f"  持仓: {holdings}")
        print(f"  不计算收益，跳过")
        last_rebalance = 0
        continue

    if i - last_rebalance >= rebalance_days:
        print(f"  [调仓] (距上次{i - last_rebalance}天)")
        prev_date = score_df.index[i-1]
        day_scores = score_df.loc[prev_date].dropna().sort_values(ascending=False)
        print(f"  用昨日({prev_date.date()})评分: {day_scores.to_dict()}")
        new_holdings = {code: 1.0/top_n for code in day_scores.head(top_n).index}
        print(f"  新持仓: {new_holdings}")
        holdings = new_holdings
        last_rebalance = i
    else:
        print(f"  [持有] (距上次{i - last_rebalance}天，未到调仓)")

    # 计算收益
    print(f"  当前持仓: {holdings}")
    day_return = 0
    for code, weight in holdings.items():
        if code in all_hist and date in all_hist[code].index:
            price_df = all_hist[code]
            prev_date = score_df.index[i-1]
            if prev_date in price_df.index:
                prev_close = price_df.loc[prev_date, 'close']
                curr_close = price_df.loc[date, 'close']
                ret = curr_close / prev_close - 1
                day_return += weight * ret
                print(f"    {code}: {prev_close:.2f} -> {curr_close:.2f} = {ret*100:.2f}%")

    portfolio_value *= (1 + day_return)
    print(f"  当日收益: {day_return*100:.2f}%")
    print(f"  组合净值: {portfolio_value:.4f}")

print("\n" + "=" * 60)

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

HK_DIR = '/Users/kirara/Desktop/etf-rotation-strategy/hk'
sys.path.insert(0, HK_DIR)
from data.etf_universe import get_etf_codes

all_hist = {}
cache_dir = os.path.join(HK_DIR, 'data/.cache')
for code in get_etf_codes():
    file_path = f"{cache_dir}/etf_hist_{code.replace('.','_')}.csv"
    if os.path.exists(file_path):
        df = pd.read_csv(file_path, index_col=0, parse_dates=True)
        df.index = df.index.tz_localize(None)
        all_hist[code] = df

all_dates = sorted(set().union(*(df.index for df in all_hist.values())))
start_date = datetime.now() - timedelta(days=5*365)
all_dates = [d for d in all_dates if d >= start_date]

def run_backtest_core(dates, all_hist, top_n, rebalance_days, ma_window, mom_window, fee_rate=0.001):
    portfolio_value = 1.0
    daily_values = []
    holdings = {}
    last_rebalance = 0
    bench_df = all_hist["2800.HK"]
    bench_ma = bench_df['close'].rolling(window=ma_window).mean()

    for i, date in enumerate(dates):
        if i > 0 and (i - last_rebalance >= rebalance_days):
            prev_date = dates[i-1]
            is_bull = False
            if prev_date in bench_df.index:
                is_bull = bench_df.loc[prev_date, 'close'] > bench_ma.loc[prev_date]
            
            day_scores = {}
            for code, df in all_hist.items():
                if prev_date in df.index:
                    idx = df.index.get_loc(prev_date)
                    if idx >= mom_window:
                        ret = df.iloc[idx]['close'] / df.iloc[idx-mom_window]['close'] - 1
                        day_scores[code] = ret
            
            candidates = [c for c, s in day_scores.items() if s > 0]
            new_holdings = {}
            if is_bull and candidates:
                sorted_candidates = sorted(candidates, key=lambda x: day_scores[x], reverse=True)
                top_codes = sorted_candidates[:top_n]
                new_holdings = {code: 1.0/len(top_codes) for code in top_codes}
            
            turnover = sum(abs(new_holdings.get(c, 0) - holdings.get(c, 0)) for c in set(new_holdings)|set(holdings))
            portfolio_value *= (1 - turnover * fee_rate)
            holdings = new_holdings
            last_rebalance = i
            
        day_return = 0
        if holdings:
            for code, weight in holdings.items():
                if date in all_hist[code].index and i > 0 and dates[i-1] in all_hist[code].index:
                    ret = all_hist[code].loc[date, 'close'] / all_hist[code].loc[dates[i-1], 'close'] - 1
                    day_return += weight * ret
        
        portfolio_value *= (1 + day_return)
        daily_values.append(portfolio_value)
    
    v = pd.Series(daily_values)
    return v

# 最佳参数
best_params = {'top_n': 2, 'rebalance_days': 19, 'ma_window': 71, 'mom_window': 35}
v = run_backtest_core(all_dates, all_hist, **best_params)

cum_ret = v.iloc[-1] - 1
days = len(v)
years = days / 252.0
ann_ret = (1 + cum_ret) ** (1/years) - 1

print(f"总交易天数: {days}")
print(f"总累计收益: {cum_ret*100:.2f}%")
print(f"总年化收益: {ann_ret*100:.2f}%")

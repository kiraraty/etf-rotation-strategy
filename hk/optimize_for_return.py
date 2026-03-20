import sys
import os
import pandas as pd
import numpy as np
import optuna
from datetime import datetime, timedelta

HK_DIR = '/Users/kirara/Desktop/etf-rotation-strategy/hk'
sys.path.insert(0, HK_DIR)
from data.etf_universe import get_etf_codes

# 1. 加载数据
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

# 数据集
split_idx = int(len(all_dates) * 0.6)
train_dates = all_dates[:split_idx]
test_dates = all_dates[split_idx:]

def run_backtest_core(dates, all_hist, top_n, rebalance_days, mom_window, fee_rate=0.001):
    portfolio_value = 1.0
    daily_values = []
    holdings = {}
    last_rebalance = 0

    for i, date in enumerate(dates):
        if i > 0 and (i - last_rebalance >= rebalance_days):
            prev_date = dates[i-1]
            
            day_scores = {}
            for code, df in all_hist.items():
                if prev_date in df.index:
                    idx = df.index.get_loc(prev_date)
                    if idx >= mom_window:
                        ret = df.iloc[idx]['close'] / df.iloc[idx-mom_window]['close'] - 1
                        day_scores[code] = ret
            
            # 仅保留正收益（绝对动量），取消大盘均线择时
            candidates = [c for c, s in day_scores.items() if s > 0]
            new_holdings = {}
            if candidates:
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

def get_metrics(v):
    cum_ret = v.iloc[-1] - 1
    mdd = ((v - v.cummax()) / v.cummax()).min()
    return cum_ret, mdd

def objective(trial):
    top_n = trial.suggest_int('top_n', 2, 5)
    rebalance_days = trial.suggest_int('rebalance_days', 5, 20)
    mom_window = trial.suggest_int('mom_window', 10, 40)
    
    v = run_backtest_core(train_dates, all_hist, top_n, rebalance_days, mom_window)
    cum_ret, mdd = get_metrics(v)
    
    # 目标：最大化收益，但如果回撤超过 30%，给予惩罚
    if mdd < -0.30:
        return cum_ret + (mdd * 2) 
    return cum_ret

print("开始以【收益最大化】为目标的优化...")
study = optuna.create_study(direction='maximize')
study.optimize(objective, n_trials=50, show_progress_bar=False)

best = study.best_params
print(f"最优参数: {best}")

v_all = run_backtest_core(all_dates, all_hist, best['top_n'], best['rebalance_days'], best['mom_window'])
cum_all, mdd_all = get_metrics(v_all)
ann_all = (1 + cum_all) ** (252 / len(v_all)) - 1

print(f"5年总累计收益: {cum_all*100:.2f}%")
print(f"5年年化收益: {ann_all*100:.2f}%")
print(f"最大回撤: {mdd_all*100:.2f}%")

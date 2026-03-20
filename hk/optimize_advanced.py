import sys
import os
import pandas as pd
import numpy as np
import optuna
from datetime import datetime, timedelta

# 环境准备
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

# 数据集切分 (60% 训练, 40% 测试)
split_idx = int(len(all_dates) * 0.6)
train_dates = all_dates[:split_idx]
test_dates = all_dates[split_idx:]

# 2. 核心回测函数
def run_backtest_core(dates, all_hist, top_n, rebalance_days, ma_window, mom_window, fee_rate=0.001):
    portfolio_value = 1.0
    daily_values = []
    holdings = {}
    last_rebalance = 0
    
    # 预计算大盘择时均线
    bench_df = all_hist["2800.HK"]
    bench_ma = bench_df['close'].rolling(window=ma_window).mean()

    for i, date in enumerate(dates):
        if i > 0 and (i - last_rebalance >= rebalance_days):
            prev_date = dates[i-1]
            
            # 大盘择时
            is_bull = False
            if prev_date in bench_df.index:
                is_bull = bench_df.loc[prev_date, 'close'] > bench_ma.loc[prev_date]
            
            # 计算动量
            day_scores = {}
            for code, df in all_hist.items():
                if prev_date in df.index:
                    idx = df.index.get_loc(prev_date)
                    if idx >= mom_window:
                        ret = df.iloc[idx]['close'] / df.iloc[idx-mom_window]['close'] - 1
                        day_scores[code] = ret
            
            # 绝对动量过滤 (score > 0)
            candidates = [c for c, s in day_scores.items() if s > 0]
            
            new_holdings = {}
            if is_bull and candidates:
                sorted_candidates = sorted(candidates, key=lambda x: day_scores[x], reverse=True)
                top_codes = sorted_candidates[:top_n]
                new_holdings = {code: 1.0/len(top_codes) for code in top_codes}
            
            # 计算费率 (含滑点)
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
    
    # 计算指标
    v = pd.Series(daily_values)
    rets = v.pct_change().dropna()
    if rets.std() == 0: return 0
    sharpe = rets.mean() / rets.std() * np.sqrt(252)
    return sharpe, v

# 3. Optuna 目标函数
def objective(trial):
    top_n = trial.suggest_int('top_n', 2, 6)
    rebalance_days = trial.suggest_int('rebalance_days', 5, 22)
    ma_window = trial.suggest_int('ma_window', 20, 120)
    mom_window = trial.suggest_int('mom_window', 10, 60)
    
    sharpe, _ = run_backtest_core(train_dates, all_hist, top_n, rebalance_days, ma_window, mom_window)
    return sharpe

# 4. 执行优化
print(f"训练周期: {train_dates[0].date()} 至 {train_dates[-1].date()}")
print(f"测试周期: {test_dates[0].date()} 至 {test_dates[-1].date()}")
print("开始 Optuna 50 次迭代优化...")

study = optuna.create_study(direction='maximize')
study.optimize(objective, n_trials=50, show_progress_bar=True)

# 5. 验证结果
best = study.best_params
print("\n" + "="*30 + " 优化完成 " + "="*30)
print(f"最优参数: {best}")

# 在训练集跑一次看表现
train_sharpe, train_v = run_backtest_core(train_dates, all_hist, **best)
# 在测试集跑一次看表现
test_sharpe, test_v = run_backtest_core(test_dates, all_hist, **best)

def final_print(name, v, sharpe):
    cum_ret = (v.iloc[-1] - 1) * 100
    mdd = ((v - v.cummax()) / v.cummax()).min() * 100
    print(f"{name} -> 累计收益: {cum_ret:>8.2f}%, 夏普: {sharpe:>6.2f}, 最大回撤: {mdd:>8.2f}%")

final_print("训练集 (In-Sample) ", train_v, train_sharpe)
final_print("测试集 (Out-of-Sample)", test_v, test_sharpe)


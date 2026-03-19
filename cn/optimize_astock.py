"""A股ETF参数优化"""
import sys
sys.path.insert(0, '/Users/kirara/Desktop/astocketf')

import optuna
import pandas as pd
from engine.backtest import run_backtest

# 读取优化后的ETF池
print("读取数据...")
from data.etf_universe import get_etf_codes
etf_codes = get_etf_codes()
all_hist = {}
for code in etf_codes:
    try:
        df = pd.read_parquet(f'.cache/etf_hist_{code}_daily_1250.parquet')
        all_hist[code] = df
    except:
        pass

print(f"成功读取{len(all_hist)}个ETF")
if len(all_hist) < 5:
    print("数据不足")
    sys.exit(1)

# 构建评分历史
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

# 分训练集和测试集
split_idx = int(len(score_df) * 0.6)
train_scores = score_df.iloc[:split_idx]
test_scores = score_df.iloc[split_idx:]

print(f"训练集: {len(train_scores)}天")
print(f"测试集: {len(test_scores)}天\n")

def objective(trial):
    top_n = trial.suggest_int('top_n', 2, 5)
    rebalance_days = trial.suggest_int('rebalance_days', 1, 10)

    result = run_backtest(train_scores, all_hist, top_n, rebalance_days, 0.00005)
    return result['sharpe_ratio']

print("开始优化...")
study = optuna.create_study(direction='maximize')
study.optimize(objective, n_trials=50, show_progress_bar=True)

print("\n" + "=" * 60)
print("优化结果")
print("=" * 60)
print(f"最优参数: {study.best_params}")
print(f"训练集夏普: {study.best_value:.2f}")

# 测试集验证
best_params = study.best_params
test_result = run_backtest(test_scores, all_hist,
                          best_params['top_n'],
                          best_params['rebalance_days'],
                          0.00005)

print("\n测试集表现:")
print(f"累计收益: {test_result['cumulative_return']*100:.2f}%")
print(f"夏普比率: {test_result['sharpe_ratio']:.2f}")
print(f"最大回撤: {test_result['max_drawdown']*100:.2f}%")
print(f"胜率: {test_result['win_rate']*100:.1f}%")

# 对比原始参数
print("\n原始参数(Top2, 3天调仓):")
baseline = run_backtest(test_scores, all_hist, 2, 3, 0.00005)
print(f"累计收益: {baseline['cumulative_return']*100:.2f}%")
print(f"夏普比率: {baseline['sharpe_ratio']:.2f}")
print("=" * 60)

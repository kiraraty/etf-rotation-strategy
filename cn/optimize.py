"""A股ETF Optuna参数优化"""
import sys
import optuna
import pandas as pd
from config import DEFAULT_CONFIG
from engine.signals import run_analysis
from engine.backtest import run_backtest

print("正在获取数据...")
result = run_analysis(period="daily", days=1250, config=DEFAULT_CONFIG)

if not result or result["score_history"].empty:
    print("数据不足")
    sys.exit(1)

score_df = result["score_history"]
all_hist = result["all_hist"]

# 分训练集和测试集
split_idx = int(len(score_df) * 0.6)
train_scores = score_df.iloc[:split_idx]
test_scores = score_df.iloc[split_idx:]

print(f"训练集: {len(train_scores)}天")
print(f"测试集: {len(test_scores)}天\n")

def objective(trial):
    top_n = trial.suggest_int('top_n', 2, 8)
    rebalance_days = trial.suggest_int('rebalance_days', 3, 15)
    
    result = run_backtest(train_scores, all_hist, top_n, rebalance_days, 0.001)
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
                          0.001)

print("\n测试集表现:")
print(f"累计收益: {test_result['cumulative_return']*100:.2f}%")
print(f"夏普比率: {test_result['sharpe_ratio']:.2f}")
print(f"最大回撤: {test_result['max_drawdown']*100:.2f}%")

# 对比原始参数
baseline = run_backtest(test_scores, all_hist, 3, 5, 0.001)
print("\n原始参数(Top3, 5天):")
print(f"累计收益: {baseline['cumulative_return']*100:.2f}%")
print(f"夏普比率: {baseline['sharpe_ratio']:.2f}")
print("=" * 60)

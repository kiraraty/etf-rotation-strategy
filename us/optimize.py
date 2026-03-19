"""Optuna参数优化"""
import optuna
import pandas as pd
from data.etf_universe import get_etf_codes, BENCHMARK
from data.fetcher import fetch_all_etfs, fetch_etf_data
from engine.indicators import calc_all_indicators
from engine.scorer import score_cross_section
from engine.backtest import run_backtest
from config import DEFAULT_CONFIG

print("正在获取数据...")
etf_codes = get_etf_codes()
all_hist = fetch_all_etfs(etf_codes, period="5y")
bench_df = fetch_etf_data(BENCHMARK, period="5y")

# 计算指标
all_indicators = {}
for code, hist_df in all_hist.items():
    indicators = calc_all_indicators(hist_df, bench_df)
    all_indicators[code] = indicators

# 构建评分历史
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

# 分训练集和测试集（前3年训练，后2年测试）
split_idx = int(len(score_df) * 0.6)
train_scores = score_df.iloc[:split_idx]
test_scores = score_df.iloc[split_idx:]

print(f"训练集: {len(train_scores)}天")
print(f"测试集: {len(test_scores)}天\n")

def objective(trial):
    """优化目标：最大化夏普比率"""
    # 优化参数
    top_n = trial.suggest_int('top_n', 2, 8)
    rebalance_days = trial.suggest_int('rebalance_days', 3, 15)
    
    # 在训练集上回测
    result = run_backtest(train_scores, all_hist, top_n, rebalance_days, 0.00005)

    return result['sharpe_ratio']

# 运行优化
print("开始优化...")
study = optuna.create_study(direction='maximize')
study.optimize(objective, n_trials=50, show_progress_bar=True)

print("\n" + "=" * 60)
print("优化结果")
print("=" * 60)
print(f"最优参数: {study.best_params}")
print(f"训练集夏普: {study.best_value:.2f}")

# 在测试集上验证
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
print("\n原始参数(Top3, 5天调仓):")
baseline = run_backtest(test_scores, all_hist, 3, 5, 0.00005)
print(f"累计收益: {baseline['cumulative_return']*100:.2f}%")
print(f"夏普比率: {baseline['sharpe_ratio']:.2f}")
print("=" * 60)

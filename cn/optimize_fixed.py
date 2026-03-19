"""A股ETF Optuna优化(修复版)"""
import sys
import optuna
import pandas as pd
import akshare as ak
from pathlib import Path

sys.path.insert(0, '/Users/kirara/Desktop/astocketf')
from config import DEFAULT_CONFIG
from engine.indicators import calc_all_indicators
from engine.scorer import score_cross_section
from engine.backtest import run_backtest

# ETF池
ETF_CODES = ['512660', '512200', '512690', '516780', '512720', 
             '159915', '512480', '512010', '515790', '159949']

print("获取数据...")
all_hist = {}
for code in ETF_CODES:
    try:
        df = ak.fund_etf_hist_em(symbol=code, period="daily", adjust="qfq")
        if df is not None and len(df) > 0:
            df = df.rename(columns={'日期': 'date', '开盘': 'open', '收盘': 'close',
                                   '最高': 'high', '最低': 'low', '成交量': 'volume',
                                   '成交额': 'amount'})
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date').sort_index()
            all_hist[code] = df.tail(1250)
    except:
        pass

if len(all_hist) < 3:
    print("数据不足")
    sys.exit(1)

# 获取基准(沪深300ETF)
bench_df = ak.fund_etf_hist_em(symbol="510300", period="daily", adjust="qfq")
bench_df = bench_df.rename(columns={'日期': 'date', '收盘': 'close'})
bench_df['date'] = pd.to_datetime(bench_df['date'])
bench_df = bench_df.set_index('date').sort_index().tail(1250)

# 计算指标
all_indicators = {}
for code, hist_df in all_hist.items():
    indicators = calc_all_indicators(hist_df, bench_df)
    all_indicators[code] = indicators

# 构建评分历史
all_dates = None
for ind_df in all_indicators.values():
    dates = ind_df.dropna(how='all').index
    all_dates = dates if all_dates is None else all_dates.intersection(dates)

scores_dict = {}
for date in sorted(all_dates):
    cross_section = {}
    for code, ind_df in all_indicators.items():
        if date in ind_df.index:
            cross_section[code] = ind_df.loc[date]
    if len(cross_section) >= 3:
        cs_df = pd.DataFrame(cross_section).T
        scores_dict[date] = score_cross_section(cs_df, DEFAULT_CONFIG.weights)

score_df = pd.DataFrame(scores_dict).T

print(f"数据期间: {score_df.index[0].date()} 至 {score_df.index[-1].date()}")
print(f"交易日数: {len(score_df)}\n")

# 分训练集和测试集
split_idx = int(len(score_df) * 0.6)
train_scores = score_df.iloc[:split_idx]
test_scores = score_df.iloc[split_idx:]

print(f"训练集: {len(train_scores)}天")
print(f"测试集: {len(test_scores)}天\n")

def objective(trial):
    top_n = trial.suggest_int('top_n', 2, 8)
    rebalance_days = trial.suggest_int('rebalance_days', 3, 15)
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
print("=" * 60)

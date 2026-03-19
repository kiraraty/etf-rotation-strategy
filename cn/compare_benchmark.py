"""对比策略和基准表现"""
import sys
import pandas as pd
import akshare as ak
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
            df = df.rename(columns={'日期': 'date', '收盘': 'close'})
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date').sort_index()
            all_hist[code] = df.tail(1250)
    except:
        pass

# 基准
bench_df = ak.fund_etf_hist_em(symbol="510300", period="daily", adjust="qfq")
bench_df = bench_df.rename(columns={'日期': 'date', '收盘': 'close'})
bench_df['date'] = pd.to_datetime(bench_df['date'])
bench_df = bench_df.set_index('date').sort_index().tail(1250)

# 计算指标和评分
all_indicators = {}
for code, hist_df in all_hist.items():
    indicators = calc_all_indicators(hist_df, bench_df)
    all_indicators[code] = indicators

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

# 测试集
split_idx = int(len(score_df) * 0.6)
test_scores = score_df.iloc[split_idx:]

# 策略回测
strategy = run_backtest(test_scores, all_hist, 3, 8, 0.00005)

# 基准表现
test_dates = test_scores.index
bench_test = bench_df.loc[bench_df.index.isin(test_dates)].sort_index()
bench_returns = bench_test['close'].pct_change().fillna(0)
bench_cumret = (1 + bench_returns).cumprod() - 1
bench_final = bench_cumret.iloc[-1]

# 计算基准回撤
bench_cummax = (1 + bench_cumret).cummax()
bench_dd = ((1 + bench_cumret) - bench_cummax) / bench_cummax
bench_maxdd = bench_dd.min()

print("\n" + "=" * 60)
print("策略 vs 基准对比 (测试集)")
print("=" * 60)
print(f"\n策略(Top3, 8天):")
print(f"  累计收益: {strategy['cumulative_return']*100:.2f}%")
print(f"  夏普比率: {strategy['sharpe_ratio']:.2f}")
print(f"  最大回撤: {strategy['max_drawdown']*100:.2f}%")

print(f"\n基准(沪深300):")
print(f"  累计收益: {bench_final*100:.2f}%")
print(f"  最大回撤: {bench_maxdd*100:.2f}%")

print(f"\n超额收益: {(strategy['cumulative_return']-bench_final)*100:.2f}%")
print("=" * 60)

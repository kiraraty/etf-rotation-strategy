"""对比不同调仓频率的表现"""
import pandas as pd
from data.etf_universe import get_etf_codes, BENCHMARK
from data.fetcher import fetch_all_etfs, fetch_etf_data
from engine.indicators import calc_all_indicators
from engine.scorer import score_cross_section
from engine.backtest import run_backtest
from config import DEFAULT_CONFIG

print("获取数据...")
etf_codes = get_etf_codes()
all_hist = fetch_all_etfs(etf_codes, period="5y")
bench_df = fetch_etf_data(BENCHMARK, period="5y")

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

print(f"\n数据期间: {score_df.index[0].date()} 至 {score_df.index[-1].date()}")
print(f"交易日数: {len(score_df)}\n")

# 测试不同调仓频率
print("=" * 70)
print("调仓频率对比 (Top2持仓, 万0.5费率)")
print("=" * 70)

results = []
for days in [1, 2, 3, 4, 5, 7, 10, 15, 20]:
    result = run_backtest(score_df, all_hist, top_n=2, rebalance_days=days, fee_rate=0.00005)
    
    # 估算年调仓次数
    years = len(score_df) / 252
    rebalances_per_year = (len(score_df) / days) / years
    
    results.append({
        '调仓间隔': f'{days}天',
        '年调仓次数': f'{rebalances_per_year:.0f}',
        '累计收益': f'{result["cumulative_return"]*100:.1f}%',
        '夏普比率': f'{result["sharpe_ratio"]:.2f}',
        '最大回撤': f'{result["max_drawdown"]*100:.1f}%',
        '胜率': f'{result["win_rate"]*100:.0f}%'
    })

df = pd.DataFrame(results)
print(df.to_string(index=False))
print("=" * 70)

"""美股ETF多空策略回测"""
import sys
import pandas as pd
import numpy as np
from data.etf_universe import get_etf_codes, BENCHMARK
from data.fetcher import fetch_all_etfs, fetch_etf_data
from engine.indicators import calc_all_indicators
from engine.scorer import score_cross_section
from config import DEFAULT_CONFIG

def run_long_short_backtest(score_history: pd.DataFrame,
                             all_hist: dict,
                             long_n: int = 3,
                             short_n: int = 3,
                             rebalance_days: int = 5,
                             fee_rate: float = 0.001) -> dict:
    """多空回测：做多Top N，做空Bottom N"""
    dates = score_history.index
    portfolio_value = 1.0
    daily_values = []
    holdings = {}
    last_rebalance = 0

    for i, date in enumerate(dates):
        # 调仓
        if i == 0 or i - last_rebalance >= rebalance_days:
            day_scores = score_history.loc[date].dropna().sort_values(ascending=False)
            
            # 做多Top N，做空Bottom N
            long_etfs = day_scores.head(long_n).index
            short_etfs = day_scores.tail(short_n).index
            
            new_holdings = {}
            for etf in long_etfs:
                new_holdings[etf] = 0.5 / long_n  # 50%做多
            for etf in short_etfs:
                new_holdings[etf] = -0.5 / short_n  # 50%做空
            
            # 计算换手和手续费
            if holdings:
                turnover = sum(abs(new_holdings.get(c, 0) - holdings.get(c, 0))
                             for c in set(new_holdings) | set(holdings))
                portfolio_value *= (1 - turnover * fee_rate)
            
            holdings = new_holdings
            last_rebalance = i

        # 计算当日收益
        day_return = 0
        for code, weight in holdings.items():
            if code in all_hist and date in all_hist[code].index:
                price_df = all_hist[code]
                if i > 0 and dates[i-1] in price_df.index:
                    ret = price_df.loc[date, 'close'] / price_df.loc[dates[i-1], 'close'] - 1
                    day_return += weight * ret

        portfolio_value *= (1 + day_return)
        daily_values.append(portfolio_value)

    # 计算指标
    daily_returns = pd.Series(daily_values).pct_change().dropna()
    cumulative_return = portfolio_value - 1
    sharpe_ratio = daily_returns.mean() / daily_returns.std() * np.sqrt(252) if daily_returns.std() > 0 else 0
    
    cummax = pd.Series(daily_values).cummax()
    drawdown = (pd.Series(daily_values) - cummax) / cummax
    max_drawdown = drawdown.min()
    
    win_rate = (daily_returns > 0).sum() / len(daily_returns) if len(daily_returns) > 0 else 0

    return {
        "daily_values": pd.Series(daily_values, index=dates),
        "cumulative_return": cumulative_return,
        "sharpe_ratio": sharpe_ratio,
        "max_drawdown": max_drawdown,
        "win_rate": win_rate,
    }

print("=" * 60)
print("美股ETF多空策略回测")
print("=" * 60)

# 获取数据
print("\n正在获取ETF数据（5年）...")
etf_codes = get_etf_codes()
all_hist = fetch_all_etfs(etf_codes, period="5y")
bench_df = fetch_etf_data(BENCHMARK, period="5y")

print(f"✓ 获取到{len(all_hist)}只ETF数据")

# 计算指标和评分
print("正在计算指标...")
all_indicators = {}
for code, hist_df in all_hist.items():
    indicators = calc_all_indicators(hist_df, bench_df)
    all_indicators[code] = indicators

print("正在计算评分...")
all_dates = bench_df.index
score_history = {}

for date in all_dates:
    cross_section = {}
    for code, ind_df in all_indicators.items():
        if date in ind_df.index:
            cross_section[code] = ind_df.loc[date]
    if len(cross_section) >= 6:  # 至少6只才能做多空
        cs_df = pd.DataFrame(cross_section).T
        day_scores = score_cross_section(cs_df, DEFAULT_CONFIG.weights)
        score_history[date] = day_scores

score_df = pd.DataFrame(score_history).T.sort_index()
print(f"✓ 共{len(score_df)}个交易日")

# 回测
print("\n正在回测...")
bt_result = run_long_short_backtest(score_df, all_hist, long_n=3, short_n=3, rebalance_days=5, fee_rate=0.001)

# 输出结果
print("\n" + "=" * 60)
print("多空策略回测结果")
print("=" * 60)
print(f"累计收益率: {bt_result['cumulative_return']*100:.2f}%")
print(f"夏普比率:   {bt_result['sharpe_ratio']:.2f}")
print(f"最大回撤:   {bt_result['max_drawdown']*100:.2f}%")
print(f"胜率:       {bt_result['win_rate']*100:.1f}%")
print("\n策略: 做多Top3 + 做空Bottom3，每5天调仓")
print("=" * 60)

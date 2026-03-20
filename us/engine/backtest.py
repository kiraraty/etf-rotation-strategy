import pandas as pd
import numpy as np

def run_backtest(score_history: pd.DataFrame,
                 all_hist: dict,
                 top_n: int = 3,
                 rebalance_days: int = 5,
                 fee_rate: float = 0.0001,
                 slippage: float = 0.0005,
                 exposure_map: pd.Series = None) -> dict:
    """实盘模拟版回测 (带动态仓位控制)
    
    Args:
        score_history: T日评分决定T+1日开盘动作
        all_hist: 历史行情数据
        exposure_map: {date: exposure_ratio} 每日仓位建议 (0~1)
    """
    dates = score_history.index
    portfolio_value = 1.0
    daily_values = []
    holdings = {}
    last_rebalance = 0

    for i, date in enumerate(dates):
        # 调仓动作
        if i > 0 and (i - last_rebalance >= rebalance_days):
            prev_date = dates[i-1]
            day_scores = score_history.loc[prev_date].dropna().sort_values(ascending=False)
            
            # 这里的 exposure 是宏观决定的全局仓位 (例如 0.7)
            exposure = exposure_map.loc[date] if exposure_map is not None and date in exposure_map.index else 1.0
            
            # 每个选中的 ETF 平分这个全局仓位 (例如每只 0.35)
            new_holdings = {code: exposure/top_n for code in day_scores.head(top_n).index}

            # 扣除摩擦成本
            codes = set(new_holdings.keys()) | set(holdings.keys())
            turnover = sum(abs(new_holdings.get(c, 0) - holdings.get(c, 0)) for c in codes)
            portfolio_value *= (1 - turnover * (fee_rate + slippage))
            
            holdings = new_holdings
            last_rebalance = i
        
        elif i == 0:
            exposure = exposure_map.iloc[0] if exposure_map is not None else 1.0
            day_scores = score_history.loc[date].dropna().sort_values(ascending=False)
            holdings = {code: exposure/top_n for code in day_scores.head(top_n).index}
            portfolio_value *= (1 - exposure * (fee_rate + slippage))
            daily_values.append(portfolio_value)
            continue

        # 计算当日净值变动
        day_return = 0
        for code, weight in holdings.items():
            if code in all_hist and date in all_hist[code].index:
                df = all_hist[code]
                idx = df.index.get_loc(date)
                if idx > 0:
                    ret = df.iloc[idx]['Close'] / df.iloc[idx-1]['Close'] - 1
                    day_return += weight * ret
        
        # 这里的 day_return 已经是加权后的，剩下没投的部分默认现金 0 收益
        portfolio_value *= (1 + day_return)
        daily_values.append(portfolio_value)

    # 指标计算
    daily_returns = pd.Series(daily_values).pct_change().dropna()
    cumulative_return = portfolio_value - 1
    sharpe_ratio = daily_returns.mean() / daily_returns.std() * np.sqrt(252) if daily_returns.std() > 0 else 0
    cummax = pd.Series(daily_values).cummax()
    max_drawdown = ((pd.Series(daily_values) - cummax) / cummax).min()

    return {
        "daily_values": pd.Series(daily_values, index=dates),
        "cumulative_return": cumulative_return,
        "sharpe_ratio": sharpe_ratio,
        "max_drawdown": max_drawdown,
    }

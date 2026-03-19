"""回测引擎：验证轮动策略效果"""

import pandas as pd
import numpy as np


def run_backtest(score_history: pd.DataFrame,
                 all_hist: dict,
                 top_n: int = 3,
                 rebalance_days: int = 5,
                 fee_rate: float = 0.001) -> dict:
    """回测ETF轮动策略

    Args:
        score_history: 历史评分 (date x etf_code)
        all_hist: {etf_code: hist_df} 历史价格数据
        top_n: 持仓数量
        rebalance_days: 调仓间隔（交易日）
        fee_rate: 单边手续费率

    Returns:
        {
            "daily_return": pd.Series,  # 每日收益率
            "cumulative_return": float,  # 累计收益率
            "sharpe_ratio": float,       # 夏普比率
            "max_drawdown": float,       # 最大回撤
            "win_rate": float,           # 胜率
        }
    """
    dates = score_history.index
    portfolio_value = 1.0  # 初始资金
    daily_values = []
    holdings = {}  # {code: weight}
    last_rebalance = 0

    for i, date in enumerate(dates):
        # 调仓逻辑:用前一天的评分决定今天的持仓(避免前瞻偏差)
        if i > 0 and (i - last_rebalance >= rebalance_days):
            # 用昨天的评分选出Top N
            prev_date = dates[i-1]
            day_scores = score_history.loc[prev_date].dropna().sort_values(ascending=False)
            new_holdings = {code: 1.0/top_n for code in day_scores.head(top_n).index}

            # 计算换手率和手续费
            if holdings:
                turnover = sum(abs(new_holdings.get(c, 0) - holdings.get(c, 0))
                             for c in set(new_holdings) | set(holdings))
                portfolio_value *= (1 - turnover * fee_rate)

            holdings = new_holdings
            last_rebalance = i
        elif i == 0:
            # 首日:用首日评分建仓,但不计算首日收益(避免前瞻偏差)
            day_scores = score_history.loc[date].dropna().sort_values(ascending=False)
            holdings = {code: 1.0/top_n for code in day_scores.head(top_n).index}
            last_rebalance = 0
            daily_values.append(portfolio_value)
            continue

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

    # 最大回撤
    cummax = pd.Series(daily_values).cummax()
    drawdown = (pd.Series(daily_values) - cummax) / cummax
    max_drawdown = drawdown.min()

    # 胜率
    win_rate = (daily_returns > 0).sum() / len(daily_returns) if len(daily_returns) > 0 else 0

    return {
        "daily_values": pd.Series(daily_values, index=dates),
        "cumulative_return": cumulative_return,
        "sharpe_ratio": sharpe_ratio,
        "max_drawdown": max_drawdown,
        "win_rate": win_rate,
    }

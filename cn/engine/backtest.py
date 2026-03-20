"""回测引擎：验证轮动策略效果"""

import pandas as pd
import numpy as np


def run_backtest(score_history: pd.DataFrame,
                 all_hist: dict,
                 top_n: int = 3,
                 rebalance_days: int = 5,
                 fee_rate: float = 0.00005,
                 slippage: float = 0.001) -> dict:
    """实盘模拟版回测

    Args:
        score_history: 历史评分 (T日评分决定T+1日开盘动作)
        all_hist: 历史数据 (需包含 open, close)
        top_n: 持仓数量
        rebalance_days: 调仓间隔
        fee_rate: 真实费率 (如 0.00005)
        slippage: 滑点 (0.001 代表单边 0.1% 的冲击成本)
    """
    dates = score_history.index
    portfolio_value = 1.0
    daily_values = []
    holdings = {} # {code: weight}
    last_rebalance = 0

    for i, date in enumerate(dates):
        # 调仓动作：基于 T-1 日的信号，在 T 日开盘执行
        if i > 0 and (i - last_rebalance >= rebalance_days):
            prev_date = dates[i-1]
            day_scores = score_history.loc[prev_date].dropna().sort_values(ascending=False)
            new_holdings = {code: 1.0/top_n for code in day_scores.head(top_n).index}

            # 计算换手率
            codes = set(new_holdings.keys()) | set(holdings.keys())
            turnover = 0
            for c in codes:
                old_w = holdings.get(c, 0)
                new_w = new_holdings.get(c, 0)
                turnover += abs(new_w - old_w)
            
            # 扣除手续费 + 滑点 (非常重要！)
            # 摩擦成本 = 换手率 * (手续费 + 滑点)
            friction_cost = turnover * (fee_rate + slippage)
            portfolio_value *= (1 - friction_cost)
            
            holdings = new_holdings
            last_rebalance = i
        
        elif i == 0:
            # 初始建仓 (假设第一天按开盘价买入)
            day_scores = score_history.loc[date].dropna().sort_values(ascending=False)
            holdings = {code: 1.0/top_n for code in day_scores.head(top_n).index}
            portfolio_value *= (1 - (fee_rate + slippage))
            daily_values.append(portfolio_value)
            continue

        # 计算当日收益 (按当日收盘/前日收盘计算)
        day_return = 0
        for code, weight in holdings.items():
            if code in all_hist and date in all_hist[code].index:
                df = all_hist[code]
                idx = df.index.get_loc(date)
                if idx > 0:
                    # 使用收盘价变动计算当日损益
                    ret = df.iloc[idx]['close'] / df.iloc[idx-1]['close'] - 1
                    day_return += weight * ret

        portfolio_value *= (1 + day_return)
        daily_values.append(portfolio_value)

    # ... 后续指标计算逻辑保持不变 ...

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

"""指标计算：动量、RPS、资金流、波动率"""

import numpy as np
import pandas as pd


def calc_momentum(df: pd.DataFrame, window: int) -> pd.Series:
    """计算N日动量（涨幅百分比）"""
    return df["close"].pct_change(window) * 100


def calc_all_momentum(df: pd.DataFrame) -> pd.DataFrame:
    """计算5/10/20日动量"""
    result = pd.DataFrame(index=df.index)
    result["momentum_5d"] = calc_momentum(df, 5)
    result["momentum_10d"] = calc_momentum(df, 10)
    result["momentum_20d"] = calc_momentum(df, 20)
    return result


def calc_rps(etf_df: pd.DataFrame, bench_df: pd.DataFrame,
             window: int = 20) -> pd.Series:
    """计算RPS相对强弱（相对基准的滚动收益率比值）

    RPS = ETF滚动收益 / 基准滚动收益，>1表示跑赢基准
    """
    etf_ret = etf_df["close"].pct_change(window)
    bench_ret = bench_df["close"].pct_change(window)
    # 对齐索引
    aligned_bench = bench_ret.reindex(etf_ret.index, method="ffill")
    # 避免除零
    rps = etf_ret / aligned_bench.replace(0, np.nan)
    return rps


def calc_money_flow(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """计算资金流向指标：成交额 vs N日均值比值

    >1 表示资金流入放大，<1 表示缩量
    """
    avg_amount = df["amount"].rolling(window).mean()
    flow = df["amount"] / avg_amount.replace(0, np.nan)
    return flow


def calc_volatility(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """计算波动率：收益率滚动标准差（年化）"""
    daily_ret = df["close"].pct_change()
    vol = daily_ret.rolling(window).std() * np.sqrt(252) * 100
    return vol


def calc_breakout(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """计算突破信号：当前价格相对N日最高价的位置

    1.0 = 创新高, 0.0 = 在最低价
    """
    rolling_high = df["close"].rolling(window).max()
    rolling_low = df["close"].rolling(window).min()
    breakout = (df["close"] - rolling_low) / (rolling_high - rolling_low).replace(0, np.nan)
    return breakout


def calc_volume_confirm(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """计算成交量确认：当前成交量相对均量的倍数"""
    avg_vol = df["volume"].rolling(window).mean()
    return df["volume"] / avg_vol.replace(0, np.nan)


def calc_all_indicators(etf_df: pd.DataFrame,
                        bench_df: pd.DataFrame) -> pd.DataFrame:
    """计算单只ETF的全部指标，返回合并DataFrame"""
    mom = calc_all_momentum(etf_df)
    rps = calc_rps(etf_df, bench_df).rename("rps")
    flow = calc_money_flow(etf_df).rename("money_flow")
    vol = calc_volatility(etf_df).rename("volatility")
    breakout = calc_breakout(etf_df).rename("breakout")
    vol_confirm = calc_volume_confirm(etf_df).rename("volume_confirm")

    result = pd.concat([mom, rps, flow, vol, breakout, vol_confirm], axis=1)
    return result

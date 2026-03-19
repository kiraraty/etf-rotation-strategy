"""akshare 数据采集模块

数据源优先级: Sina（稳定，不受系统代理影响） → 东方财富（备用）
"""

import os
import time

import pandas as pd
import streamlit as st

from config import DEFAULT_CONFIG
from data.cache import read_cache, write_cache
from data.etf_universe import BENCHMARK_ETF

# 尝试禁用系统代理
for _k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
            "all_proxy", "ALL_PROXY"):
    os.environ.pop(_k, None)
os.environ.setdefault("no_proxy", "*")

import akshare as ak


def _throttle():
    """请求节流，防封IP"""
    time.sleep(DEFAULT_CONFIG.data.request_interval)


def _code_to_sina_symbol(code: str) -> str:
    """ETF代码转Sina格式: 51xxxx→sh51xxxx, 159xxx→sz159xxx"""
    if code.startswith("15") or code.startswith("16"):
        return f"sz{code}"
    return f"sh{code}"


def _fetch_etf_hist_sina(code: str, max_retries: int = 3) -> pd.DataFrame:
    """从 Sina 数据源拉取 ETF 全量历史行情"""
    symbol = _code_to_sina_symbol(code)
    for attempt in range(max_retries):
        _throttle()
        try:
            df = ak.fund_etf_hist_sina(symbol=symbol)
            break
        except Exception:
            if attempt == max_retries - 1:
                raise
            time.sleep(1 + attempt)
            continue
    if df is None or df.empty:
        return pd.DataFrame()
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    return df


def _fetch_etf_hist_em(code: str, period: str, start_date: str,
                        end_date: str, max_retries: int = 3) -> pd.DataFrame:
    """从东方财富拉取 ETF 历史行情（备用）"""
    for attempt in range(max_retries):
        _throttle()
        try:
            df = ak.fund_etf_hist_em(
                symbol=code, period=period,
                start_date=start_date, end_date=end_date, adjust="qfq",
            )
            break
        except Exception:
            if attempt == max_retries - 1:
                raise
            time.sleep(1 + attempt)
            continue
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.rename(columns={
        "日期": "date", "开盘": "open", "收盘": "close",
        "最高": "high", "最低": "low", "成交量": "volume",
        "成交额": "amount", "振幅": "amplitude",
        "涨跌幅": "pct_change", "涨跌额": "change", "换手率": "turnover",
    })
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    return df


def _fetch_etf_hist_raw(code: str, period: str = "daily",
                         start_date: str = "", end_date: str = "") -> pd.DataFrame:
    """拉取 ETF 历史行情，优先 Sina，失败回退东方财富"""
    # Sina 源（不依赖 push2his.eastmoney.com，代理兼容性好）
    try:
        df = _fetch_etf_hist_sina(code)
        if not df.empty:
            return df
    except Exception:
        pass
    # 东方财富备用
    return _fetch_etf_hist_em(code, period, start_date, end_date)


@st.cache_data(ttl=DEFAULT_CONFIG.cache.memory_ttl_seconds, show_spinner=False)
def fetch_etf_hist(code: str, period: str = "daily",
                   days: int = 0) -> pd.DataFrame:
    """获取 ETF 历史行情（两层缓存）

    缓存链路: st.cache_data(内存) → Parquet文件 → akshare API
    """
    if days <= 0:
        days = DEFAULT_CONFIG.data.default_period_days

    cache_key = f"etf_hist_{code}_{period}_{days}"

    # 尝试 Parquet 文件缓存
    cached = read_cache(cache_key)
    if cached is not None:
        return cached

    # 计算起止日期
    end = pd.Timestamp.now()
    start = end - pd.Timedelta(days=int(days * 1.8))  # 多拉一些保证交易日够
    start_str = start.strftime("%Y%m%d")
    end_str = end.strftime("%Y%m%d")

    df = _fetch_etf_hist_raw(code, period, start_str, end_str)
    if not df.empty:
        df = df.tail(days)
        write_cache(cache_key, df)
    return df


def fetch_benchmark(period: str = "daily",
                    days: int = 0) -> pd.DataFrame:
    """获取基准（沪深300ETF）历史行情"""
    return fetch_etf_hist(BENCHMARK_ETF.code, period, days)


def fetch_all_etf_hist(codes: list, period: str = "daily",
                       days: int = 0,
                       progress_callback=None) -> dict:
    """批量获取多只 ETF 历史行情

    Returns: {code: DataFrame}
    """
    result = {}
    for i, code in enumerate(codes):
        try:
            df = fetch_etf_hist(code, period, days)
            if not df.empty:
                result[code] = df
        except Exception as e:
            st.warning(f"获取 {code} 数据失败: {e}")
        if progress_callback:
            progress_callback(i + 1, len(codes))
    return result

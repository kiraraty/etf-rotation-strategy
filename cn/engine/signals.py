"""轮动信号生成：串联完整分析流程"""

from typing import Optional

import pandas as pd
try:
    import streamlit as st
except ImportError:
    # Mock streamlit for CLI headless mode
    class MockStreamlit:
        def progress(self, val, text=""): return self
        def empty(self): pass
        def error(self, text): print(f"ERROR: {text}")
        def warning(self, text): print(f"WARNING: {text}")
    st = MockStreamlit()

from config import AppConfig, DEFAULT_CONFIG
from data.etf_universe import get_etf_codes, get_etf_map, BENCHMARK_ETF
from data.fetcher import fetch_etf_hist, fetch_benchmark, fetch_all_etf_hist
from engine.indicators import calc_all_indicators
from engine.scorer import score_cross_section
from engine.macro_regime import MacroRegimeEngine


def classify_signal(score: float, config: AppConfig = None) -> str:
    """根据评分分类信号"""
    if config is None:
        config = DEFAULT_CONFIG
    if score >= config.signal.strong_threshold:
        return "强势-关注"
    elif score >= config.signal.neutral_threshold:
        return "中性-观望"
    else:
        return "弱势-回避"


def run_analysis(period: str = "daily",
                 days: int = 0,
                 config: AppConfig = None,
                 etf_codes: list = None) -> dict:
    """运行完整分析流程

    Returns:
        {
            "latest_scores": pd.DataFrame,  # 最新截面评分
            "score_history": pd.DataFrame,  # 历史评分时间序列
            "all_indicators": dict,         # {code: indicators_df}
            "all_hist": dict,               # {code: hist_df}
        }
    """
    if config is None:
        config = DEFAULT_CONFIG
    if etf_codes is None:
        etf_codes = get_etf_codes()

    etf_map = get_etf_map()

    # 1. 启动宏观引擎
    macro_engine = MacroRegimeEngine()
    
    # 2. 获取基准数据
    bench_df = fetch_benchmark(period, days)
    if bench_df.empty:
        st.error("无法获取基准(沪深300ETF)数据")
        return {}

    # 3. 抓取宏观数据 (注入基准行情)
    macro_engine.fetch_data(days=days+100, benchmark_df=bench_df)
    macro_engine.calculate_regimes()

    # 2. 批量获取ETF数据
    progress = st.progress(0, text="正在获取ETF数据...")

    def on_progress(current, total):
        progress.progress(current / total, text=f"正在获取ETF数据 ({current}/{total})...")

    all_hist = fetch_all_etf_hist(etf_codes, period, days, on_progress)
    progress.empty()

    if not all_hist:
        st.error("未获取到任何ETF数据")
        return {}

    # 4. 计算各ETF指标
    all_indicators = {}
    for code, hist_df in all_hist.items():
        indicators = calc_all_indicators(hist_df, bench_df)
        all_indicators[code] = indicators

    # 5. 构建历史评分时间序列 (注入宏观)
    score_history = _build_score_history(all_indicators, config, macro_engine)

    # 6. 最新截面评分 (注入宏观)
    latest_scores = _build_latest_scores(
        all_indicators, etf_map, config, macro_engine=macro_engine
    )

    return {
        "latest_scores": latest_scores,
        "score_history": score_history,
        "all_indicators": all_indicators,
        "all_hist": all_hist,
        "benchmark": bench_df,
        "macro_engine": macro_engine,
    }


def _build_score_history(all_indicators: dict,
                         config: AppConfig,
                         macro_engine: MacroRegimeEngine = None) -> pd.DataFrame:
    """构建历史评分时间序列

    对每个交易日做截面评分
    """
    # 找到公共日期范围
    all_dates = None
    for code, ind_df in all_indicators.items():
        dates = ind_df.dropna(how="all").index
        if all_dates is None:
            all_dates = dates
        else:
            all_dates = all_dates.intersection(dates)

    if all_dates is None or len(all_dates) == 0:
        return pd.DataFrame()

    # 取所有可用的交易日做历史评分
    all_dates = all_dates.sort_values()

    scores_dict = {}
    for date in all_dates:
        cross_section = {}
        for code, ind_df in all_indicators.items():
            if date in ind_df.index:
                cross_section[code] = ind_df.loc[date]
        if len(cross_section) < 3:
            continue
        cs_df = pd.DataFrame(cross_section).T
        # 传入日期和宏观引擎
        day_scores = score_cross_section(cs_df, config.weights, date=date, macro_engine=macro_engine)
        scores_dict[date] = day_scores

    if not scores_dict:
        return pd.DataFrame()

    return pd.DataFrame(scores_dict).T.sort_index()


def _build_latest_scores(all_indicators: dict,
                         etf_map: dict,
                         config: AppConfig,
                         sentiment_scores: dict = None,
                         macro_engine: MacroRegimeEngine = None) -> pd.DataFrame:
    """构建最新截面评分表"""
    # 取每只ETF最新一行指标
    latest = {}
    latest_date = None
    for code, ind_df in all_indicators.items():
        valid = ind_df.dropna(how="all")
        if not valid.empty:
            latest[code] = valid.iloc[-1]
            if latest_date is None or valid.index[-1] > latest_date:
                latest_date = valid.index[-1]

    if not latest:
        return pd.DataFrame()

    cs_df = pd.DataFrame(latest).T
    # 传入日期和宏观引擎
    scores = score_cross_section(cs_df, config.weights, sentiment_scores, date=latest_date, macro_engine=macro_engine)

    result = pd.DataFrame({
        "code": scores.index,
        "name": [etf_map[c].name if c in etf_map else c for c in scores.index],
        "sector": [etf_map[c].sector if c in etf_map else "" for c in scores.index],
        "score": scores.values,
        "signal": [classify_signal(s, config) for s in scores.values],
    })

    # 附加最新指标值
    for col in ["momentum_5d", "momentum_10d", "momentum_20d",
                "rps", "money_flow", "volatility"]:
        result[col] = [cs_df.loc[c, col] if c in cs_df.index and col in cs_df.columns
                       else None for c in result["code"]]

    result = result.sort_values("score", ascending=False).reset_index(drop=True)
    result.index = result.index + 1  # 排名从1开始
    result.index.name = "rank"
    return result


def rescore_with_debate(analysis_result: dict,
                        debate_result: dict,
                        config: AppConfig = None) -> pd.DataFrame:
    """用辩论结果重新计算评分（将AI情绪纳入权重）

    Args:
        analysis_result: run_analysis() 的返回值
        debate_result: run_debate() 的返回值
        config: 应用配置（需 news_sentiment 权重 > 0）
    Returns:
        重算后的 latest_scores DataFrame
    """
    if config is None:
        config = DEFAULT_CONFIG

    etf_map = get_etf_map()
    all_indicators = analysis_result["all_indicators"]
    sector_scores = debate_result.get("sector_scores", {})

    # 将 sector_scores（板块名→分数）转换为 etf_code→分数
    code_scores = {}
    for code, info in etf_map.items():
        if info.sector in sector_scores:
            code_scores[code] = sector_scores[info.sector]

    return _build_latest_scores(
        all_indicators, etf_map, config, code_scores
    )


def rescore_with_sentiment(analysis_result: dict,
                           sentiment_results: dict,
                           config: AppConfig = None) -> pd.DataFrame:
    """用批量新闻分析结果重新计算评分

    Args:
        analysis_result: run_analysis() 的返回值
        sentiment_results: analyze_all_sectors() 的返回值 {sector: {"sentiment_score": int, ...}}
        config: 应用配置
    """
    if config is None:
        config = DEFAULT_CONFIG

    etf_map = get_etf_map()
    all_indicators = analysis_result["all_indicators"]

    # 提取板块情绪分
    code_scores = {}
    for code, info in etf_map.items():
        if info.sector in sentiment_results:
            code_scores[code] = sentiment_results[info.sector].get("sentiment_score", 0)

    return _build_latest_scores(
        all_indicators, etf_map, config, code_scores
    )

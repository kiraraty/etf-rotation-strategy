"""综合评分引擎：截面排名归一化 → 加权求和"""

import numpy as np
import pandas as pd

from config import WeightConfig, DEFAULT_CONFIG


def rank_normalize(series: pd.Series) -> pd.Series:
    """截面排名归一化到 0~100"""
    ranked = series.rank(pct=True, na_option="bottom")
    return ranked * 100


def score_cross_section(indicators: dict[str, pd.Series],
                        weights: WeightConfig = None,
                        sentiment_scores: dict = None) -> pd.Series:
    """对单个截面（某一天）的所有ETF指标进行评分

    Args:
        indicators: DataFrame，columns=指标名, index=etf_code
        weights: 权重配置
        sentiment_scores: {etf_code: float} AI情绪评分(-100~100), 可选

    Returns:
        pd.Series: index=etf_code, value=综合评分(0~100)
    """
    if weights is None:
        weights = DEFAULT_CONFIG.weights

    w = weights.as_dict()
    df = indicators if isinstance(indicators, pd.DataFrame) else pd.DataFrame(indicators)

    scored = pd.DataFrame(index=df.index)

    # 正向指标：值越大越好 → 直接排名归一化
    for col in ["momentum_5d", "momentum_10d", "momentum_20d", "rps",
                "money_flow", "breakout", "volume_confirm"]:
        if col in df.columns:
            scored[col] = rank_normalize(df[col])

    # 反向指标：波动率越低越好 → 取反后排名
    if "volatility" in df.columns:
        scored["volatility"] = rank_normalize(-df["volatility"])

    # AI情绪评分（辩论结果回灌）
    if "news_sentiment" in w and sentiment_scores:
        sentiment_series = pd.Series(
            {code: sentiment_scores.get(code, 0) for code in df.index}
        )
        scored["news_sentiment"] = rank_normalize(sentiment_series)

    # 加权求和
    total = pd.Series(0.0, index=df.index)
    for col, weight in w.items():
        if col in scored.columns:
            total += scored[col].fillna(50) * weight

    return total

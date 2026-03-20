"""综合评分引擎：截面排名归一化 → 加权求和"""

import numpy as np
import pandas as pd

from config import WeightConfig, DEFAULT_CONFIG


from config import WeightConfig, DEFAULT_CONFIG
from data.etf_universe import get_etf_map

def rank_normalize(series: pd.Series) -> pd.Series:
    """截面排名归一化到 0~100"""
    ranked = series.rank(pct=True, na_option="bottom")
    return ranked * 100


def score_cross_section(indicators: dict[str, pd.Series],
                        weights: WeightConfig = None,
                        sentiment_scores: dict = None,
                        date: pd.Timestamp = None,
                        macro_engine = None) -> pd.Series:
    """对单个截面（某一天）的所有ETF指标进行评分

    Args:
        indicators: DataFrame，columns=指标名, index=etf_code
        weights: 权重配置
        sentiment_scores: {etf_code: float} AI情绪评分(-100~100), 可选
        date: 当前日期 (用于宏观判断)
        macro_engine: USMacroRegimeEngine 实例

    Returns:
        pd.Series: index=etf_code, value=综合评分(0~100)
    """
    if weights is None:
        weights = DEFAULT_CONFIG.weights

    w = weights.as_dict()
    df = indicators if isinstance(indicators, pd.DataFrame) else pd.DataFrame(indicators)

    scored = pd.DataFrame(index=df.index)

    # 1. 技术指标评分
    for col in ["momentum_5d", "momentum_10d", "momentum_20d", "rps",
                "money_flow", "breakout", "volume_confirm"]:
        if col in df.columns:
            scored[col] = rank_normalize(df[col])

    if "volatility" in df.columns:
        scored["volatility"] = rank_normalize(-df["volatility"])

    # 2. 加权初始求和
    total = pd.Series(0.0, index=df.index)
    for col, weight in w.items():
        if col in scored.columns:
            total += scored[col].fillna(50) * weight

    # 3. 注入宏观环境乘数 (非后验逻辑)
    if date is not None and macro_engine is not None:
        etf_map = get_etf_map()
        for code in total.index:
            info = etf_map.get(code)
            if info:
                sector = info.get("sector", "")
                # 获取该板块在当前宏观环境下的权重调节系数
                multiplier = macro_engine.get_multiplier(date, sector)
                total.loc[code] *= multiplier

    return total

"""LLM 新闻情绪分析：对板块新闻做情绪评分"""

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import streamlit as st
from typing import Dict

from llm.provider import OpenAICompatProvider

logger = logging.getLogger(__name__)

ANALYSIS_PROMPT = """请分析以下A股板块"{sector}"的最新新闻，给出：
1. sentiment_score: 情绪评分(-100到100，正=利好，负=利空)
2. summary: 一句话总结板块当前消息面(30字内)
3. key_factors: 关键影响因素列表(最多3个)
4. impact_level: 影响程度(high/medium/low)

新闻内容：
{news_text}

请严格以JSON格式回复，不要其他内容：
{{"sentiment_score": 0, "summary": "", "key_factors": [], "impact_level": "low"}}"""


def _get_llm():
    if "llm_provider" not in st.session_state:
        st.session_state.llm_provider = OpenAICompatProvider()
    return st.session_state.llm_provider


def analyze_sector_news(sector: str, news_titles: list, llm=None) -> dict:
    """用LLM分析单个板块的新闻情绪"""
    if not news_titles:
        return {"sentiment_score": 0, "summary": "无新闻", "key_factors": [], "impact_level": "low"}

    news_text = "\n".join(f"- {t}" for t in news_titles[:10])
    prompt = ANALYSIS_PROMPT.format(sector=sector, news_text=news_text)

    if llm is None:
        llm = _get_llm()
    raw = llm.analyze(prompt, {})

    try:
        # 尝试提取JSON
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(raw[start:end])
    except (json.JSONDecodeError, ValueError):
        logger.warning(f"LLM JSON parse failed for {sector}: {raw[:100]}")

    return {"sentiment_score": 0, "summary": raw[:50], "key_factors": [], "impact_level": "low"}


def _extract_titles(data: dict) -> list:
    """从板块新闻数据中提取标题列表"""
    titles = []
    etf_df = data.get("etf_news")
    if etf_df is not None and not etf_df.empty:
        titles.extend(etf_df["title"].tolist())
    cls_df = data.get("cls_matched")
    if cls_df is not None and not cls_df.empty:
        titles.extend(cls_df["title"].tolist())
    return titles


def analyze_all_sectors(sector_news: Dict[str, dict],
                        max_workers: int = 5,
                        on_progress=None) -> Dict[str, dict]:
    """批量并发分析所有板块新闻情绪

    Args:
        sector_news: {sector: {"etf_news": df, "cls_matched": df, ...}}
        max_workers: 并发线程数
        on_progress: 可选回调 (sector, index, total, result_or_error) -> None
    Returns:
        {sector: {"sentiment_score": int, "summary": str, ...}}
    """
    tasks = {
        sector: _extract_titles(data)
        for sector, data in sector_news.items()
    }
    total = len(tasks)

    # 在主线程创建 LLM provider，避免子线程访问 st.session_state
    llm = _get_llm()

    results = {}
    done_count = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(analyze_sector_news, sector, titles, llm): sector
            for sector, titles in tasks.items()
        }
        for future in as_completed(futures):
            sector = futures[future]
            done_count += 1
            try:
                res = future.result()
                results[sector] = res
                if on_progress:
                    on_progress(sector, done_count, total, res)
            except Exception as e:
                logger.error(f"Analyze {sector} failed: {e}")
                err_res = {
                    "sentiment_score": 0, "summary": f"分析失败: {e}",
                    "key_factors": [], "impact_level": "low",
                }
                results[sector] = err_res
                if on_progress:
                    on_progress(sector, done_count, total, err_res)
    return results

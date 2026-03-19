"""外部消息/新闻数据采集模块

数据源:
- 东方财富个股新闻 (stock_news_em) → 板块相关新闻
- 财联社快讯 (stock_info_global_cls) → 市场整体消息
- 新闻联播 (news_cctv) → 重大政策信号
"""

import os
import time
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

for _k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
            "all_proxy", "ALL_PROXY"):
    os.environ.pop(_k, None)
os.environ.setdefault("no_proxy", "*")

import akshare as ak

# 板块关键词映射：用于从财联社快讯中匹配板块相关消息
SECTOR_KEYWORDS = {
    "半导体": ["半导体", "芯片", "集成电路", "晶圆", "光刻", "EDA", "封测"],
    "新能源": ["新能源", "锂电", "储能", "电池", "充电桩", "风电"],
    "医药": ["医药", "创新药", "CXO", "生物医药", "集采", "医保"],
    "消费": ["消费", "零售", "家电", "食品", "内需"],
    "银行": ["银行", "信贷", "LPR", "降息", "降准", "存款"],
    "军工": ["军工", "国防", "航空", "航天", "导弹"],
    "计算机": ["计算机", "信创", "软件", "数字经济", "人工智能", "AI", "大模型"],
    "光伏": ["光伏", "太阳能", "硅片", "组件", "逆变器"],
    "农业": ["农业", "种业", "化肥", "猪肉", "粮食"],
    "房地产": ["房地产", "地产", "楼市", "房价", "住房", "土地"],
    "证券": ["证券", "券商", "资本市场", "注册制", "IPO"],
    "稀土": ["稀土", "永磁", "磁材"],
    "旅游": ["旅游", "酒店", "景区", "出行", "免税"],
    "有色金属": ["有色", "铜", "铝", "黄金", "贵金属", "锂"],
    "5G": ["5G", "通信", "基站", "光模块", "算力"],
    "酒": ["白酒", "酒", "茅台", "酿酒"],
    "游戏": ["游戏", "版号", "电竞", "网游"],
    "传媒": ["传媒", "影视", "短视频", "直播", "文化"],
    "环保": ["环保", "碳中和", "碳交易", "绿色", "污染"],
    "医疗": ["医疗", "器械", "医院", "诊断", "手术机器人"],
}


def _throttle():
    time.sleep(0.3)


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_sector_news(etf_code: str, max_rows: int = 10) -> pd.DataFrame:
    """获取单只ETF相关新闻（东方财富）"""
    try:
        _throttle()
        df = ak.stock_news_em(symbol=etf_code)
        if df is None or df.empty:
            return pd.DataFrame()
        df = df.rename(columns={
            "新闻标题": "title", "新闻内容": "summary",
            "发布时间": "time", "文章来源": "source", "新闻链接": "url",
        })
        df = df[["title", "summary", "time", "source"]].head(max_rows)
        df["time"] = pd.to_datetime(df["time"], errors="coerce")
        return df.sort_values("time", ascending=False).reset_index(drop=True)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=900, show_spinner=False)
def fetch_cls_news() -> pd.DataFrame:
    """获取财联社快讯（全市场）"""
    try:
        _throttle()
        df = ak.stock_info_global_cls(symbol="全部")
        if df is None or df.empty:
            return pd.DataFrame()
        df = df.rename(columns={
            "标题": "title", "内容": "summary",
            "发布日期": "date", "发布时间": "time_str",
        })
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_cctv_news(date_str: str = "") -> pd.DataFrame:
    """获取新闻联播文字稿"""
    if not date_str:
        date_str = datetime.now().strftime("%Y%m%d")
    try:
        _throttle()
        df = ak.news_cctv(date=date_str)
        if df is None or df.empty:
            return pd.DataFrame()
        return df
    except Exception:
        return pd.DataFrame()


def match_sector_news(cls_df: pd.DataFrame, sector: str) -> pd.DataFrame:
    """从财联社快讯中匹配指定板块的相关消息"""
    if cls_df.empty or sector not in SECTOR_KEYWORDS:
        return pd.DataFrame()
    keywords = SECTOR_KEYWORDS[sector]
    mask = cls_df.apply(
        lambda row: any(
            kw in str(row.get("title", "")) + str(row.get("summary", ""))
            for kw in keywords
        ), axis=1
    )
    return cls_df[mask].reset_index(drop=True)


def fetch_all_sector_news_summary(etf_map: dict) -> dict:
    """批量获取所有板块的新闻摘要

    Returns: {sector: DataFrame}
    """
    cls_df = fetch_cls_news()
    result = {}
    for code, info in etf_map.items():
        # 合并：ETF专属新闻 + 财联社板块匹配
        etf_news = fetch_sector_news(code, max_rows=5)
        cls_matched = match_sector_news(cls_df, info.sector)
        if not cls_matched.empty:
            cls_matched = cls_matched[["title", "summary"]].head(5)
        result[info.sector] = {
            "etf_news": etf_news,
            "cls_matched": cls_matched,
            "news_count": len(etf_news) + len(cls_matched),
        }
    return result

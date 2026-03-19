"""新闻资讯：板块相关新闻 + 财联社快讯 + 新闻联播政策"""

import streamlit as st
from datetime import datetime

from data.news import fetch_cls_news, fetch_cctv_news, fetch_sector_news, match_sector_news, SECTOR_KEYWORDS
from data.etf_universe import get_etf_pool

st.set_page_config(page_title="新闻资讯", page_icon="📰", layout="wide")
st.title("新闻资讯")

# --- 财联社快讯 ---
st.subheader("财联社快讯")
cls_df = fetch_cls_news()
if not cls_df.empty:
    for _, row in cls_df.iterrows():
        st.markdown(
            f"**{row.get('time_str', '')}** | {row['title']}",
            help=str(row.get("summary", "")),
        )
else:
    st.info("暂无财联社快讯数据")

st.markdown("---")

# --- 板块新闻筛选 ---
st.subheader("板块相关消息")
etf_pool = get_etf_pool()
sectors = [e.sector for e in etf_pool]
selected_sector = st.selectbox("选择板块", sectors)

# 找到对应ETF代码
selected_etf = next((e for e in etf_pool if e.sector == selected_sector), None)

col_a, col_b = st.columns(2)

with col_a:
    st.markdown(f"##### {selected_sector} - ETF相关新闻")
    if selected_etf:
        etf_news = fetch_sector_news(selected_etf.code)
        if not etf_news.empty:
            for _, row in etf_news.iterrows():
                t = row.get("time", "")
                if hasattr(t, "strftime"):
                    t = t.strftime("%m-%d %H:%M")
                st.markdown(f"- **[{t}]** {row['title']}")
                if row.get("summary"):
                    st.caption(str(row["summary"])[:120] + "...")
        else:
            st.info("暂无该ETF相关新闻")

with col_b:
    st.markdown(f"##### {selected_sector} - 财联社关键词匹配")
    matched = match_sector_news(cls_df, selected_sector)
    if not matched.empty:
        for _, row in matched.iterrows():
            st.markdown(f"- {row['title']}")
    else:
        st.caption(f"今日快讯中未匹配到「{selected_sector}」相关关键词")
    st.caption(f"匹配关键词: {', '.join(SECTOR_KEYWORDS.get(selected_sector, []))}")

st.markdown("---")

# --- 新闻联播政策信号 ---
st.subheader("新闻联播政策信号")
date_input = st.date_input("选择日期", value=datetime.now())
cctv_df = fetch_cctv_news(date_input.strftime("%Y%m%d"))
if not cctv_df.empty:
    for _, row in cctv_df.iterrows():
        with st.expander(row["title"]):
            st.write(str(row.get("content", ""))[:500])
else:
    st.info("暂无该日期新闻联播数据")

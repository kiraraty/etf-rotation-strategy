"""主看板：热力图 + 排行榜 + 信号时间线 + AI辩论摘要"""

import streamlit as st

from config import AppConfig, DEFAULT_CONFIG
from engine.signals import run_analysis
from viz.heatmap import create_heatmap
from viz.ranking import create_ranking_chart
from viz.timeline import create_timeline
from data.news import fetch_cls_news, fetch_sector_news, match_sector_news

st.set_page_config(page_title="A股板块轮动", page_icon="📊", layout="wide")

# --- 自定义样式 ---
st.markdown("""<style>
.block-container {padding-top: 1rem;}
div[data-testid="stMetric"] {
    background: linear-gradient(135deg, #667eea11, #764ba211);
    border: 1px solid #e0e0e0; border-radius: 10px; padding: 12px 16px;
}
div[data-testid="stMetric"] label {font-size: 0.85rem; color: #666;}
div[data-testid="stMetric"] [data-testid="stMetricValue"] {font-size: 1.6rem; font-weight: 700;}
</style>""", unsafe_allow_html=True)

st.title("A股板块轮动分析")

# 侧边栏参数
with st.sidebar:
    st.header("分析参数")
    period = st.selectbox("数据周期", ["daily", "weekly"],
                          format_func=lambda x: {"daily": "日线", "weekly": "周线"}[x])
    days = st.slider("回溯天数", 60, 250, 120, step=10)
    top_n = st.slider("时间线显示Top N", 3, 10, 5)

    st.markdown("---")
    use_llm = st.checkbox("启用 LLM 情绪增强分析", value=False, help="调用大模型对各板块新闻进行评分，需耗费一定时间")

    run_btn = st.button("运行分析", type="primary", use_container_width=True)

# session_state
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

if run_btn:
    with st.spinner("正在运行量化分析..."):
        result = run_analysis(period=period, days=days)
        if result:
            if use_llm:
                from data.etf_universe import get_etf_map
                from data.news import fetch_all_sector_news_summary
                from llm.news_analyzer import analyze_all_sectors
                from engine.signals import rescore_with_sentiment

                with st.status("LLM 正在分析各板块新闻情绪...", expanded=False) as status:
                    st.write("获取板块新闻摘要...")
                    etf_map = get_etf_map()
                    sector_news = fetch_all_sector_news_summary(etf_map)

                    st.write("调用大模型批量评分...")
                    sentiment_results = analyze_all_sectors(
                        sector_news,
                        on_progress=lambda s, i, t, r: status.update(label=f"已分析 {s} ({i}/{t})")
                    )

                    st.write("重算综合评分...")
                    new_latest = rescore_with_sentiment(result, sentiment_results)
                    result["latest_scores"] = new_latest
                    result["sentiment_results"] = sentiment_results
                    status.update(label="LLM 情绪分析完成", state="complete", expanded=False)

            st.session_state.analysis_result = result

result = st.session_state.analysis_result
if result is None:
    st.info("点击左侧「运行分析」按钮开始")
    st.stop()

latest_scores = result.get("latest_scores")
score_history = result.get("score_history")
sentiment_results = result.get("sentiment_results")

if latest_scores is None or latest_scores.empty:
    st.warning("未获取到有效评分数据")
    st.stop()

# --- 信号摘要 ---
strong = latest_scores[latest_scores["signal"] == "强势-关注"]
neutral = latest_scores[latest_scores["signal"] == "中性-观望"]
weak = latest_scores[latest_scores["signal"] == "弱势-回避"]

col1, col2, col3, col4 = st.columns(4)
col1.metric("强势-关注", f"{len(strong)} 只")
col2.metric("中性-观望", f"{len(neutral)} 只")
col3.metric("弱势-回避", f"{len(weak)} 只")
col4.metric("ETF总数", f"{len(latest_scores)} 只")

# --- 评分排行表 ---
st.subheader("综合评分排行")
display_cols = ["name", "sector", "score", "signal",
                "momentum_5d", "momentum_10d", "momentum_20d"]
# 如果有情绪分，也展示出来
if sentiment_results:
    # 将 sentiment_score 映射到 DataFrame
    latest_scores["sentiment"] = latest_scores["sector"].map(
        lambda s: sentiment_results.get(s, {}).get("sentiment_score", 0)
    )
    display_cols.insert(4, "sentiment")

display_df = latest_scores[display_cols].copy()
format_dict = {
    "score": "%.2f",
    "momentum_5d": "%.2f",
    "momentum_10d": "%.2f",
    "momentum_20d": "%.2f",
}
if "sentiment" in display_df.columns:
    format_dict["sentiment"] = "%d"

for c, fmt in format_dict.items():
    if c in display_df.columns:
        display_df[c] = display_df[c].round(2) if "%.2f" in fmt else display_df[c]

column_config = {
    "name": st.column_config.TextColumn("名称"),
    "sector": st.column_config.TextColumn("板块"),
    "score": st.column_config.ProgressColumn("评分", min_value=0, max_value=100, format="%.1f"),
    "signal": st.column_config.TextColumn("信号"),
    "momentum_5d": st.column_config.NumberColumn("5日动量%", format="%.2f"),
    "momentum_10d": st.column_config.NumberColumn("10日动量%", format="%.2f"),
    "momentum_20d": st.column_config.NumberColumn("20日动量%", format="%.2f"),
}
if "sentiment" in display_df.columns:
    column_config["sentiment"] = st.column_config.NumberColumn("情绪分", format="%d", help="LLM 对板块新闻的情绪评分(-100到100)")

st.dataframe(
    display_df, use_container_width=True,
    column_config=column_config,
)

# --- 图表区域 ---
chart_col1, chart_col2 = st.columns(2)
with chart_col1:
    st.subheader("评分排行图")
    st.plotly_chart(create_ranking_chart(latest_scores), use_container_width=True)
with chart_col2:
    st.subheader("评分趋势")
    if score_history is not None and not score_history.empty:
        st.plotly_chart(create_timeline(score_history, top_n=top_n), use_container_width=True)
    else:
        st.info("历史评分数据不足")

st.subheader("板块轮动热力图")
if score_history is not None and not score_history.empty:
    st.plotly_chart(create_heatmap(score_history), use_container_width=True)
else:
    st.info("历史评分数据不足，无法生成热力图")

# --- AI 辩论分析摘要 ---
st.markdown("---")
st.subheader("AI 辩论分析")

debate_result = st.session_state.get("debate_result")
if debate_result:
    judge = debate_result.get("judge_verdict", {})
    winner = judge.get("winner", "neutral")
    winner_label = "多头胜" if winner == "bull" else "空头胜" if winner == "bear" else "平局"
    sentiment = judge.get("market_sentiment", "neutral")
    sentiment_map = {"bullish": "看多", "bearish": "看空", "neutral": "中性"}

    dc1, dc2, dc3, dc4 = st.columns(4)
    dc1.metric("辩论胜方", winner_label)
    dc2.metric("置信度", f"{judge.get('confidence', 0):.0%}")
    dc3.metric("风险等级", judge.get("risk_level", "medium"))
    dc4.metric("市场情绪", sentiment_map.get(sentiment, sentiment))

    if judge.get("narrative"):
        st.info(judge["narrative"])
    if judge.get("rotation_advice"):
        st.caption(f"轮动建议: {judge['rotation_advice']}")

    st.page_link("pages/5_AI辩论.py", label="查看完整辩论详情 →", icon="⚖️")
else:
    st.caption("尚未运行AI辩论分析。")
    st.page_link("pages/5_AI辩论.py", label="前往AI辩论页面 →", icon="⚖️")

# --- 新闻速览 ---
st.markdown("---")
st.subheader("板块新闻速览")

cls_df = fetch_cls_news()

if not strong.empty:
    top_sectors = strong.head(3)
    news_cols = st.columns(len(top_sectors))
    for i, (_, row) in enumerate(top_sectors.iterrows()):
        with news_cols[i]:
            st.markdown(f"**{row['name']}** ({row['sector']})")
            etf_news = fetch_sector_news(row["code"], max_rows=3)
            if not etf_news.empty:
                for _, n in etf_news.iterrows():
                    st.caption(f"· {n['title']}")
            else:
                matched = match_sector_news(cls_df, row["sector"])
                if not matched.empty:
                    for _, n in matched.head(3).iterrows():
                        st.caption(f"· {n['title']}")
                else:
                    st.caption("暂无相关新闻")

st.markdown("##### 财联社最新快讯")
if not cls_df.empty:
    for _, row in cls_df.head(5).iterrows():
        st.caption(f"**{row.get('time_str', '')}** {row['title']}")
else:
    st.caption("暂无快讯数据")

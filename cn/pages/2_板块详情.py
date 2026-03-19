"""单板块详情：单只ETF指标详细分析"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from data.etf_universe import get_etf_pool, get_etf_map
from engine.signals import classify_signal

st.set_page_config(page_title="板块详情", page_icon="🔍", layout="wide")
st.title("板块详情")

# 检查是否有分析结果
if "analysis_result" not in st.session_state or st.session_state.analysis_result is None:
    st.warning("请先在主看板页面运行分析")
    st.stop()

result = st.session_state.analysis_result
all_hist = result.get("all_hist", {})
all_indicators = result.get("all_indicators", {})
latest_scores = result.get("latest_scores")
etf_map = get_etf_map()

# ETF选择器
available_codes = list(all_hist.keys())
if not available_codes:
    st.warning("无可用ETF数据")
    st.stop()

options = {code: f"{etf_map[code].name} ({code})" if code in etf_map else code
           for code in available_codes}
selected_code = st.selectbox(
    "选择板块ETF",
    available_codes,
    format_func=lambda x: options[x],
)

hist_df = all_hist.get(selected_code)
ind_df = all_indicators.get(selected_code)
etf_info = etf_map.get(selected_code)

if hist_df is None or hist_df.empty:
    st.warning("该ETF无历史数据")
    st.stop()

# 基本信息和最新指标
name = etf_info.name if etf_info else selected_code
st.subheader(f"{name} ({selected_code})")

if ind_df is not None and not ind_df.empty:
    latest = ind_df.dropna(how="all").iloc[-1]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("5日动量", f"{latest.get('momentum_5d', 0):.2f}%")
    c2.metric("10日动量", f"{latest.get('momentum_10d', 0):.2f}%")
    c3.metric("20日动量", f"{latest.get('momentum_20d', 0):.2f}%")
    c4.metric("RPS强弱", f"{latest.get('rps', 0):.3f}")

    c5, c6 = st.columns(2)
    c5.metric("资金流向", f"{latest.get('money_flow', 0):.2f}")
    c6.metric("波动率", f"{latest.get('volatility', 0):.2f}%")

# 价格走势图
st.subheader("价格走势")
fig_price = make_subplots(
    rows=2, cols=1, shared_xaxes=True,
    row_heights=[0.7, 0.3],
    vertical_spacing=0.05,
)
fig_price.add_trace(
    go.Candlestick(
        x=hist_df.index, open=hist_df["open"],
        high=hist_df["high"], low=hist_df["low"],
        close=hist_df["close"], name="K线",
    ), row=1, col=1,
)
fig_price.add_trace(
    go.Bar(x=hist_df.index, y=hist_df["amount"],
           name="成交额", marker_color="rgba(100,100,200,0.5)"),
    row=2, col=1,
)
fig_price.update_layout(
    height=500, xaxis_rangeslider_visible=False,
    margin=dict(l=60, r=20, t=20, b=40),
)
st.plotly_chart(fig_price, use_container_width=True)

# 指标走势图
if ind_df is not None and not ind_df.empty:
    st.subheader("指标走势")

    col_left, col_right = st.columns(2)

    with col_left:
        # 动量指标
        fig_mom = go.Figure()
        for col_name, label in [("momentum_5d", "5日动量"),
                                 ("momentum_10d", "10日动量"),
                                 ("momentum_20d", "20日动量")]:
            if col_name in ind_df.columns:
                fig_mom.add_trace(go.Scatter(
                    x=ind_df.index, y=ind_df[col_name],
                    mode="lines", name=label,
                ))
        fig_mom.add_hline(y=0, line_dash="dash", line_color="gray")
        fig_mom.update_layout(
            title="动量因子", height=350,
            margin=dict(l=60, r=20, t=40, b=40),
        )
        st.plotly_chart(fig_mom, use_container_width=True)

    with col_right:
        # RPS + 资金流向
        fig_rps = go.Figure()
        if "rps" in ind_df.columns:
            fig_rps.add_trace(go.Scatter(
                x=ind_df.index, y=ind_df["rps"],
                mode="lines", name="RPS",
            ))
        fig_rps.add_hline(y=1.0, line_dash="dash", line_color="gray",
                          annotation_text="基准线")
        fig_rps.update_layout(
            title="RPS相对强弱", height=350,
            margin=dict(l=60, r=20, t=40, b=40),
        )
        st.plotly_chart(fig_rps, use_container_width=True)

    # 第二行图表
    col_left2, col_right2 = st.columns(2)

    with col_left2:
        fig_flow = go.Figure()
        if "money_flow" in ind_df.columns:
            fig_flow.add_trace(go.Scatter(
                x=ind_df.index, y=ind_df["money_flow"],
                mode="lines", name="资金流向",
                fill="tozeroy", fillcolor="rgba(100,150,200,0.2)",
            ))
        fig_flow.add_hline(y=1.0, line_dash="dash", line_color="gray",
                           annotation_text="均值线")
        fig_flow.update_layout(
            title="资金流向（成交额/均值）", height=350,
            margin=dict(l=60, r=20, t=40, b=40),
        )
        st.plotly_chart(fig_flow, use_container_width=True)

    with col_right2:
        fig_vol = go.Figure()
        if "volatility" in ind_df.columns:
            fig_vol.add_trace(go.Scatter(
                x=ind_df.index, y=ind_df["volatility"],
                mode="lines", name="波动率",
                line=dict(color="orange"),
            ))
        fig_vol.update_layout(
            title="年化波动率 (%)", height=350,
            margin=dict(l=60, r=20, t=40, b=40),
        )
        st.plotly_chart(fig_vol, use_container_width=True)

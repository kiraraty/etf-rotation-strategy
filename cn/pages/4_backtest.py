"""回测页面：验证轮动策略效果"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from config import DEFAULT_CONFIG
from engine.signals import run_analysis
from engine.backtest import run_backtest

st.set_page_config(page_title="策略回测", page_icon="📊", layout="wide")
st.title("📊 ETF轮动策略回测")

# 参数设置
col1, col2, col3, col4 = st.columns(4)
with col1:
    top_n = st.slider("持仓数量", 1, 10, 3)
with col2:
    rebalance_days = st.slider("调仓间隔(天)", 1, 20, 5)
with col3:
    fee_rate = st.number_input("手续费率(%)", 0.0, 1.0, 0.1) / 100
with col4:
    days = st.slider("回测天数", 60, 365, 120)

if st.button("开始回测", type="primary"):
    with st.spinner("正在运行分析..."):
        # 运行分析
        result = run_analysis(period="daily", days=days, config=DEFAULT_CONFIG)

        if not result or result["score_history"].empty:
            st.error("数据不足，无法回测")
            st.stop()

        # 运行回测
        bt_result = run_backtest(
            result["score_history"],
            result["all_hist"],
            top_n=top_n,
            rebalance_days=rebalance_days,
            fee_rate=fee_rate
        )

        # 显示指标
        st.subheader("📈 回测结果")
        metric_cols = st.columns(4)
        with metric_cols[0]:
            st.metric("累计收益率", f"{bt_result['cumulative_return']*100:.2f}%")
        with metric_cols[1]:
            st.metric("夏普比率", f"{bt_result['sharpe_ratio']:.2f}")
        with metric_cols[2]:
            st.metric("最大回撤", f"{bt_result['max_drawdown']*100:.2f}%")
        with metric_cols[3]:
            st.metric("胜率", f"{bt_result['win_rate']*100:.1f}%")

        # 净值曲线
        st.subheader("💰 净值曲线")
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=bt_result["daily_values"].index,
            y=bt_result["daily_values"].values,
            mode='lines',
            name='策略净值',
            line=dict(color='#1f77b4', width=2)
        ))
        fig.update_layout(
            xaxis_title="日期",
            yaxis_title="净值",
            hovermode='x unified',
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)

        st.info(f"💡 策略说明：每{rebalance_days}天调仓，持有评分Top{top_n}的ETF，等权配置")

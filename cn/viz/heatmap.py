"""轮动热力图：展示板块ETF评分随时间变化"""

import plotly.graph_objects as go
import pandas as pd

from data.etf_universe import get_etf_map


def create_heatmap(score_history: pd.DataFrame) -> go.Figure:
    """创建板块轮动热力图

    Args:
        score_history: index=日期, columns=ETF代码, values=评分
    """
    if score_history.empty:
        return _empty_figure("暂无数据")

    etf_map = get_etf_map()

    # 用ETF名称替换代码作为Y轴标签
    display_names = [
        etf_map[c].name if c in etf_map else c
        for c in score_history.columns
    ]

    # 按最新评分排序
    latest = score_history.iloc[-1]
    sorted_cols = latest.sort_values(ascending=True).index
    sorted_names = [
        etf_map[c].name if c in etf_map else c
        for c in sorted_cols
    ]
    z_data = score_history[sorted_cols].T.values

    fig = go.Figure(data=go.Heatmap(
        z=z_data,
        x=score_history.index.strftime("%m-%d"),
        y=sorted_names,
        colorscale=[
            [0, "#d73027"],
            [0.4, "#fee08b"],
            [0.7, "#d9ef8b"],
            [1, "#1a9850"],
        ],
        zmin=20,
        zmax=80,
        colorbar=dict(title="评分"),
        hovertemplate="日期: %{x}<br>板块: %{y}<br>评分: %{z:.1f}<extra></extra>",
    ))

    fig.update_layout(
        title="板块轮动热力图",
        xaxis_title="日期",
        yaxis_title="",
        height=max(400, len(sorted_cols) * 28),
        margin=dict(l=100, r=20, t=40, b=40),
    )
    return fig


def _empty_figure(text: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=text, xref="paper", yref="paper",
                       x=0.5, y=0.5, showarrow=False, font_size=16)
    fig.update_layout(height=300)
    return fig

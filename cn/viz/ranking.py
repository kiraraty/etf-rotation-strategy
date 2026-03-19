"""评分排行图：展示最新板块ETF综合评分排名"""

import plotly.graph_objects as go
import pandas as pd


def create_ranking_chart(latest_scores: pd.DataFrame) -> go.Figure:
    """创建评分排行条形图

    Args:
        latest_scores: 包含 name, score, signal 列的 DataFrame
    """
    if latest_scores.empty:
        return _empty_figure("暂无评分数据")

    df = latest_scores.sort_values("score", ascending=True).copy()

    # 根据信号设置颜色
    color_map = {
        "强势-关注": "#1a9850",
        "中性-观望": "#fee08b",
        "弱势-回避": "#d73027",
    }
    colors = [color_map.get(s, "#999999") for s in df["signal"]]

    fig = go.Figure(data=go.Bar(
        x=df["score"],
        y=df["name"],
        orientation="h",
        marker_color=colors,
        text=df["score"].round(1),
        textposition="outside",
        hovertemplate=(
            "%{y}<br>"
            "评分: %{x:.1f}<br>"
            "<extra></extra>"
        ),
    ))

    fig.update_layout(
        title="板块ETF综合评分排行",
        xaxis_title="综合评分",
        yaxis_title="",
        height=max(400, len(df) * 28),
        margin=dict(l=100, r=60, t=40, b=40),
        xaxis=dict(range=[0, 105]),
    )
    return fig


def _empty_figure(text: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=text, xref="paper", yref="paper",
                       x=0.5, y=0.5, showarrow=False, font_size=16)
    fig.update_layout(height=300)
    return fig

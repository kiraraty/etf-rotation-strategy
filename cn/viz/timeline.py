"""信号时间线图：展示板块评分随时间变化趋势"""

import plotly.graph_objects as go
import pandas as pd

from data.etf_universe import get_etf_map


def create_timeline(score_history: pd.DataFrame,
                    top_n: int = 5) -> go.Figure:
    """创建评分时间线折线图

    Args:
        score_history: index=日期, columns=ETF代码, values=评分
        top_n: 显示排名前N的ETF
    """
    if score_history.empty:
        return _empty_figure("暂无历史数据")

    etf_map = get_etf_map()

    # 按最新评分取 top_n
    latest = score_history.iloc[-1].sort_values(ascending=False)
    top_codes = latest.head(top_n).index.tolist()

    fig = go.Figure()
    for code in top_codes:
        name = etf_map[code].name if code in etf_map else code
        fig.add_trace(go.Scatter(
            x=score_history.index,
            y=score_history[code],
            mode="lines+markers",
            name=name,
            marker=dict(size=4),
            hovertemplate=f"{name}<br>日期: %{{x}}<br>评分: %{{y:.1f}}<extra></extra>",
        ))

    # 添加阈值线
    fig.add_hline(y=70, line_dash="dash", line_color="green",
                  annotation_text="强势线(70)")
    fig.add_hline(y=40, line_dash="dash", line_color="red",
                  annotation_text="弱势线(40)")

    fig.update_layout(
        title=f"评分趋势 (Top {top_n})",
        xaxis_title="日期",
        yaxis_title="综合评分",
        height=450,
        yaxis=dict(range=[0, 100]),
        legend=dict(orientation="h", yanchor="bottom",
                    y=1.02, xanchor="right", x=1),
        margin=dict(l=60, r=20, t=60, b=40),
    )
    return fig


def _empty_figure(text: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=text, xref="paper", yref="paper",
                       x=0.5, y=0.5, showarrow=False, font_size=16)
    fig.update_layout(height=300)
    return fig

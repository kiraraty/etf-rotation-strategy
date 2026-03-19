"""A股板块ETF轮动自动化分析 Agent - Streamlit 入口"""

import os
from pathlib import Path

# 加载 .env
_env_file = Path(__file__).parent / ".env"
if _env_file.exists():
    for line in _env_file.read_text().strip().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

import streamlit as st

st.set_page_config(
    page_title="A股板块ETF轮动分析",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("A股板块ETF轮动自动化分析")
st.markdown(
    "基于动量、RPS相对强弱、资金流向、波动率等多因子模型，"
    "自动计算板块ETF综合评分与轮动信号。"
)
st.markdown("---")
st.markdown("👈 请从左侧导航选择页面：")
st.markdown(
    "- **主看板** — 热力图 + 排行榜 + 信号时间线\n"
    "- **板块详情** — 单只ETF指标详细分析\n"
    "- **参数配置** — 权重调整、ETF池管理、缓存管理"
)

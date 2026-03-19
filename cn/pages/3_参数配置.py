"""参数配置：权重调整、ETF池管理、缓存管理"""

import streamlit as st

from config import DEFAULT_CONFIG, WeightConfig
from data.cache import clear_cache
from data.etf_universe import get_etf_pool, ETFInfo

st.set_page_config(page_title="参数配置", page_icon="⚙️", layout="wide")
st.title("参数配置")

# 初始化 session_state 中的权重配置
if "weights" not in st.session_state:
    st.session_state.weights = DEFAULT_CONFIG.weights.as_dict()
# 兼容旧 session_state（没有 news_sentiment）
st.session_state.weights.setdefault("news_sentiment", 0.0)

# --- 权重调整 ---
st.subheader("指标权重调整")
st.caption("调整各指标在综合评分中的权重，总和应为1.0")

weight_labels = {
    "momentum_5d": "5日动量",
    "momentum_10d": "10日动量",
    "momentum_20d": "20日动量",
    "rps": "RPS相对强弱",
    "money_flow": "资金流向",
    "volatility": "波动率(反向)",
    "news_sentiment": "新闻情绪(需LLM)",
}

cols = st.columns(3)
new_weights = {}
for i, (key, label) in enumerate(weight_labels.items()):
    with cols[i % 3]:
        new_weights[key] = st.slider(
            label, 0.0, 0.5,
            value=st.session_state.weights[key],
            step=0.05, key=f"w_{key}",
        )

total_weight = sum(new_weights.values())
if abs(total_weight - 1.0) < 0.01:
    st.success(f"权重总和: {total_weight:.2f} ✓")
else:
    st.warning(f"权重总和: {total_weight:.2f}（建议调整为1.0）")

if st.button("应用权重", type="primary"):
    st.session_state.weights = new_weights
    DEFAULT_CONFIG.weights = WeightConfig(**new_weights)
    st.success("权重已更新，请重新运行分析")

st.markdown("---")

# --- ETF池管理 ---
st.subheader("ETF池")
etf_pool = get_etf_pool()

etf_data = [{"代码": e.code, "名称": e.name, "板块": e.sector} for e in etf_pool]
st.dataframe(etf_data, use_container_width=True, height=400)

st.markdown("---")

# --- 信号阈值 ---
st.subheader("信号阈值")
col_t1, col_t2 = st.columns(2)
with col_t1:
    strong_th = st.number_input(
        "强势阈值（>=此值为强势-关注）",
        min_value=50, max_value=95,
        value=int(DEFAULT_CONFIG.signal.strong_threshold),
        step=5,
    )
with col_t2:
    neutral_th = st.number_input(
        "中性阈值（>=此值为中性-观望）",
        min_value=20, max_value=60,
        value=int(DEFAULT_CONFIG.signal.neutral_threshold),
        step=5,
    )

if st.button("应用阈值"):
    DEFAULT_CONFIG.signal.strong_threshold = float(strong_th)
    DEFAULT_CONFIG.signal.neutral_threshold = float(neutral_th)
    st.success("阈值已更新，请重新运行分析")

st.markdown("---")

# --- 缓存管理 ---
st.subheader("缓存管理")
st.caption(
    f"内存缓存TTL: {DEFAULT_CONFIG.cache.memory_ttl_seconds}s | "
    f"文件缓存TTL: {DEFAULT_CONFIG.cache.parquet_ttl_seconds}s"
)

if st.button("清除所有缓存"):
    count = clear_cache()
    st.cache_data.clear()
    st.success(f"已清除 {count} 个缓存文件，内存缓存已重置")

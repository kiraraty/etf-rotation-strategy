"""AI 板块轮动辩论分析"""

import os
import streamlit as st

from config import AppConfig, WeightConfig, DEFAULT_CONFIG

st.set_page_config(page_title="AI辩论分析", page_icon="⚖️", layout="wide")

# --- 自定义样式 ---
st.markdown("""<style>
.block-container {padding-top: 1rem;}
div[data-testid="stMetric"] {
    background: linear-gradient(135deg, #667eea11, #764ba211);
    border: 1px solid #e0e0e0; border-radius: 10px; padding: 12px 16px;
}
.bull-card {
    background: #fff5f5; border-radius: 8px; padding: 12px 16px;
    margin-bottom: 8px; border-left: 4px solid #e53935;
}
.bear-card {
    background: #f5fff5; border-radius: 8px; padding: 12px 16px;
    margin-bottom: 8px; border-left: 4px solid #43a047;
}
.judge-card {
    background: #fffde7; border-radius: 8px; padding: 12px 16px;
    margin-bottom: 8px; border-left: 4px solid #ffc107;
}
.anomaly-card {
    background: #fff3e0; border-radius: 8px; padding: 10px 14px;
    border-left: 4px solid #ff9800; margin-bottom: 8px;
}
.overweight-tag {
    display: inline-block; background: #ffebee; color: #c62828;
    border-radius: 4px; padding: 2px 8px; margin: 2px; font-size: 0.9em;
}
.underweight-tag {
    display: inline-block; background: #e8f5e9; color: #2e7d32;
    border-radius: 4px; padding: 2px 8px; margin: 2px; font-size: 0.9em;
}
</style>""", unsafe_allow_html=True)

st.title("AI 板块轮动辩论分析")

# --- 前置检查 ---
if "analysis_result" not in st.session_state or st.session_state.analysis_result is None:
    st.warning("请先在主看板页面运行量化分析")
    st.stop()

if not os.getenv("LLM_API_KEY"):
    st.error("请设置 LLM_API_KEY 环境变量")
    st.stop()

result = st.session_state.analysis_result
latest_scores = result["latest_scores"]
score_history = result.get("score_history")

if "debate_result" not in st.session_state:
    st.session_state.debate_result = None

# --- 运行辩论 ---
st.markdown("基于量化评分结果，多头与空头分析师进行两轮辩论，裁判综合裁决给出轮动建议。")

STEP_LABELS = {
    "scene": "场景识别",
    "bull_r1": "多头立论 (R1)",
    "bear_r1": "空头立论 (R1)",
    "bull_r2": "多头反驳 (R2)",
    "bear_r2": "空头反驳 (R2)",
    "judge": "裁判裁决",
}
STEP_ORDER = list(STEP_LABELS.keys())

if st.button("运行AI辩论分析", type="primary", use_container_width=True):
    from llm.debate import run_debate

    news_sentiment = st.session_state.get("llm_results")

    status = st.status("AI 辩论分析进行中（共6次LLM调用）...", expanded=True)
    progress_bar = status.progress(0, text="准备中...")
    log_area = status.empty()
    log_lines = []

    def _on_progress(step, step_status, summary, detail):
        idx = STEP_ORDER.index(step) if step in STEP_ORDER else 0
        label = STEP_LABELS.get(step, step)
        if step_status == "running":
            log_lines.append(f"⏳ {label}...")
        elif step_status == "done":
            # 替换最后一个该步骤的 running 行
            for i in range(len(log_lines) - 1, -1, -1):
                if f"⏳ {label}" in log_lines[i]:
                    log_lines[i] = f"✅ {label}: {summary or '完成'}"
                    break
            progress_bar.progress(
                (idx + 1) / len(STEP_ORDER),
                text=f"{label} 完成 ({idx + 1}/{len(STEP_ORDER)})",
            )
        log_area.markdown("\n\n".join(log_lines))

    try:
        st.session_state.debate_result = run_debate(
            latest_scores, score_history, news_sentiment,
            on_progress=_on_progress,
        )
        status.update(label="AI 辩论分析完成", state="complete")
    except Exception as e:
        status.update(label=f"辩论失败: {e}", state="error")
    st.rerun()

# --- 结果展示 ---
debate = st.session_state.debate_result
if debate is None:
    st.info("点击上方按钮开始AI辩论分析")
    st.stop()

judge = debate["judge_verdict"]
scene = debate["scene"]

# --- 裁决摘要 ---
st.markdown("---")
winner = judge.get("winner", "neutral")
winner_label = "多头胜" if winner == "bull" else "空头胜" if winner == "bear" else "平局"
sentiment = judge.get("market_sentiment", "neutral")
sentiment_map = {"bullish": "看多", "bearish": "看空", "neutral": "中性"}

c1, c2, c3, c4 = st.columns(4)
c1.metric("辩论胜方", winner_label)
c2.metric("置信度", f"{judge.get('confidence', 0):.0%}")
c3.metric("风险等级", judge.get("risk_level", "medium"))
c4.metric("市场情绪", sentiment_map.get(sentiment, sentiment))

# --- 轮动策略建议 ---
if judge.get("narrative"):
    st.markdown(
        f'<div class="judge-card"><b>裁判总结:</b> {judge["narrative"]}</div>',
        unsafe_allow_html=True,
    )
if judge.get("rotation_advice"):
    st.info(f"**轮动策略建议:** {judge['rotation_advice']}")

# --- 超配/低配板块 ---
col_over, col_under = st.columns(2)
with col_over:
    st.markdown("**建议超配**")
    tags = "".join(f'<span class="overweight-tag">{s}</span>' for s in judge.get("overweight", []))
    st.markdown(tags or "无", unsafe_allow_html=True)
with col_under:
    st.markdown("**建议低配**")
    tags = "".join(f'<span class="underweight-tag">{s}</span>' for s in judge.get("underweight", []))
    st.markdown(tags or "无", unsafe_allow_html=True)

if judge.get("watch"):
    st.caption("密切关注: " + "、".join(judge["watch"]))

# --- 信号背离预警 ---
anomalies = debate.get("anomalies", [])
if anomalies:
    st.markdown("---")
    st.subheader("信号背离预警")
    for a in anomalies:
        st.markdown(
            f'<div class="anomaly-card">⚠️ {a["warning"]}</div>',
            unsafe_allow_html=True,
        )

# --- 辩论详情 ---
st.markdown("---")
st.subheader("辩论详情")

tab_scene, tab_bull, tab_bear, tab_judge = st.tabs(
    ["场景识别", "多头论证", "空头论证", "裁判裁决"]
)

with tab_scene:
    st.markdown(f"**当前场景:** {scene.get('primary_scene', 'normal')}")
    if scene.get("focus_guidance"):
        st.markdown(f"**分析重点:** {scene['focus_guidance']}")
    if scene.get("key_question"):
        st.markdown(f"**核心问题:** {scene['key_question']}")
    if scene.get("scenes"):
        st.caption(f"识别到的场景: {', '.join(scene['scenes'])}")

with tab_bull:
    bull_r1 = debate["bull_r1"]
    bull_r2 = debate["bull_r2"]
    st.markdown(f"**R1 置信度:** {bull_r1.get('confidence', '?')} → "
                f"**R2 修正:** {bull_r2.get('revised_confidence', '?')}")
    st.markdown("**第一轮立论:**")
    for i, arg in enumerate(bull_r1.get("arguments", []), 1):
        strength = arg.get("strength", "?")
        icon = "🔴" if strength == "strong" else "🟡" if strength == "moderate" else "⚪"
        st.markdown(
            f'{icon} **{i}. [{arg.get("dimension", "")}]** {arg.get("point", "")}'
        )
        if arg.get("data"):
            st.caption(f"　　数据: {arg['data']}")
    if bull_r1.get("biggest_risk"):
        st.warning(f"最大风险: {bull_r1['biggest_risk']}")

    with st.expander("第二轮反驳"):
        for rb in bull_r2.get("rebuttals", []):
            eff = rb.get("effectiveness", "?")
            icon = "💪" if eff == "strong" else "👌" if eff == "moderate" else "🤏"
            st.markdown(f'{icon} 针对「{rb.get("target", "")}」: {rb.get("rebuttal", "")}')
        if bull_r2.get("concessions"):
            st.markdown("**承认的弱点:**")
            for c in bull_r2["concessions"]:
                st.markdown(f"- {c}")
        if bull_r2.get("confidence_change_reason"):
            st.caption(f"置信度变化原因: {bull_r2['confidence_change_reason']}")

with tab_bear:
    bear_r1 = debate["bear_r1"]
    bear_r2 = debate["bear_r2"]
    st.markdown(f"**R1 置信度:** {bear_r1.get('confidence', '?')} → "
                f"**R2 修正:** {bear_r2.get('revised_confidence', '?')}")
    st.markdown("**第一轮立论:**")
    for i, arg in enumerate(bear_r1.get("arguments", []), 1):
        strength = arg.get("strength", "?")
        icon = "🟢" if strength == "strong" else "🟡" if strength == "moderate" else "⚪"
        st.markdown(
            f'{icon} **{i}. [{arg.get("dimension", "")}]** {arg.get("point", "")}'
        )
        if arg.get("data"):
            st.caption(f"　　数据: {arg['data']}")
    if bear_r1.get("biggest_risk"):
        st.warning(f"最大系统性风险: {bear_r1['biggest_risk']}")

    with st.expander("第二轮反驳"):
        for rb in bear_r2.get("rebuttals", []):
            eff = rb.get("effectiveness", "?")
            icon = "💪" if eff == "strong" else "👌" if eff == "moderate" else "🤏"
            st.markdown(f'{icon} 针对「{rb.get("target", "")}」: {rb.get("rebuttal", "")}')
        if bear_r2.get("concessions"):
            st.markdown("**承认的弱点:**")
            for c in bear_r2["concessions"]:
                st.markdown(f"- {c}")
        if bear_r2.get("confidence_change_reason"):
            st.caption(f"置信度变化原因: {bear_r2['confidence_change_reason']}")

with tab_judge:
    verdict = judge.get("verdict", {})
    jc1, jc2 = st.columns(2)
    jc1.metric("多头得分", verdict.get("bull_score", "?"))
    jc2.metric("空头得分", verdict.get("bear_score", "?"))

    if verdict.get("key_factor"):
        st.markdown(f"**决定性因素:** {verdict['key_factor']}")

    if verdict.get("bull_highlights"):
        st.markdown("**采纳的多头论据:**")
        for h in verdict["bull_highlights"]:
            st.markdown(f"- ✅ {h}")
    if verdict.get("bear_highlights"):
        st.markdown("**采纳的空头论据:**")
        for h in verdict["bear_highlights"]:
            st.markdown(f"- ✅ {h}")
    if verdict.get("cross_exam_summary"):
        st.markdown(f"**交叉反驳总结:** {verdict['cross_exam_summary']}")

    if judge.get("reasoning"):
        with st.expander("详细推理过程"):
            st.markdown(judge["reasoning"])

# --- AI情绪评分 + 重算对比 ---
sector_scores = debate.get("sector_scores", {})
if sector_scores:
    st.markdown("---")
    st.subheader("AI情绪评分 & 重算对比")

    # 展示每个板块的AI情绪分
    import pandas as pd
    ss_df = pd.DataFrame([
        {"板块": k, "AI情绪分": v}
        for k, v in sorted(sector_scores.items(), key=lambda x: x[1], reverse=True)
    ])
    st.dataframe(ss_df, use_container_width=True, hide_index=True)

    # --- 重算对比 ---
    st.markdown("#### 纳入AI情绪后的评分对比")
    sentiment_weight = st.slider(
        "AI情绪权重", 0.0, 0.3, 0.10, 0.05,
        help="设置 news_sentiment 在综合评分中的权重占比",
    )
    if sentiment_weight > 0 and "analysis_result" in st.session_state:
        from copy import deepcopy
        from engine.signals import rescore_with_debate

        cfg = deepcopy(DEFAULT_CONFIG)
        cfg.weights.news_sentiment = sentiment_weight
        rescored = rescore_with_debate(
            st.session_state.analysis_result, debate, cfg,
        )
        if rescored is not None and not rescored.empty:
            # 合并原始评分和重算评分
            orig = latest_scores[["code", "name", "score", "signal"]].copy()
            orig.columns = ["code", "名称", "原评分", "原信号"]
            new = rescored[["code", "score", "signal"]].copy()
            new.columns = ["code", "新评分", "新信号"]
            compare = orig.merge(new, on="code")
            compare["评分变化"] = compare["新评分"] - compare["原评分"]
            compare["排名变化"] = (
                compare["原评分"].rank(ascending=False)
                - compare["新评分"].rank(ascending=False)
            ).astype(int)
            compare = compare.sort_values("新评分", ascending=False).reset_index(drop=True)
            compare.index = compare.index + 1
            display = compare[["名称", "原评分", "新评分", "评分变化", "原信号", "新信号", "排名变化"]]
            for c in ["原评分", "新评分", "评分变化"]:
                display[c] = display[c].round(1)
            st.dataframe(display, use_container_width=True)
        else:
            st.warning("重算失败，请检查数据")
    elif sentiment_weight == 0:
        st.caption("将权重调至 > 0 查看AI情绪纳入后的评分变化")

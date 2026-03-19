"""板块轮动 Bull/Bear 辩论系统

6次LLM调用:
  Scene: 市场环境识别 (1次)
  R1: 多头 + 空头 并行立论 (2次)
  R2: 多头 + 空头 并行交叉反驳 (2次)
  Judge: 裁判裁决 (1次)
"""

import json
import logging
import concurrent.futures
from datetime import datetime
from typing import Dict, Optional, Callable

import pandas as pd
import streamlit as st

from llm.provider import OpenAICompatProvider

logger = logging.getLogger(__name__)


# ── Prompt 模板 ──────────────────────────────────────────────

SCENE_PROMPT = """你是A股板块轮动分析的市场环境识别专家。根据以下板块轮动数据快照，判断当前市场环境和分析重点。

当前时间: {current_time}

【板块评分排行】
{ranking_text}

【市场宽度】
{breadth_text}

【板块轮动信号】
{rotation_text}

【新闻情绪】
{sentiment_text}

请判断当前属于以下哪种市场环境（可多选，通常1-2个）：
- broad_rally: 普涨行情（多数板块强势），关注是否过热
- broad_decline: 普跌行情（多数板块弱势），关注是否超卖
- sector_rotation: 明显板块轮动（部分板块快速上升，部分快速下降）
- concentration: 资金集中少数板块（强者恒强，弱者恒弱）
- divergence: 量化信号与消息面背离（需重点关注）
- policy_driven: 政策驱动行情（新闻情绪主导）
- momentum_reversal: 动量反转信号（前期强势板块转弱，弱势板块转强）
- normal: 以上均不明显，均衡分析

请严格输出JSON，不要其他内容：
{{"scenes": ["场景1"], "primary_scene": "最主要场景", "focus_guidance": "2-3句话说明分析重点", "key_question": "当前最核心的一个问题"}}"""


BULL_R1_PROMPT = """你是A股板块轮动的多头分析师。你需要论证当前排名靠前的板块值得超配，轮动信号可靠。

时间: {current_time}
{scene_guidance}

【板块评分排行（量化模型）】
{ranking_text}

【强势板块详情（Top 5）】
{top5_text}

【弱势板块详情（Bottom 5）】
{bottom5_text}

【板块轮动信号】
{rotation_text}

【新闻情绪】
{sentiment_text}

【市场宽度】
{breadth_text}

规则：
1. 站在看多/超配强势板块的立场
2. 论证为什么排名靠前的板块会继续走强
3. 论证当前轮动信号的可靠性
4. 给出3-5个最强论据，每个标注强度和数据支撑
5. 诚实指出你认为最大的风险

输出JSON（简洁，不要其他内容）：
{{"position": "bull", "arguments": [{{"dimension": "维度", "point": "论据", "strength": "strong/moderate/weak", "data": "数据支撑"}}], "overweight_sectors": ["建议超配板块"], "underweight_sectors": ["建议低配板块"], "biggest_risk": "最大风险", "confidence": 0.0到1.0}}"""


BEAR_R1_PROMPT = """你是A股板块轮动的空头/风险分析师。你需要论证当前轮动信号可能不可靠，强势板块可能见顶。

时间: {current_time}
{scene_guidance}

【板块评分排行（量化模型）】
{ranking_text}

【强势板块详情（Top 5）】
{top5_text}

【弱势板块详情（Bottom 5）】
{bottom5_text}

【板块轮动信号】
{rotation_text}

【新闻情绪】
{sentiment_text}

【市场宽度】
{breadth_text}

规则：
1. 站在看空/质疑轮动信号的立场
2. 论证为什么强势板块可能见顶或信号失效
3. 指出量化模型可能遗漏的风险
4. 关注消息面与量化信号的背离
5. 给出3-5个最强论据

输出JSON（简洁，不要其他内容）：
{{"position": "bear", "arguments": [{{"dimension": "维度", "point": "论据", "strength": "strong/moderate/weak", "data": "数据支撑"}}], "risk_sectors": ["高风险板块"], "potential_reversals": ["可能反转的板块"], "biggest_risk": "最大系统性风险", "confidence": 0.0到1.0}}"""


BULL_R2_PROMPT = """多头分析师反驳环节。

{scene_guidance}

【你的第一轮立论】
{own_r1_text}

【空头第一轮立论】
{opponent_r1_text}

反驳对方最强的2-3个论据，承认自己论证中的弱点，给出修正后的置信度。

输出JSON（不要其他内容）：
{{"rebuttals": [{{"target": "对方论据", "rebuttal": "反驳理由", "effectiveness": "strong/moderate/weak"}}], "concessions": ["承认的弱点"], "revised_confidence": 0.0到1.0, "confidence_change_reason": "置信度变化原因"}}"""


BEAR_R2_PROMPT = """空头分析师反驳环节。

{scene_guidance}

【你的第一轮立论】
{own_r1_text}

【多头第一轮立论】
{opponent_r1_text}

反驳对方最强的2-3个论据，承认自己论证中的弱点，给出修正后的置信度。

输出JSON（不要其他内容）：
{{"rebuttals": [{{"target": "对方论据", "rebuttal": "反驳理由", "effectiveness": "strong/moderate/weak"}}], "concessions": ["承认的弱点"], "revised_confidence": 0.0到1.0, "confidence_change_reason": "置信度变化原因"}}"""


JUDGE_PROMPT = """你是A股板块轮动策略的中立裁判。你刚听完多头和空头分析师的两轮辩论。

当前时间: {current_time}
{scene_guidance}

【板块评分排行】
{ranking_text}

【多头分析师完整论证】
{bull_text}

【空头分析师完整论证】
{bear_text}

你的任务：
1. 重点关注经过交叉反驳后仍然成立的"幸存论据"
2. 关注双方主动承认的弱点（concessions）
3. R1→R2置信度大幅降低说明该方论证不扎实
4. 综合量化评分和辩论结果，给出最终轮动建议
5. 为每个板块给出AI情绪评分（-100到100）

评判标准：
- 幸存论据 > 未被反驳的论据 > 被有效反驳的论据
- 硬数据 > 主观判断
- 多维度一致 > 单一维度强信号

请严格输出JSON，不要其他内容：
{{"winner": "bull或bear",
  "rotation_advice": "当前轮动策略建议（2-3句话）",
  "overweight": ["建议超配板块"],
  "underweight": ["建议低配板块"],
  "watch": ["需要密切关注的板块"],
  "confidence": 0.0到1.0,
  "risk_level": "low/medium/high",
  "market_sentiment": "bullish/bearish/neutral",
  "narrative": "一句话总结当前板块轮动格局",
  "reasoning": "详细推理过程（2-3段）",
  "verdict": {{
    "bull_score": 0到100,
    "bear_score": 0到100,
    "key_factor": "决定性因素",
    "bull_highlights": ["采纳的多头论据"],
    "bear_highlights": ["采纳的空头论据"],
    "cross_exam_summary": "交叉反驳总结"
  }},
  "sector_scores": {{"板块名": -100到100的整数}}
}}"""


# ── 辅助函数 ──────────────────────────────────────────────────

def _get_llm() -> OpenAICompatProvider:
    if "llm_provider" not in st.session_state:
        st.session_state.llm_provider = OpenAICompatProvider()
    return st.session_state.llm_provider


def _parse_json(raw: str) -> dict:
    """从 LLM 响应中提取 JSON"""
    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(raw[start:end])
    except (json.JSONDecodeError, ValueError):
        logger.warning(f"JSON parse failed: {raw[:200]}")
    return {}


# ── 上下文构建 ────────────────────────────────────────────────

def _format_ranking(latest_scores: pd.DataFrame, trends: dict) -> str:
    """格式化评分排行文本"""
    lines = []
    for _, row in latest_scores.iterrows():
        code = row["code"]
        trend_delta = trends.get(code, 0)
        trend_arrow = "↑" if trend_delta > 2 else "↓" if trend_delta < -2 else "→"
        lines.append(
            f"{row.name}. {row['name']}({row['sector']}) "
            f"评分:{row['score']:.1f} 信号:{row['signal']} "
            f"5日动量:{row.get('momentum_5d', 0):.1f}% "
            f"趋势:{trend_arrow}{trend_delta:+.1f}"
        )
    return "\n".join(lines)


def _format_sector_detail(df: pd.DataFrame, trends: dict,
                          news_sentiment: Optional[dict]) -> str:
    """格式化板块详情（Top/Bottom）"""
    lines = []
    for _, row in df.iterrows():
        code = row["code"]
        sector = row["sector"]
        trend_delta = trends.get(code, 0)
        line = (
            f"- {row['name']}({sector}): "
            f"评分{row['score']:.1f}, 信号={row['signal']}, "
            f"5日动量={row.get('momentum_5d', 0):.1f}%, "
            f"10日动量={row.get('momentum_10d', 0):.1f}%, "
            f"20日动量={row.get('momentum_20d', 0):.1f}%, "
            f"RPS={row.get('rps', 0):.2f}, "
            f"资金流={row.get('money_flow', 0):.2f}, "
            f"波动率={row.get('volatility', 0):.1f}%, "
            f"5日趋势={trend_delta:+.1f}"
        )
        if news_sentiment and sector in news_sentiment:
            ns = news_sentiment[sector]
            line += f", 新闻情绪={ns.get('sentiment_score', 0):+d}({ns.get('summary', '')})"
        lines.append(line)
    return "\n".join(lines)


def _detect_rotation(score_history: Optional[pd.DataFrame]) -> list:
    """检测板块轮动信号：比较5天前和现在的排名变化"""
    if score_history is None or len(score_history) < 5:
        return []
    recent = score_history.tail(1).iloc[0]
    past = score_history.iloc[-5]
    recent_rank = recent.rank(ascending=False)
    past_rank = past.rank(ascending=False)
    signals = []
    for code in recent.index:
        delta = past_rank.get(code, 0) - recent_rank.get(code, 0)
        if abs(delta) >= 5:
            direction = "上升" if delta > 0 else "下降"
            signals.append(
                f"{code}: 排名从第{int(past_rank[code])}→第{int(recent_rank[code])}（{direction}{abs(int(delta))}位）"
            )
    return signals


def _format_sentiment(news_sentiment: Optional[dict]) -> str:
    """格式化新闻情绪文本"""
    if not news_sentiment:
        return "暂无新闻情绪数据"
    lines = []
    for sector, info in sorted(
        news_sentiment.items(),
        key=lambda x: x[1].get("sentiment_score", 0),
        reverse=True,
    ):
        score = info.get("sentiment_score", 0)
        summary = info.get("summary", "")
        lines.append(f"- {sector}: 情绪{score:+d}, {summary}")
    return "\n".join(lines) if lines else "暂无新闻情绪数据"


def build_debate_context(latest_scores: pd.DataFrame,
                         score_history: Optional[pd.DataFrame],
                         news_sentiment: Optional[dict] = None) -> dict:
    """构建辩论共享上下文"""
    # 评分趋势（最近5个交易日变化）
    trends: Dict[str, float] = {}
    if score_history is not None and len(score_history) >= 5:
        recent = score_history.tail(5)
        for col in recent.columns:
            trends[col] = float(recent[col].iloc[-1] - recent[col].iloc[0])

    # 市场宽度
    strong = len(latest_scores[latest_scores["signal"] == "强势-关注"])
    weak = len(latest_scores[latest_scores["signal"] == "弱势-回避"])
    total = len(latest_scores)

    # 轮动信号
    rotation = _detect_rotation(score_history)

    return {
        "current_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "ranking_text": _format_ranking(latest_scores, trends),
        "top5_text": _format_sector_detail(latest_scores.head(5), trends, news_sentiment),
        "bottom5_text": _format_sector_detail(latest_scores.tail(5), trends, news_sentiment),
        "rotation_text": "\n".join(rotation) if rotation else "近5日无明显轮动",
        "sentiment_text": _format_sentiment(news_sentiment),
        "breadth_text": f"强势板块: {strong}个, 弱势板块: {weak}个, 共{total}个板块",
        "scene_guidance": "",  # 场景识别后填充
    }


# ── 辩论格式化 ────────────────────────────────────────────────

def _format_r1_for_rebuttal(case: dict) -> str:
    """格式化 R1 立论供反驳使用"""
    lines = [f"立场: {case.get('position', '?')}"]
    lines.append(f"置信度: {case.get('confidence', '?')}")
    for i, arg in enumerate(case.get("arguments", []), 1):
        lines.append(
            f"{i}. [{arg.get('strength', '?')}][{arg.get('dimension', '?')}] "
            f"{arg.get('point', '')}"
        )
        if arg.get("data"):
            lines.append(f"   数据: {arg['data']}")
    lines.append(f"最大风险: {case.get('biggest_risk', '未说明')}")
    return "\n".join(lines)


def _format_full_case(r1: dict, r2: dict, position: str) -> str:
    """格式化完整辩论记录（R1+R2）供裁判使用"""
    label = "多头" if position == "bull" else "空头"
    lines = [f"=== {label}第一轮立论 ==="]
    lines.append(f"置信度: {r1.get('confidence', '?')}")
    for i, arg in enumerate(r1.get("arguments", []), 1):
        lines.append(
            f"{i}. [{arg.get('strength', '?')}][{arg.get('dimension', '?')}] "
            f"{arg.get('point', '')}"
        )
        if arg.get("data"):
            lines.append(f"   数据: {arg['data']}")
    lines.append(f"最大风险: {r1.get('biggest_risk', '未说明')}")

    lines.append(f"\n=== {label}第二轮反驳 ===")
    lines.append(
        f"修正置信度: {r2.get('revised_confidence', '?')} "
        f"(原: {r1.get('confidence', '?')})"
    )
    lines.append(f"变化原因: {r2.get('confidence_change_reason', '未说明')}")
    for i, rb in enumerate(r2.get("rebuttals", []), 1):
        lines.append(
            f"  {i}. [{rb.get('effectiveness', '?')}] "
            f"针对「{rb.get('target', '?')}」: {rb.get('rebuttal', '')}"
        )
    concessions = r2.get("concessions", [])
    if concessions:
        lines.append("承认的弱点:")
        for c in concessions:
            lines.append(f"  - {c}")
    return "\n".join(lines)


# ── LLM 调用函数 ─────────────────────────────────────────────

_SCENE_SYSTEM = "你是A股市场环境识别专家，擅长判断板块轮动格局。回复用中文，严格输出JSON。"
_BULL_SYSTEM = "你是A股板块轮动多头分析师，擅长发现板块上涨机会。回复用中文，严格输出JSON。"
_BEAR_SYSTEM = "你是A股板块轮动空头/风险分析师，擅长识别风险和信号失效。回复用中文，严格输出JSON。"
_JUDGE_SYSTEM = "你是A股板块轮动策略的中立裁判，客观公正，基于证据做决策。回复用中文，严格输出JSON。"


def _call_scene(llm: OpenAICompatProvider, ctx: dict) -> dict:
    prompt = SCENE_PROMPT.format(**ctx)
    raw = llm.analyze_with_role(_SCENE_SYSTEM, prompt)
    result = _parse_json(raw)
    result.setdefault("scenes", ["normal"])
    result.setdefault("primary_scene", "normal")
    result.setdefault("focus_guidance", "")
    result.setdefault("key_question", "")
    return result


def _call_bull_r1(llm: OpenAICompatProvider, ctx: dict) -> dict:
    prompt = BULL_R1_PROMPT.format(**ctx)
    raw = llm.analyze_with_role(_BULL_SYSTEM, prompt)
    result = _parse_json(raw)
    result.setdefault("position", "bull")
    result.setdefault("arguments", [])
    result.setdefault("overweight_sectors", [])
    result.setdefault("underweight_sectors", [])
    result.setdefault("biggest_risk", "")
    result.setdefault("confidence", 0.5)
    return result


def _call_bear_r1(llm: OpenAICompatProvider, ctx: dict) -> dict:
    prompt = BEAR_R1_PROMPT.format(**ctx)
    raw = llm.analyze_with_role(_BEAR_SYSTEM, prompt)
    result = _parse_json(raw)
    result.setdefault("position", "bear")
    result.setdefault("arguments", [])
    result.setdefault("risk_sectors", [])
    result.setdefault("potential_reversals", [])
    result.setdefault("biggest_risk", "")
    result.setdefault("confidence", 0.5)
    return result


def _fill_r2_defaults(r2: dict) -> dict:
    r2.setdefault("rebuttals", [])
    r2.setdefault("concessions", [])
    r2.setdefault("revised_confidence", 0.5)
    r2.setdefault("confidence_change_reason", "")
    return r2


def _call_bull_r2(llm: OpenAICompatProvider, ctx: dict,
                  own_r1_text: str, opponent_r1_text: str) -> dict:
    prompt = BULL_R2_PROMPT.format(
        scene_guidance=ctx.get("scene_guidance", ""),
        own_r1_text=own_r1_text,
        opponent_r1_text=opponent_r1_text,
    )
    raw = llm.analyze_with_role(_BULL_SYSTEM, prompt)
    return _fill_r2_defaults(_parse_json(raw))


def _call_bear_r2(llm: OpenAICompatProvider, ctx: dict,
                  own_r1_text: str, opponent_r1_text: str) -> dict:
    prompt = BEAR_R2_PROMPT.format(
        scene_guidance=ctx.get("scene_guidance", ""),
        own_r1_text=own_r1_text,
        opponent_r1_text=opponent_r1_text,
    )
    raw = llm.analyze_with_role(_BEAR_SYSTEM, prompt)
    return _fill_r2_defaults(_parse_json(raw))


def _call_judge(llm: OpenAICompatProvider, ctx: dict,
                bull_r1: dict, bull_r2: dict,
                bear_r1: dict, bear_r2: dict) -> dict:
    bull_text = _format_full_case(bull_r1, bull_r2, "bull")
    bear_text = _format_full_case(bear_r1, bear_r2, "bear")
    prompt = JUDGE_PROMPT.format(
        current_time=ctx["current_time"],
        scene_guidance=ctx.get("scene_guidance", ""),
        ranking_text=ctx["ranking_text"],
        bull_text=bull_text,
        bear_text=bear_text,
    )
    raw = llm.analyze_with_role(_JUDGE_SYSTEM, prompt)
    result = _parse_json(raw)
    result.setdefault("winner", "neutral")
    result.setdefault("rotation_advice", "")
    result.setdefault("overweight", [])
    result.setdefault("underweight", [])
    result.setdefault("watch", [])
    result.setdefault("confidence", 0.5)
    result.setdefault("risk_level", "medium")
    result.setdefault("market_sentiment", "neutral")
    result.setdefault("narrative", "")
    result.setdefault("reasoning", "")
    result.setdefault("verdict", {})
    result.setdefault("sector_scores", {})
    return result


# ── 异常检测 ─────────────────────────────────────────────────

def _detect_anomalies(latest_scores: pd.DataFrame,
                      judge_verdict: dict,
                      news_sentiment: Optional[dict]) -> list:
    """检测量化信号与AI分析的背离"""
    anomalies = []
    sector_scores = judge_verdict.get("sector_scores", {})

    for _, row in latest_scores.iterrows():
        sector = row["sector"]
        quant_score = row["score"]
        ai_score = sector_scores.get(sector, 0)

        if quant_score >= 70 and ai_score < -30:
            anomalies.append({
                "sector": sector,
                "name": row["name"],
                "type": "quant_bull_ai_bear",
                "quant_score": round(quant_score, 1),
                "ai_score": ai_score,
                "warning": (
                    f"{row['name']}({sector}): "
                    f"量化评分{quant_score:.0f}(强势) 但AI情绪{ai_score}(看空)，需警惕"
                ),
            })
        elif quant_score < 40 and ai_score > 30:
            anomalies.append({
                "sector": sector,
                "name": row["name"],
                "type": "quant_bear_ai_bull",
                "quant_score": round(quant_score, 1),
                "ai_score": ai_score,
                "warning": (
                    f"{row['name']}({sector}): "
                    f"量化评分{quant_score:.0f}(弱势) 但AI情绪{ai_score}(看多)，可能有反转机会"
                ),
            })
    return anomalies


# ── 主编排函数 ────────────────────────────────────────────────

def run_debate(
    latest_scores: pd.DataFrame,
    score_history: Optional[pd.DataFrame],
    news_sentiment: Optional[dict] = None,
    on_progress: Optional[Callable] = None,
) -> dict:
    """运行完整辩论流程（6次LLM调用）

    Args:
        on_progress: callback(step, status, summary, detail)
            step: "scene"|"bull_r1"|"bear_r1"|"bull_r2"|"bear_r2"|"judge"
            status: "running"|"done"|"error"
    Returns:
        {scene, bull_r1, bull_r2, bear_r1, bear_r2,
         judge_verdict, sector_scores, anomalies}
    """
    llm = _get_llm()
    ctx = build_debate_context(latest_scores, score_history, news_sentiment)

    # ── Step 1: 场景识别 ──
    if on_progress:
        on_progress("scene", "running", None, None)
    try:
        scene = _call_scene(llm, ctx)
    except Exception as e:
        logger.error(f"Scene recognition failed: {e}")
        scene = {"primary_scene": "normal", "focus_guidance": "", "key_question": ""}
    ctx["scene_guidance"] = (
        f"【场景: {scene.get('primary_scene', 'normal')}】"
        f"{scene.get('focus_guidance', '')}"
    )
    if on_progress:
        on_progress("scene", "done", scene.get("primary_scene"), scene.get("focus_guidance"))

    # ── Step 2: R1 并行立论 ──
    if on_progress:
        on_progress("bull_r1", "running", None, None)
        on_progress("bear_r1", "running", None, None)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        f_bull = pool.submit(_call_bull_r1, llm, ctx)
        f_bear = pool.submit(_call_bear_r1, llm, ctx)
        bull_r1 = f_bull.result(timeout=120)
        bear_r1 = f_bear.result(timeout=120)
    if on_progress:
        on_progress("bull_r1", "done", f"置信度 {bull_r1.get('confidence')}", None)
        on_progress("bear_r1", "done", f"置信度 {bear_r1.get('confidence')}", None)

    # ── Step 3: R2 并行反驳 ──
    bull_r1_text = _format_r1_for_rebuttal(bull_r1)
    bear_r1_text = _format_r1_for_rebuttal(bear_r1)
    if on_progress:
        on_progress("bull_r2", "running", None, None)
        on_progress("bear_r2", "running", None, None)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        f_bull2 = pool.submit(_call_bull_r2, llm, ctx, bull_r1_text, bear_r1_text)
        f_bear2 = pool.submit(_call_bear_r2, llm, ctx, bear_r1_text, bull_r1_text)
        bull_r2 = f_bull2.result(timeout=120)
        bear_r2 = f_bear2.result(timeout=120)
    if on_progress:
        on_progress("bull_r2", "done", f"修正置信度 {bull_r2.get('revised_confidence')}", None)
        on_progress("bear_r2", "done", f"修正置信度 {bear_r2.get('revised_confidence')}", None)

    # ── Step 4: 裁判裁决 ──
    if on_progress:
        on_progress("judge", "running", None, None)
    judge_verdict = _call_judge(llm, ctx, bull_r1, bull_r2, bear_r1, bear_r2)
    if on_progress:
        on_progress("judge", "done", judge_verdict.get("narrative"), None)

    # ── Step 5: 异常检测 ──
    anomalies = _detect_anomalies(latest_scores, judge_verdict, news_sentiment)

    return {
        "scene": scene,
        "bull_r1": bull_r1,
        "bull_r2": bull_r2,
        "bear_r1": bear_r1,
        "bear_r2": bear_r2,
        "judge_verdict": judge_verdict,
        "sector_scores": judge_verdict.get("sector_scores", {}),
        "anomalies": anomalies,
    }

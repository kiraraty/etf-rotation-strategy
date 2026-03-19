"""用LLM分析板块新闻情绪"""
import os
from anthropic import Anthropic

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

def analyze_sector_sentiment(sector: str, news_list: list) -> dict:
    """分析板块新闻情绪
    
    Args:
        sector: 板块名称
        news_list: [{"title": "...", "summary": "..."}]
    
    Returns:
        {
            "sentiment_score": int,  # -100到100
            "reasoning": str,
            "key_points": list
        }
    """
    if not news_list:
        return {"sentiment_score": 0, "reasoning": "无新闻", "key_points": []}
    
    # 构建prompt
    news_text = "\n".join([
        f"- {item.get('title', '')}: {item.get('summary', '')[:100]}"
        for item in news_list[:10]
    ])
    
    prompt = f"""分析以下{sector}板块的新闻,给出情绪评分:

新闻列表:
{news_text}

请给出:
1. 情绪评分(-100到100): -100=极度利空, 0=中性, 100=极度利好
2. 理由(50字内)
3. 关键要点(3条以内)

直接输出JSON格式:
{{"sentiment_score": 数字, "reasoning": "理由", "key_points": ["要点1", "要点2"]}}"""
    
    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        
        import json
        result = json.loads(response.content[0].text)
        return result
    except Exception as e:
        print(f"分析{sector}失败: {e}")
        return {"sentiment_score": 0, "reasoning": "分析失败", "key_points": []}


def analyze_all_sectors(news_summary: dict) -> dict:
    """批量分析所有板块
    
    Args:
        news_summary: {sector: {"etf_news": df, "cls_matched": df}}
    
    Returns:
        {sector: {"sentiment_score": int, "reasoning": str, "key_points": list}}
    """
    results = {}
    for sector, data in news_summary.items():
        # 合并新闻
        news_list = []
        if "etf_news" in data and not data["etf_news"].empty:
            news_list.extend(data["etf_news"].to_dict("records"))
        if "cls_matched" in data and not data["cls_matched"].empty:
            news_list.extend(data["cls_matched"].to_dict("records"))
        
        results[sector] = analyze_sector_sentiment(sector, news_list)
    
    return results

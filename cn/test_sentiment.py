"""测试LLM情绪分析"""
import sys
sys.path.insert(0, '/Users/kirara/Desktop/astocketf')

from data.etf_universe import get_etf_map
from data.news import fetch_all_sector_news_summary
from data.sentiment_analyzer import analyze_all_sectors

print("获取新闻...")
etf_map = get_etf_map()
news_summary = fetch_all_sector_news_summary(etf_map)

print("\n分析情绪...")
sentiments = analyze_all_sectors(news_summary)

print("\n" + "=" * 60)
print("板块情绪分析结果")
print("=" * 60)

# 按情绪评分排序
sorted_sectors = sorted(sentiments.items(), 
                       key=lambda x: x[1]["sentiment_score"], 
                       reverse=True)

for sector, result in sorted_sectors[:10]:
    score = result["sentiment_score"]
    reasoning = result["reasoning"]
    print(f"\n{sector}: {score:+d}分")
    print(f"  理由: {reasoning}")
    if result.get("key_points"):
        for point in result["key_points"]:
            print(f"  - {point}")

print("\n" + "=" * 60)

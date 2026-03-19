import sys
sys.path.insert(0, '/Users/kirara/Desktop/astocketf')
from config import DEFAULT_CONFIG
from engine.signals import run_analysis
from engine.backtest import run_backtest

print("获取数据...")
result = run_analysis(period="daily", days=1250, config=DEFAULT_CONFIG)
score_df = result["score_history"]
all_hist = result["all_hist"]

split_idx = int(len(score_df) * 0.6)
test_scores = score_df.iloc[split_idx:]

print("\n" + "=" * 60)
print("费率对比 (Top2, 3天调仓, 测试集)")
print("=" * 60)

# 正确费率: 万0.5单边 = 0.00005
correct = run_backtest(test_scores, all_hist, 2, 3, 0.00005)
print(f"\n正确费率(万0.5单边 = 0.005%):")
print(f"  累计收益: {correct['cumulative_return']*100:.2f}%")
print(f"  夏普比率: {correct['sharpe_ratio']:.2f}")

# 之前用的费率
old = run_backtest(test_scores, all_hist, 2, 3, 0.001)
print(f"\n之前费率(万10 = 0.1%):")
print(f"  累计收益: {old['cumulative_return']*100:.2f}%")
print(f"  夏普比率: {old['sharpe_ratio']:.2f}")

print(f"\n收益差异: +{(correct['cumulative_return']-old['cumulative_return'])*100:.2f}%")
print("=" * 60)

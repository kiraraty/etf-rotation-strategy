import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 1. 环境准备
HK_DIR = '/Users/kirara/Desktop/etf-rotation-strategy/hk'
sys.path.insert(0, HK_DIR)
from engine.backtest import run_backtest
from data.etf_universe import get_etf_codes

print("="*60)
print(f"🚀 开始港股ETF轮动策略5年期回测 (2021-2026)")
print("="*60)

# 2. 读取数据 (CSV)
all_hist = {}
cache_dir = os.path.join(HK_DIR, 'data/.cache')
etf_codes = get_etf_codes()

for code in etf_codes:
    safe_code = code.replace(".", "_")
    file_path = f"{cache_dir}/etf_hist_{safe_code}.csv"
    if os.path.exists(file_path):
        df = pd.read_csv(file_path, index_col=0, parse_dates=True)
        df.index = df.index.tz_localize(None)
        if not df.empty:
            all_hist[code] = df

print(f"成功加载 {len(all_hist)} 个 ETF 数据")

# 3. 计算评分历史 (20日动量)
# 找出所有数据共有日期范围
all_dates = sorted(set().union(*(df.index for df in all_hist.values())))
start_date = datetime.now() - timedelta(days=5*365)
all_dates = [d for d in all_dates if d >= start_date]

scores_dict = {}
for date in all_dates:
    day_scores = {}
    for code, df in all_hist.items():
        if date in df.index:
            idx = df.index.get_loc(date)
            if idx >= 20:
                prev_price = df.iloc[idx-20]['close']
                curr_price = df.iloc[idx]['close']
                ret = curr_price / prev_price - 1
                day_scores[code] = ret * 100
    if day_scores:
        scores_dict[date] = pd.Series(day_scores)

score_df = pd.DataFrame(scores_dict).T
print(f"回测周期: {score_df.index[0].date()} 至 {score_df.index[-1].date()} ({len(score_df)} 个交易日)")

# 4. 运行回测 (使用最优参数)
TOP_N = 5
REBALANCE_DAYS = 9
FEE_RATE = 0.0005 

result = run_backtest(score_df, all_hist, TOP_N, REBALANCE_DAYS, FEE_RATE)

# 5. 计算基准 (2800.HK 盈富基金)
benchmark_code = "2800.HK"
bench_df = all_hist[benchmark_code]
# 使用 reindex 并前向填充处理缺失日期
bench_prices = bench_df['close'].reindex(score_df.index, method='ffill')
bench_returns = bench_prices.pct_change().fillna(0)
bench_cum = (1 + bench_returns).cumprod()

# 6. 计算年化指标
def calc_annual_metrics(daily_values, cumulative_return):
    days = len(daily_values)
    years = days / 252.0
    annual_return = (1 + cumulative_return) ** (1/years) - 1
    
    daily_rets = daily_values.pct_change().dropna()
    sharpe = daily_rets.mean() / daily_rets.std() * np.sqrt(252) if daily_rets.std() > 0 else 0
    
    cummax = daily_values.cummax()
    drawdown = (daily_values - cummax) / cummax
    mdd = drawdown.min()
    
    return annual_return, sharpe, mdd

strategy_ann, strategy_sharpe, strategy_mdd = calc_annual_metrics(result['daily_values'], result['cumulative_return'])
bench_ann, bench_sharpe, bench_mdd = calc_annual_metrics(bench_cum, bench_cum.iloc[-1] - 1)

# 7. 输出结果
print("\n" + "="*20 + " 5年期策略表现 (vs 盈富基金) " + "="*20)
print(f"{'指标':<15} | {'策略 (轮动)':<15} | {'基准 (2800.HK)':<15}")
print("-" * 65)
print(f"{'累计收益':<15} | {result['cumulative_return']*100:>14.2f}% | { (bench_cum.iloc[-1]-1)*100:>14.2f}%")
print(f"{'年化收益':<15} | {strategy_ann*100:>14.2f}% | {bench_ann*100:>14.2f}%")
print(f"{'夏普比率':<15} | {strategy_sharpe:>14.2f} | {bench_sharpe:>14.2f}")
print(f"{'最大回撤':<15} | {strategy_mdd*100:>14.2f}% | {bench_mdd*100:>14.2f}%")
print(f"{'胜率':<15} | {result['win_rate']*100:>14.1f}% | {'-':>15}")
print("=" * 65)

# 8. 当前持仓
last_date = score_df.index[-1]
last_scores = score_df.loc[last_date].sort_values(ascending=False).head(TOP_N)
from data.etf_universe import get_etf_map
etf_map = get_etf_map()

print(f"\n当前建议持仓 (调仓参考日期: {last_date.date()}):")
for i, (code, score) in enumerate(last_scores.items(), 1):
    name = etf_map.get(code, {}).get('name', 'Unknown')
    print(f"{i}. {code:<10} {name:<10} (20日动量评分: {score:>6.2f}%)")


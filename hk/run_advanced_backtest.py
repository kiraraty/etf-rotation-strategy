import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 1. 环境准备
HK_DIR = '/Users/kirara/Desktop/etf-rotation-strategy/hk'
sys.path.insert(0, HK_DIR)
from data.etf_universe import get_etf_codes, get_etf_map

print("="*60)
print(f"🛡️  开始港股ETF轮动【进阶防守版】策略回测")
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

# 3. 计算指标
# 找出共有日期 (5年内)
all_dates = sorted(set().union(*(df.index for df in all_hist.values())))
start_date = datetime.now() - timedelta(days=5*365)
all_dates = [d for d in all_dates if d >= start_date]

# 计算基准 2800.HK 的 60日均线 (大盘择时用)
bench_df = all_hist["2800.HK"]
bench_ma60 = bench_df['close'].rolling(window=60).mean()

# 4. 进阶版回测引擎 (带防守逻辑)
def run_advanced_rotation(dates, all_hist, top_n=5, rebalance_days=10, fee_rate=0.001):
    portfolio_value = 1.0
    daily_values = []
    holdings = {} # {code: weight}
    last_rebalance = 0
    
    cash_history = [] # 记录现金占比

    for i, date in enumerate(dates):
        # --- 调仓逻辑 ---
        if i > 0 and (i - last_rebalance >= rebalance_days):
            prev_date = dates[i-1]
            
            # A. 大盘择时检查 (Benchmark MA60)
            is_market_bull = False
            if prev_date in bench_df.index:
                is_market_bull = bench_df.loc[prev_date, 'close'] > bench_ma60.loc[prev_date]
            
            # B. 计算所有ETF动量评分
            day_scores = {}
            for code, df in all_hist.items():
                if prev_date in df.index:
                    idx = df.index.get_loc(prev_date)
                    if idx >= 20:
                        ret = df.iloc[idx]['close'] / df.iloc[idx-20]['close'] - 1
                        day_scores[code] = ret
            
            # C. 过滤：只选动量为正的ETF (绝对动量)
            positive_scores = {c: s for c, s in day_scores.items() if s > 0}
            
            # D. 最终决策
            new_holdings = {}
            if not is_market_bull:
                # 大盘走势差，直接空仓 (躺平防守)
                new_holdings = {}
            else:
                # 大盘好，选正收益的前N名
                sorted_codes = sorted(positive_scores.keys(), key=lambda x: positive_scores[x], reverse=True)
                top_codes = sorted_codes[:top_n]
                if top_codes:
                    weight = 1.0 / len(top_codes) # 尽量等权，如果没有N个就按实际个数分
                    new_holdings = {code: weight for code in top_codes}

            # 计算换手费
            turnover = sum(abs(new_holdings.get(c, 0) - holdings.get(c, 0)) for c in set(new_holdings)|set(holdings))
            portfolio_value *= (1 - turnover * fee_rate)
            
            holdings = new_holdings
            last_rebalance = i
        
        # --- 每日净值计算 ---
        day_return = 0
        if holdings:
            for code, weight in holdings.items():
                if code in all_hist and date in all_hist[code].index:
                    df = all_hist[code]
                    if i > 0 and dates[i-1] in df.index:
                        ret = df.loc[date, 'close'] / df.loc[dates[i-1], 'close'] - 1
                        day_return += weight * ret
        
        portfolio_value *= (1 + day_return)
        daily_values.append(portfolio_value)
        cash_history.append(1.0 if not holdings else 0.0)

    return pd.Series(daily_values, index=dates), pd.Series(cash_history, index=dates)

# 运行进阶策略
# 参数设为更稳健的：Top 3 (聚焦), 10天调仓, 0.1%摩擦成本
strategy_values, cash_history = run_advanced_rotation(all_dates, all_hist, top_n=3, rebalance_days=10, fee_rate=0.001)

# 计算基准 (2800.HK)
bench_prices = all_hist["2800.HK"]['close'].reindex(all_dates, method='ffill')
bench_cum = (bench_prices / bench_prices.iloc[0])

# 计算指标函数
def get_metrics(v):
    ret = v.iloc[-1] - 1
    ann_ret = (1 + ret) ** (252/len(v)) - 1
    dd = (v - v.cummax()) / v.cummax()
    mdd = dd.min()
    vol = v.pct_change().std() * np.sqrt(252)
    sharpe = ann_ret / vol if vol > 0 else 0
    return ret, ann_ret, mdd, sharpe

s_ret, s_ann, s_mdd, s_sharpe = get_metrics(strategy_values)
b_ret, b_ann, b_mdd, b_sharpe = get_metrics(bench_cum)

print("\n" + "="*20 + " 进阶防守版 vs 原版/基准 " + "="*20)
print(f"{'指标':<15} | {'进阶策略(带防守)':<15} | {'基准(2800.HK)':<15}")
print("-" * 65)
print(f"{'累计收益':<15} | {s_ret*100:>14.2f}% | {b_ret*100:>14.2f}%")
print(f"{'年化收益':<15} | {s_ann*100:>14.2f}% | {b_ann*100:>14.2f}%")
print(f"{'夏普比率':<15} | {s_sharpe:>14.2f} | {b_sharpe:>14.2f}")
print(f"{'最大回撤':<15} | {s_mdd*100:>14.2f}% | {b_mdd*100:>14.2f}%")
print(f"{'空仓避险天数':<15} | {int(cash_history.sum()):>11} 天 | {'0':>15} 天")
print("=" * 65)

# 当前持仓
last_date = all_dates[-1]
etf_map = get_etf_map()
# 模拟最后一次调仓逻辑
prev_date = all_dates[-1]
is_market_bull = bench_df.loc[prev_date, 'close'] > bench_ma60.loc[prev_date] if prev_date in bench_df.index else False
day_scores = {}
for code, df in all_hist.items():
    if prev_date in df.index:
        idx = df.index.get_loc(prev_date)
        if idx >= 20:
            day_scores[code] = (df.iloc[idx]['close'] / df.iloc[idx-20]['close'] - 1) * 100

sorted_scores = sorted([ (c,s) for c,s in day_scores.items() if s > 0], key=lambda x:x[1], reverse=True)

print(f"\n当前实盘指导 (日期: {last_date.date()}):")
print(f"大盘状态: {'🟢 牛市区域 (持仓)' if is_market_bull else '🔴 熊市区域 (空仓避险)'}")
if not is_market_bull:
    print("📢 建议：当前大盘处于60日线下，建议空仓或极低仓位观望。")
else:
    print("📢 建议持仓Top 3:")
    for i, (code, score) in enumerate(sorted_scores[:3], 1):
        print(f"{i}. {code:<10} {etf_map.get(code,{}).get('name'):<10} (20日动量: {score:>6.2f}%)")


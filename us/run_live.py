"""实盘自动交易"""
import pandas as pd
from data.etf_universe import get_etf_codes, BENCHMARK
from data.fetcher import fetch_all_etfs, fetch_etf_data
from engine.indicators import calc_all_indicators
from engine.scorer import score_cross_section
from config import DEFAULT_CONFIG
from broker.ibkr_client import IBKRClient

print("=" * 60)
print("美股ETF轮动 - 实盘交易")
print("=" * 60)

# 连接IBKR
client = IBKRClient(host='127.0.0.1', port=4002)  # 4002=IB Gateway Paper
if not client.connect():
    print("无法连接IBKR，请确保TWS或IB Gateway已启动")
    exit(1)

# 获取账户信息
account_value = client.get_account_value()
print(f"\n账户净值: ${account_value:,.2f}")

# 获取数据并计算评分
print("\n正在计算最新评分...")
etf_codes = get_etf_codes()
all_hist = fetch_all_etfs(etf_codes, period="3mo")
bench_df = fetch_etf_data(BENCHMARK, period="3mo")

# 计算指标
all_indicators = {}
for code, hist_df in all_hist.items():
    indicators = calc_all_indicators(hist_df, bench_df)
    all_indicators[code] = indicators

# 获取最新评分
latest = {}
for code, ind_df in all_indicators.items():
    valid = ind_df.dropna(how='all')
    if not valid.empty:
        latest[code] = valid.iloc[-1]

cs_df = pd.DataFrame(latest).T
scores = score_cross_section(cs_df, DEFAULT_CONFIG.weights)
top2 = scores.nlargest(2)

print("\n最新评分Top2:")
for symbol, score in top2.items():
    print(f"  {symbol}: {score:.2f}")

# 调仓
print("\n开始调仓...")
target_weights = {symbol: 0.5 for symbol in top2.index}
orders = client.rebalance(target_weights)

print("\n交易完成:")
for order in orders:
    print(f"  {order['action']} {order['quantity']} {order['symbol']} - {order['status']}")

client.disconnect()
print("\n" + "=" * 60)

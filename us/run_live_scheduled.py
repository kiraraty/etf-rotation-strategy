"""实盘自动交易 - 支持调仓周期控制"""
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from data.etf_universe import get_etf_codes, BENCHMARK
from data.fetcher import fetch_all_etfs, fetch_etf_data
from engine.indicators import calc_all_indicators
from engine.scorer import score_cross_section
from config import DEFAULT_CONFIG
from broker.ibkr_client import IBKRClient

REBALANCE_DAYS = 4  # 调仓间隔(天)
STATE_FILE = Path(__file__).parent / ".last_rebalance.txt"

print("=" * 60)
print("美股ETF轮动 - 每日分析")
print("=" * 60)

# 连接IBKR
client = IBKRClient(host='127.0.0.1', port=4002)
if not client.connect():
    print("无法连接IBKR")
    exit(1)

account_value = client.get_account_value()
print(f"\n账户净值: ${account_value:,.2f}")

# 获取数据并计算评分
print("\n正在计算最新评分...")
etf_codes = get_etf_codes()
all_hist = fetch_all_etfs(etf_codes, period="3mo")
bench_df = fetch_etf_data(BENCHMARK, period="3mo")

all_indicators = {}
for code, hist_df in all_hist.items():
    indicators = calc_all_indicators(hist_df, bench_df)
    all_indicators[code] = indicators

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

# 检查是否需要调仓
last_rebalance = None
if STATE_FILE.exists():
    last_rebalance = datetime.fromisoformat(STATE_FILE.read_text().strip())
    days_since = (datetime.now() - last_rebalance).days
    print(f"\n上次调仓: {last_rebalance.date()} ({days_since}天前)")
else:
    print("\n首次运行,将进行调仓")

should_rebalance = (last_rebalance is None or
                   (datetime.now() - last_rebalance).days >= REBALANCE_DAYS)

if should_rebalance:
    print("\n开始调仓...")
    target_weights = {symbol: 0.5 for symbol in top2.index}
    orders = client.rebalance(target_weights)

    print("\n交易完成:")
    for order in orders:
        print(f"  {order['action']} {order['quantity']} {order['symbol']} - {order['status']}")

    # 记录调仓时间
    STATE_FILE.write_text(datetime.now().isoformat())
    print(f"\n✓ 调仓完成,下次调仓时间: {(datetime.now() + timedelta(days=REBALANCE_DAYS)).date()}")
else:
    print(f"\n⏸ 距离下次调仓还有{REBALANCE_DAYS - days_since}天,暂不交易")

# 显示当前持仓
print("\n当前持仓:")
positions = client.get_positions()
if not positions.empty:
    print(positions.to_string())

client.disconnect()
print("\n" + "=" * 60)

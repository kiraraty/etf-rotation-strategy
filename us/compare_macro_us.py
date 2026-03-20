import sys
import os
import pandas as pd
import yfinance as yf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import DEFAULT_CONFIG
from engine.backtest import run_backtest
from engine.macro_regime import USMacroRegimeEngine
from data.etf_universe import get_etf_codes, get_etf_map

# 1. 抓取美股 ETF 数据
TICKERS = get_etf_codes()
print(f"正在抓取 {len(TICKERS)} 只美股 ETF 数据...")
all_hist = {}
for t in TICKERS + ["SPY"]:
    df = yf.download(t, period="3y", interval="1d", progress=False)
    if not df.empty:
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        all_hist[t] = df

# 2. 计算简单指标
print("计算基础技术指标...")
def calc_simple_mom(df):
    m5 = df['Close'].pct_change(5)
    m20 = df['Close'].pct_change(20)
    m60 = df['Close'].pct_change(60)
    # 模拟 RPS (相对SPY强度)
    return pd.DataFrame({"momentum_5d": m5, "momentum_20d": m20, "momentum_60d": m60, "rps": m20})

all_indicators = {t: calc_simple_mom(df) for t, df in all_hist.items() if t != "SPY"}

# 3. 启动宏观引擎
macro_engine = USMacroRegimeEngine()
macro_engine.fetch_data(days=1000)
macro_engine.calculate_regimes()

# 4. 构建评分历史
from engine.scorer import score_cross_section
all_dates = all_hist["SPY"].index[60:]
scores_macro = {}
scores_tech = {}

print("执行截面评分...")
for date in all_dates:
    cs = {}
    for t, ind in all_indicators.items():
        if date in ind.index: cs[t] = ind.loc[date]
    if not cs: continue
    cs_df = pd.DataFrame(cs).T
    scores_macro[date] = score_cross_section(cs_df, DEFAULT_CONFIG.weights, date=date, macro_engine=macro_engine)
    scores_tech[date] = score_cross_section(cs_df, DEFAULT_CONFIG.weights, date=date, macro_engine=None)

# 5. 回测 (Top 2, 10日调仓)
bt_macro = run_backtest(pd.DataFrame(scores_macro).T, all_hist, top_n=2, rebalance_days=10, fee_rate=0.0001, slippage=0.001)
bt_tech = run_backtest(pd.DataFrame(scores_tech).T, all_hist, top_n=2, rebalance_days=10, fee_rate=0.0001, slippage=0.001)

# 6. 输出结果
print("\n" + "="*50)
print(f"美股 ETF 轮动对比 (最近 2 年)")
print("="*50)
print(f"{'指标':<12} | {'纯技术面':<12} | {'技术+宏观修正':<12}")
print("-"*50)
print(f"{'累计收益':<12} | {bt_tech['cumulative_return']*100:>10.2f}% | {bt_macro['cumulative_return']*100:>13.2f}%")
print(f"{'夏普比率':<12} | {bt_tech['sharpe_ratio']:>11.2f} | {bt_macro['sharpe_ratio']:>14.2f}")
print(f"{'最大回撤':<12} | {bt_tech['max_drawdown']*100:>10.2f}% | {bt_macro['max_drawdown']*100:>13.2f}%")
print("="*50)

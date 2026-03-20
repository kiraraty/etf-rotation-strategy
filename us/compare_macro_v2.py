import sys
import os
import pandas as pd
import yfinance as yf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import DEFAULT_CONFIG
from engine.backtest import run_backtest
from engine.macro_regime import USMacroRegimeEngine
from data.etf_universe import get_etf_codes, get_etf_map
from engine.scorer import score_cross_section

# 1. 抓取数据
TICKERS = get_etf_codes()
all_hist = {}
print("同步美股数据中...")
for t in TICKERS + ["SPY"]:
    df = yf.download(t, period="4y", interval="1d", progress=False)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    all_hist[t] = df

# 2. 宏观引擎
macro_engine = USMacroRegimeEngine()
macro_engine.fetch_data(days=1200)
macro_engine.calculate_regimes()

# 3. 评分逻辑
all_indicators = {}
for t, df in all_hist.items():
    if t == "SPY": continue
    m20 = df['Close'].pct_change(20)
    all_indicators[t] = pd.DataFrame({"momentum_5d": df['Close'].pct_change(5), "momentum_20d": m20, "rps": m20})

all_dates = all_hist["SPY"].index[60:]
scores_pure = {}
exposure_series = pd.Series(index=all_dates, dtype=float)

for date in all_dates:
    cs = {t: ind.loc[date] for t, ind in all_indicators.items() if date in ind.index}
    if not cs: continue
    cs_df = pd.DataFrame(cs).T
    scores_pure[date] = score_cross_section(cs_df, DEFAULT_CONFIG.weights, date=date, macro_engine=None)
    exposure_series.loc[date] = macro_engine.get_exposure(date)

# 4. 回测对比
bt_pure = run_backtest(pd.DataFrame(scores_pure).T, all_hist, top_n=2, rebalance_days=10, exposure_map=None)
bt_advanced = run_backtest(pd.DataFrame(scores_pure).T, all_hist, top_n=2, rebalance_days=10, exposure_map=exposure_series)

# 5. 输出
print("\n" + "="*55)
print("美股进阶仓位控制对比 (2021-2025)")
print("="*55)
print(f"{'指标':<12} | {'纯技术面(100%)':<16} | {'技术+宏观仓位控':<16}")
print("-"*55)
print(f"{'累计收益':<12} | {bt_pure['cumulative_return']*100:>14.2f}% | {bt_advanced['cumulative_return']*100:>17.2f}%")
print(f"{'夏普比率':<12} | {bt_pure['sharpe_ratio']:>15.2f} | {bt_advanced['sharpe_ratio']:>18.2f}")
print(f"{'最大回撤':<12} | {bt_pure['max_drawdown']*100:>14.2f}% | {bt_advanced['max_drawdown']*100:>17.2f}%")
print("="*55)

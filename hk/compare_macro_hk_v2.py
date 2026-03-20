import sys
import os
import pandas as pd
import yfinance as yf
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ETF_POOL = {
    "3033.HK": "科技",
    "2800.HK": "大盘",
    "3110.HK": "红利",
    "2828.HK": "大盘",
    "3067.HK": "科技",
    "3069.HK": "医疗",
    "3097.HK": "能源",
    "3008.HK": "公用事业",
}

def run_hk_test():
    print("同步港股数据...")
    all_hist = {}
    for t in ETF_POOL.keys():
        df = yf.download(t, period="3y", interval="1d", progress=False)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        all_hist[t] = df

    from hk.engine.macro_regime import HKMacroRegimeEngine
    macro_engine = HKMacroRegimeEngine()
    macro_engine.fetch_data(days=1000)
    macro_engine.calculate_regimes()

    all_dates = all_hist["2800.HK"].index[60:]
    scores_tech = {}
    scores_macro = {}
    exposure_series = pd.Series(index=all_dates, dtype=float)

    for date in all_dates:
        cs_scores = {}
        for t, df in all_hist.items():
            if date in df.index:
                idx = df.index.get_loc(date)
                if idx >= 20:
                    mom = df.iloc[idx]['Close'] / df.iloc[idx-20]['Close'] - 1
                    cs_scores[t] = mom
        if not cs_scores: continue
        scores_tech[date] = pd.Series(cs_scores)
        macro_cs = {}
        for t, s in cs_scores.items():
            mult = macro_engine.get_multiplier(date, ETF_POOL[t])
            macro_cs[t] = s * mult
        scores_macro[date] = pd.Series(macro_cs)
        exposure_series.loc[date] = macro_engine.get_exposure(date)

    from us.engine.backtest import run_backtest
    bt_tech = run_backtest(pd.DataFrame(scores_tech).T, all_hist, top_n=2, rebalance_days=10)
    bt_macro = run_backtest(pd.DataFrame(scores_macro).T, all_hist, top_n=2, rebalance_days=10, exposure_map=exposure_series)

    print("\n" + "="*55)
    print("港股 ETF 轮动：灵敏冒险版对比 (2023-2025)")
    print("="*55)
    print(f"{'指标':<12} | {'纯技术面(100%)':<16} | {'灵敏宏观+阶梯仓位':<16}")
    print("-"*55)
    print(f"{'累计收益':<12} | {bt_tech['cumulative_return']*100:>14.2f}% | {bt_macro['cumulative_return']*100:>17.2f}%")
    print(f"{'夏普比率':<12} | {bt_tech['sharpe_ratio']:>15.2f} | {bt_macro['sharpe_ratio']:>18.2f}")
    print(f"{'最大回撤':<12} | {bt_tech['max_drawdown']*100:>14.2f}% | {bt_macro['max_drawdown']*100:>17.2f}%")
    print("="*55)

if __name__ == "__main__":
    run_hk_test()

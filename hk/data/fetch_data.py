"""港股ETF数据获取"""
import yfinance as yf
import pandas as pd
from pathlib import Path

def fetch_etf_data(code: str, period: str = "8y") -> pd.DataFrame:
    """获取单个ETF历史数据"""
    ticker = yf.Ticker(code)
    df = ticker.history(period=period)
    df.index = pd.to_datetime(df.index)
    df.columns = [c.lower() for c in df.columns]
    return df[['open', 'high', 'low', 'close', 'volume']]

def fetch_all_etfs(etf_codes: list, cache_dir: str = ".cache"):
    """批量获取并缓存ETF数据"""
    Path(cache_dir).mkdir(exist_ok=True)

    for code in etf_codes:
        try:
            df = fetch_etf_data(code)
            safe_code = code.replace(".", "_")
            df.to_csv(f"{cache_dir}/etf_hist_{safe_code}.csv")
            print(f"✓ {code}: {len(df)} days")
        except Exception as e:
            print(f"✗ {code}: {e}")

if __name__ == "__main__":
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from etf_universe import get_etf_codes
    fetch_all_etfs(get_etf_codes())

"""yfinance数据获取"""
import yfinance as yf
import pandas as pd

def fetch_etf_data(symbol: str, period: str = "1y") -> pd.DataFrame:
    """获取ETF历史数据"""
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period)
        if df.empty:
            return pd.DataFrame()
        
        df = df.rename(columns={
            'Close': 'close',
            'Volume': 'volume',
            'Open': 'open',
            'High': 'high',
            'Low': 'low'
        })
        df['amount'] = df['close'] * df['volume']
        return df[['open', 'high', 'low', 'close', 'volume', 'amount']]
    except:
        return pd.DataFrame()

def fetch_all_etfs(symbols: list, period: str = "1y") -> dict:
    """批量获取ETF数据"""
    result = {}
    for symbol in symbols:
        df = fetch_etf_data(symbol, period)
        if not df.empty:
            result[symbol] = df
    return result

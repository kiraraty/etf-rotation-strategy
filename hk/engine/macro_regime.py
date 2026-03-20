import pandas as pd
import numpy as np
import yfinance as yf

class HKMacroRegimeEngine:
    """港股宏观引擎：汇率定生死，利率定风格"""
    
    def __init__(self, window=20):
        self.window = window
        self.data = None
        self.regimes = None

    def fetch_data(self, days=1000):
        """抓取核心指标：离岸人民币、美债收益率"""
        print(f"正在抓取港股宏观指标 (CNH=X:汇率, ^TNX:美债) 过去 {days} 天...")
        try:
            # CNH=X 是离岸人民币汇率
            # ^TNX 是美债收益率
            macro_tickers = ["CNH=X", "^TNX"]
            df = yf.download(macro_tickers, period=f"{int(days*1.5)}d", interval="1d")['Close']
            df = df.rename(columns={"CNH=X": "usdcnh", "^TNX": "us10y"})
            
            self.data = df.sort_index().ffill().tail(days)
            return self.data
        except Exception as e:
            print(f"港股宏观数据抓取失败: {e}")
            return None

    def calculate_regimes(self):
        """
        冒险版判定逻辑：看斜率而非均线
        """
        if self.data is None: return
        
        df = self.data.copy()
        # 计算汇率 5 日变动率 (斜率)
        df['fx_slope'] = df['usdcnh'].pct_change(5)
        # 计算利率趋势
        df['rate_ma'] = df['us10y'].rolling(10).mean() # 改为更灵敏的 10 日线
        
        # 判定 (偏移1天)
        # 人民币加速贬值风险 (5天贬值超过 0.5%)
        df['currency_crash'] = df['fx_slope'] > 0.005 
        df['liquidity_on'] = df['us10y'] < df['rate_ma']
        
        self.regimes = df[['currency_crash', 'liquidity_on']].shift(1)
        return self.regimes

    def get_exposure(self, date):
        """阶梯仓位：加速贬值 30%，小幅波动 80%，升值 100%"""
        if self.regimes is None or date not in self.regimes.index:
            return 1.0
        r = self.regimes.loc[date]
        
        if r['currency_crash']:
            return 0.3 # 只有崩盘式贬值才逃跑
        return 0.8 # 其他时间至少保持 80% 仓位，防止踏空 924 这种行情

    def get_multiplier(self, date, etf_sector, mult=1.6):
        # 提高乘数到 1.6，进一步放大弹性板块
        if self.regimes is None or date not in self.regimes.index:
            return 1.0
        r = self.regimes.loc[date]
        growth = ['科技', '互联网', '半导体', '医疗']
        value = ['红利', '银行', '能源']
        
        if r['liquidity_on']:
            for s in growth:
                if s in etf_sector: return mult
        else:
            for s in value:
                if s in etf_sector: return mult
        return 1.0

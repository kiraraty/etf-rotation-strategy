import pandas as pd
import numpy as np
import yfinance as yf
import os

class USMacroRegimeEngine:
    """美股宏观环境判定引擎 (基于 US10Y 和 DXY)"""
    
    def __init__(self, window=20):
        self.window = window
        self.data = None
        self.regimes = None

    def fetch_data(self, days=1000):
        """抓取美股核心宏观指标"""
        print(f"正在抓取美股宏观指标 (TNX:美债, DX-Y.NYB:美元指数) 过去 {days} 天...")
        try:
            # ^TNX 是 10年期美债收益率的代号 (10倍基数)
            # DX-Y.NYB 是美元指数
            macro_tickers = ["^TNX", "DX-Y.NYB", "GLD"]
            df = yf.download(macro_tickers, period=f"{int(days*1.5)}d", interval="1d")['Close']
            df = df.rename(columns={"^TNX": "us10y", "DX-Y.NYB": "dxy", "GLD": "gold"})
            
            self.data = df.sort_index().ffill().tail(days)
            return self.data
        except Exception as e:
            print(f"美股宏观数据抓取失败: {e}")
            return None

    def calculate_regimes(self):
        """
        计算宏观因子趋势 (非前瞻)
        """
        if self.data is None: return
        
        df = self.data.copy()
        df['us10y_ma'] = df['us10y'].rolling(self.window).mean()
        df['dxy_ma'] = df['dxy'].rolling(self.window).mean()
        
        # 核心判定 (偏移1天)
        # 1. 利率风险: 收益率高于均线
        df['rate_risk'] = df['us10y'] > df['us10y_ma']
        # 2. 汇率风险: 美元指数高于均线 (收割全球流动性)
        df['dxy_risk'] = df['dxy'] > df['dxy_ma']
        
        self.regimes = df[['rate_risk', 'dxy_risk']].shift(1)
        return self.regimes

    def get_exposure(self, date):
        """根据日期返回建议的总仓位比例 (0.0 ~ 1.0)"""
        if self.regimes is None or date not in self.regimes.index:
            return 1.0
            
        r = self.regimes.loc[date]
        rate_risk = r['rate_risk']
        dxy_risk = r['dxy_risk']
        
        # 仓位阶梯:
        # 双风险: 40% (极度保守)
        if rate_risk and dxy_risk:
            return 0.4
        # 单风险: 70% (中性守备)
        if rate_risk or dxy_risk:
            return 0.7
        # 双利好: 100% (全速进攻)
        return 1.0

    def get_multiplier(self, date, etf_sector, mult=1.3):
        """保留板块乘数逻辑，作为二级过滤"""
        if self.regimes is None or date not in self.regimes.index:
            return 1.0
        # 这里可以保持简单返回 1.0，因为 V2 版本主要考量 get_exposure
        return 1.0

import pandas as pd
import numpy as np
import akshare as ak
import os
import time

class MacroRegimeEngine:
    """宏观环境判定引擎 (双因子版: 美债利率 + 人民币汇率)"""
    
    def __init__(self, window=20):
        self.window = window
        self.data = None
        self.regimes = None

    def fetch_data(self, days=500, benchmark_df=None):
        """抓取宏观指标: 利率 (akshare) + 价格基准 (外部传入)"""
        print(f"正在抓取宏观指标 (利率) 过去 {days} 天...")
        try:
            # 1. 美债 10Y (唯一依赖的外部宏观接口)
            df_bond = ak.bond_zh_us_rate(start_date="20200101")
            df_bond = df_bond.rename(columns={"日期": "date", "美国国债收益率10年": "us10y"})
            df_bond['date'] = pd.to_datetime(df_bond['date'])
            df_bond = df_bond.set_index('date')[['us10y']]
            
            self.data = df_bond.sort_index().ffill().tail(days)
            
            # 2. 如果传入了基准行情(如沪深300), 则合并它作为资本流向因子
            if benchmark_df is not None:
                bench_close = benchmark_df[['close']].rename(columns={'close': 'bench_price'})
                self.data = pd.concat([self.data, bench_close], axis=1).ffill().dropna()
                
            return self.data
        except Exception as e:
            print(f"宏观数据抓取失败: {e}")
            return None

    def calculate_regimes(self):
        """
        核心判定逻辑:
        - LIQUIDITY_ON: US10Y < MA20 (利率下行 -> 利好成长)
        - CAPITAL_ON: Bench_Price > MA20 (价格上行 -> 利好权重)
        """
        if self.data is None: return
        
        df = self.data.copy()
        df['us10y_ma'] = df['us10y'].rolling(self.window).mean()
        
        # 判定标签
        df['liquidity_on'] = df['us10y'] < df['us10y_ma']
        
        if 'bench_price' in df.columns:
            df['bench_ma'] = df['bench_price'].rolling(self.window).mean()
            df['capital_on'] = df['bench_price'] > df['bench_ma']
        else:
            df['capital_on'] = True # 缺省默认
        
        # 存储结果 (偏移1天)
        self.regimes = df[['liquidity_on', 'capital_on']].shift(1)
        return self.regimes

    def get_multiplier(self, date, etf_sector):
        """根据日期、板块以及利率/汇率双因子返回乘数"""
        if self.regimes is None or date not in self.regimes.index:
            return 1.0
            
        r = self.regimes.loc[date]
        liq_on = r['liquidity_on']
        cap_on = r['capital_on']
        
        # 定义板块分类
        # 1. 成长类 (对利率极度敏感)
        growth = ['科技', '芯片', '半导体', '恒生科技', '新能源', '光伏', '计算机', '科创50']
        # 2. 蓝筹权重类 (对外资/汇率极度敏感)
        bluechip = ['大盘', '沪深300', '消费', '酒', '证券', '基准']
        # 3. 防御类 (避风港)
        defensive = ['红利', '银行', '公用事业', '煤炭', '石油']
        
        # 逻辑判定
        # A. 利率下行 -> 成长加分
        if liq_on:
            for s in growth:
                if s in etf_sector: return 1.4 # 成长起飞
        else:
            for s in growth:
                if s in etf_sector: return 0.6 # 成长压制
                
        # B. 汇率升值 -> 蓝筹加分
        if cap_on:
            for s in bluechip:
                if s in etf_sector: return 1.3 # 权重吸金
        else:
            for s in bluechip:
                if s in etf_sector: return 0.7 # 权重失血
                
        # C. 极端防御情况: 利率升 + 汇率贬 -> 只有红利抗跌
        if not liq_on and not cap_on:
            for s in defensive:
                if s in etf_sector: return 1.5
            return 0.5 # 其他全部大幅压低
                
        return 1.0

if __name__ == "__main__":
    engine = MacroRegimeEngine()
    engine.fetch_data()
    engine.calculate_regimes()
    print("最新宏观环境判定:", engine.regimes.iloc[-1])

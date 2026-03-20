import sys
import os
import pandas as pd
import numpy as np
import optuna
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import DEFAULT_CONFIG
from engine.signals import run_analysis
from engine.backtest import run_backtest

optuna.logging.set_verbosity(optuna.logging.WARNING)

print("正在获取数据...")
BACKTEST_DAYS = 650
base_result = run_analysis(period="daily", days=BACKTEST_DAYS, config=DEFAULT_CONFIG)
all_hist = base_result["all_hist"]
all_indicators = base_result["all_indicators"]

def objective(trial):
    top_n = trial.suggest_int("top_n", 2, 4)
    rebalance_days = trial.suggest_int("rebalance_days", 3, 15)
    macro_mult = trial.suggest_float("macro_multiplier", 1.1, 1.6)
    
    from engine.signals import _build_score_history
    macro_engine = base_result["macro_engine"]
    
    # 临时覆盖 get_multiplier 逻辑以支持动态 multiplier
    original_get_multiplier = macro_engine.get_multiplier
    def temp_multiplier(date, etf_sector):
        if macro_engine.regimes is None or date not in macro_engine.regimes.index:
            return 1.0
        r = macro_engine.regimes.loc[date]
        growth = ['科技', '芯片', '半导体', '恒生科技', '新能源', '光伏', '计算机', '科创50']
        bluechip = ['大盘', '沪深300', '消费', '酒', '证券', '基准']
        defensive = ['红利', '银行', '公用事业', '煤炭', '石油']
        
        if r['liquidity_on']:
            for s in growth:
                if s in etf_sector: return macro_mult
        if r['capital_on']:
            for s in bluechip:
                if s in etf_sector: return macro_mult
        if not r['liquidity_on'] and not r['capital_on']:
            for s in defensive:
                if s in etf_sector: return macro_mult
        return 1.0
    
    macro_engine.get_multiplier = temp_multiplier
    
    score_history = _build_score_history(all_indicators, DEFAULT_CONFIG, macro_engine=macro_engine)
    
    bt = run_backtest(score_history, all_hist, 
                      top_n=top_n, 
                      rebalance_days=rebalance_days, 
                      fee_rate=0.00005, 
                      slippage=0.0005)
    
    ret = bt['cumulative_return']
    mdd = abs(bt['max_drawdown'])
    sharpe = bt['sharpe_ratio']
    
    if mdd < 0.05: mdd = 0.05
    # 我们以 夏普 * (收益/回撤) 为优化目标
    return (ret / mdd) * max(0, sharpe)

# 运行优化
study = optuna.create_study(direction="maximize")
print("开始 Optuna 搜索 (50次 Trial)...")
study.optimize(objective, n_trials=50)

print("\n" + "="*50)
print("最优参数组合:")
print(study.best_params)
print(f"最优得分: {study.best_value:.4f}")
print("="*50)

# 计算最终结果
best = study.best_params
macro_engine = base_result["macro_engine"]
# 再次覆盖为最优乘数
def final_multiplier(date, etf_sector):
    if macro_engine.regimes is None or date not in macro_engine.regimes.index:
        return 1.0
    r = macro_engine.regimes.loc[date]
    mult = best["macro_multiplier"]
    growth = ['科技', '芯片', '半导体', '恒生科技', '新能源', '光伏', '计算机', '科创50']
    bluechip = ['大盘', '沪深300', '消费', '酒', '证券', '基准']
    defensive = ['红利', '银行', '公用事业', '煤炭', '石油']
    if r['liquidity_on']:
        for s in growth:
            if s in etf_sector: return mult
    if r['capital_on']:
        for s in bluechip:
            if s in etf_sector: return mult
    if not r['liquidity_on'] and not r['capital_on']:
        for s in defensive:
            if s in etf_sector: return mult
    return 1.0

macro_engine.get_multiplier = final_multiplier
from engine.signals import _build_score_history
score_history = _build_score_history(all_indicators, DEFAULT_CONFIG, macro_engine=macro_engine)
bt = run_backtest(score_history, all_hist, top_n=best["top_n"], rebalance_days=best["rebalance_days"], fee_rate=0.00005, slippage=0.0005)

print(f"\n最优配置下 2 年累计收益: {bt['cumulative_return']*100:.2f}%")
print(f"最大回撤: {bt['max_drawdown']*100:.2f}%")
print(f"夏普比率: {bt['sharpe_ratio']:.2f}")
print(f"年化换手率(模拟): {60/best['rebalance_days']*100:.1f}%")

# Global ETF Rotation Strategy

全球市场 ETF 动量轮动策略，支持 A股、美股、港股三大市场。

## 策略概览

使用横截面动量（价格强弱）评分，持有近期涨幅最强的 ETF，定期轮动。

核心假设：动量效应——涨的继续涨。通过在不同市场、不同板块间轮动，分散风险、捕捉趋势。

## 三市场对比

| 市场 | 策略 | 年化 | 夏普 | 最大回撤 | 说明 |
|------|------|------|------|---------|------|
| **A股 ETF** | Top5 10天轮动 + 宏观叠加 | ~20% | 0.79 | -22% | 宏观信号（美10Y + 沪深300）价值巨大 |
| **港股 ETF** | Top5 动量轮动 | ~40-50% | ~0.7 | -30% | 纯动量效果好，波动大 |
| **美股 ETF** | Top5 轮动 | ~8% | 0.67 | -11% | 板块 alpha 有限，跑不赢 SPY |
| **美股个股** | voltarget（见 us-stock repo） | 29.9% | 1.47 | -26.3% | 个股 alpha 远强于板块 ETF |

**结论**：美股策略应选个股轮动（us-stock repo），ETF 板块轮动在美国市场效果有限。

---

## A股策略（cn/）

### 策略：ETF 板块轮动 + 宏观叠加

使用 21 只主流行业 ETF，根据价格动量和宏观 regime 综合评分。

**核心逻辑**：
- 20 日价格动量（趋势强度）
- 宏观 regime 过滤（美10Y × 沪深300 趋势）
- 宏观信号把年化从 -41% 翻转到 +48%

**参数**：
- Top N = 5
- 调仓周期 = 10 天
- 等权配置

**回测结果（15年 2010-2025）**：
- 年化 ~20%
- 夏普 ~0.8
- 最大回撤 -22%

### 关键发现

1. **宏观叠加价值最大**：美10Y 与沪深300 趋势叠加，显著提升表现
2. **反转因子无效**：在 A股趋势行情中，价值/反转策略亏损
3. **参数空间平坦**：网格搜索验证 Top5 10天为最优，无需进一步优化
4. **融资杠杆信号**：6年数据验证无效，实盘不启用

**文件**：
- `cn/engine/signals.py` — 评分引擎
- `cn/engine/backtest.py` — 回测引擎（含涨跌停模拟）
- `cn/engine/macro_regime.py` — 宏观 regime 计算
- `cn/optimize_astock.py` — 参数优化
- `cn/paper_trading/` — 模拟盘入口

---

## 港股策略（hk/）

### 策略：纯动量轮动

港股 ETF 市场弹性大，20 日纯动量效果显著。

**回测结果（5年）**：
- Top5 动量：年化 53.6%（含 924 行情放大）
- 防守版（MA60 择时）：年化 ~120%
- 最大回撤 -30%

**关键发现**：
- 港股 ETF 动量效应比 A股更强
- 924 行情（2024年9月）是极端特例，真实预期应打折
- 宏观 regime 叠加仍有价值

**文件**：
- `hk/engine/signals.py` — 评分引擎
- `hk/engine/backtest.py` — 回测引擎
- `hk/engine/macro_regime.py` — 宏观 regime
- `hk/optimize_advanced.py` — 参数优化

---

## 美股 ETF 策略（us/）

### 策略：板块动量轮动

使用主要板块 ETF（XLK/XLF/XLE 等），周频调仓。

**回测结果**：
- 年化 ~8%，夏普 0.67
- 最大回撤 -11%
- **结论：跑不赢 SPY 买入持有，板块轮动 alpha 有限**

**关键发现**：
- 美股市场更有效，板块轮动超额收益少
- 个股 alpha 远强于板块 ETF（见 us-stock repo）
- 美股策略应选择个股轮动而非 ETF 轮动

---

## 目录结构

```
etf-rotation-strategy/
├── cn/                         # A股 ETF 策略
│   ├── data/
│   │   ├── cache.py            # 数据缓存
│   │   ├── etf_universe.py     # ETF 池定义
│   │   └── fetcher.py          # akshare 数据获取
│   ├── engine/
│   │   ├── backtest.py         # 回测引擎（涨跌停模拟）
│   │   ├── indicators.py       # 技术指标
│   │   ├── macro_regime.py     # 宏观 regime
│   │   ├── scorer.py           # 评分计算
│   │   └── signals.py          # 信号生成
│   ├── optimize_astock.py      # Optuna 参数优化
│   ├── run_backtest.py         # 回测入口
│   └── paper_trading/          # 模拟盘
│       ├── daily_runner.py     # 每日运行
│       └── paper_scorer.py     # 评分脚本
├── hk/                         # 港股 ETF 策略
│   ├── data/
│   ├── engine/
│   ├── broker/
│   └── optimize_advanced.py
├── us/                         # 美股 ETF 策略
│   ├── data/
│   ├── engine/
│   ├── broker/
│   └── run_backtest.py
└── docs/                       # 研究文档
```

---

## 快速开始

### A股 ETF 策略

```bash
cd cn

# 1. 运行回测
python run_backtest.py

# 2. 参数优化（可选，默认 Top5 10天 已验证最优）
python optimize_astock.py

# 3. 模拟盘
python -m cn.paper_trading.daily_runner
```

### 港股 ETF 策略

```bash
cd hk
python run_5y_backtest.py
python optimize_advanced.py
```

### 美股 ETF 策略

```bash
cd us
python run_backtest.py
```

---

## 数据说明

| 市场 | 数据源 | 频率 |
|------|--------|------|
| A股 | akshare（Tushare 底层） | 日线 |
| 港股 | akshare（Yahoo Finance 底层） | 日线 |
| 美股 | yfinance | 日线 |

---

## 费率基准（IBKR）

| 市场 | fee_rate | slippage | 说明 |
|------|----------|----------|------|
| A股（国内券商） | 0.00005 | 0 | 免印花税 |
| 港股 ETF | 0.0006 | 0.0005 | 佣金 5bps + 交易所 1bps，ETF 免印花税 |
| 美股 ETF/个股 | 0.0003 | 0.0005 | 佣金 $0.0035/股 + 交易所费 |

---

## 关键教训

1. **大道至简**：技术指标堆砌、Optuna 过度优化、机器学习因子——都不如最简单的价格动量
2. **宏观信号价值大**：A股/港股市场，宏观 regime 叠加显著提升表现
3. **美股选个股不选 ETF**：美股个股 alpha 远强于板块 ETF 轮动
4. **参数空间平坦**：大量实验证明，Top5 10天是最优参数附近，无需过度优化
5. **避免过度复杂**：融资信号、资金流、情绪因子——经回测验证均无效

---

## 相关项目

- **[us-stock](https://github.com/kiraraty/us-stock-momentum)** — 美股个股动量策略（voltarget，推荐美股实盘）
- **A股个股轮动** — 在 `cn/stock_rotation/`，基于 Tushare 59 只龙头股

---

## 免责声明

本项目仅供研究学习，不构成投资建议。历史回测结果不代表未来表现。

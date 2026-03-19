# ETF Rotation Strategy

基于动量的ETF板块轮动策略，支持A股和美股市场。

## 策略概述

使用20日动量指标对ETF池进行评分，选择Top N个ETF等权持仓，定期调仓。

## 回测结果

### A股策略 (cn/)
- **ETF池**: 21个主流板块ETF
- **参数**: Top5, 每天调仓
- **测试期**: 2024-2026 (约2年)
- **年化收益**: 58.5%
- **夏普比率**: 1.21
- **最大回撤**: -23.34%

### 美股策略 (us/)
- **ETF池**: 21个板块ETF (覆盖11个行业)
- **参数**: Top5, 5天调仓
- **测试期**: 约2年
- **年化收益**: 26.3%
- **夏普比率**: 1.66
- **最大回撤**: -12.79%

## 目录结构

```
etf-rotation-strategy/
├── cn/                    # A股策略
│   ├── data/             # 数据获取和ETF池定义
│   ├── engine/           # 回测引擎
│   ├── optimize_astock.py # 参数优化
│   └── ...
├── us/                    # 美股策略
│   ├── data/             # 数据获取和ETF池定义
│   ├── engine/           # 回测引擎
│   ├── broker/           # IBKR交易接口
│   ├── optimize.py       # 参数优化
│   └── run_live_scheduled.py # 实盘交易
└── README.md
```

## 使用方法

### 参数优化

**A股:**
```bash
cd cn
python optimize_astock.py
```

**美股:**
```bash
cd us
python optimize.py
```

### 实盘交易 (美股)

```bash
cd us
python run_live_scheduled.py
```

## 关键特性

- ✅ 严格避免未来函数
- ✅ 准确的手续费计算 (万0.5)
- ✅ Optuna参数优化
- ✅ 支持IBKR实盘交易
- ✅ 训练集/测试集分离验证

## 依赖

- Python 3.8+
- pandas, numpy
- optuna
- akshare (A股数据)
- yfinance (美股数据)
- ib_insync (IBKR交易)

## 免责声明

本项目仅供学习研究使用，不构成投资建议。历史回测结果不代表未来表现。

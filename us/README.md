# 美股ETF板块轮动策略

基于20日动量的美股板块ETF轮动策略，支持回测和IBKR实盘交易。

## 策略表现

**回测期**: 约2年 (2024-2026)
- **年化收益**: 26.3%
- **夏普比率**: 1.66
- **最大回撤**: -12.79%
- **胜率**: 62.5%

**最优参数**: Top5持仓，5天调仓

## ETF池 (21个)

覆盖11个主要行业板块：
- 科技: QQQ, XLK, SOXX
- 金融: XLF, KRE
- 能源: XLE, XOP
- 医疗: XLV, IBB
- 消费: XLY, XLP, XRT
- 工业: XLI, IYT
- 材料: XLB, GDX
- 房地产: XLRE
- 公用事业: XLU
- 通信: XLC
- 避险: GLD

## 目录结构

```
us/
├── data/
│   ├── etf_universe.py    # ETF池定义
│   └── fetch_data.py      # yfinance数据获取
├── engine/
│   └── backtest.py        # 回测引擎
├── broker/
│   └── ibkr_trader.py     # IBKR交易接口
├── optimize.py            # Optuna参数优化
└── run_live_scheduled.py  # 实盘定时交易
```

## 使用方法

### 1. 安装依赖
```bash
pip install pandas numpy yfinance optuna ib_insync
```

### 2. 参数优化
```bash
python optimize.py
```

### 3. 实盘交易

配置IBKR连接后运行：
```bash
python run_live_scheduled.py
```

## 策略逻辑

1. 每日计算所有ETF的20日动量评分
2. 选择评分最高的Top N个ETF等权持仓
3. 每隔N天根据最新评分调仓
4. 手续费: 单边0.005% (IBKR标准费率)

## 风险提示

- 历史回测不代表未来表现
- 动量策略在震荡市可能表现不佳
- 需要严格的风险管理和止损机制

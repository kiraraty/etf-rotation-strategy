# IBKR实盘交易设置指南

## 1. 安装依赖

```bash
pip install ib_insync
```

## 2. 下载并启动TWS或IB Gateway

- TWS (Trader Workstation): 完整交易平台
- IB Gateway: 轻量级API网关（推荐）

下载地址: https://www.interactivebrokers.com/en/trading/tws.php

## 3. 配置API权限

1. 启动TWS/Gateway
2. 进入 File → Global Configuration → API → Settings
3. 勾选 "Enable ActiveX and Socket Clients"
4. 添加信任的IP: 127.0.0.1
5. 端口设置:
   - TWS模拟盘: 7497
   - TWS实盘: 7496
   - Gateway模拟盘: 4002
   - Gateway实盘: 4001

## 4. 运行实盘交易

```bash
python run_live.py
```

## 5. 注意事项

- 先用模拟盘测试（端口7497或4002）
- 确认策略稳定后再用实盘
- 建议每5天运行一次（周一开盘前）
- 可以用cron定时执行

## 6. 定时任务示例

```bash
# 每周一早上9点执行
0 9 * * 1 cd /path/to/us-etf-rotation && python run_live.py
```

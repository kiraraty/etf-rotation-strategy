"""独立回测脚本：快速验证策略效果"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import DEFAULT_CONFIG
from engine.signals import run_analysis
from engine.backtest import run_backtest

print("=" * 60)
print("ETF轮动策略回测")
print("=" * 60)

# 运行分析
print("\n正在获取数据...")
result = run_analysis(period="daily", days=1250, config=DEFAULT_CONFIG)

if not result or result["score_history"].empty:
    print("❌ 数据不足，无法回测")
    sys.exit(1)

print(f"✓ 数据获取完成，共{len(result['score_history'])}个交易日")

# 运行回测
print("\n正在回测...")
bt_result = run_backtest(
    result["score_history"],
    result["all_hist"],
    top_n=3,
    rebalance_days=5,
    fee_rate=0.001
)

# 输出结果
print("\n" + "=" * 60)
print("回测结果")
print("=" * 60)
print(f"累计收益率: {bt_result['cumulative_return']*100:.2f}%")
print(f"夏普比率:   {bt_result['sharpe_ratio']:.2f}")
print(f"最大回撤:   {bt_result['max_drawdown']*100:.2f}%")
print(f"胜率:       {bt_result['win_rate']*100:.1f}%")
print("\n策略说明: 每5天调仓，持有评分Top3的ETF，等权配置")
print("=" * 60)

"""IBKR交易接口"""
from ib_insync import IB, Stock, MarketOrder, util
import pandas as pd

class IBKRClient:
    def __init__(self, host='127.0.0.1', port=7497, client_id=1):
        """初始化IBKR客户端
        
        Args:
            host: TWS/IB Gateway地址
            port: 7497(TWS Paper), 7496(TWS Live), 4002(Gateway Paper), 4001(Gateway Live)
            client_id: 客户端ID
        """
        self.ib = IB()
        self.host = host
        self.port = port
        self.client_id = client_id
        
    def connect(self):
        """连接IBKR"""
        try:
            self.ib.connect(self.host, self.port, clientId=self.client_id)
            print(f"✓ 已连接到IBKR: {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"✗ 连接失败: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        self.ib.disconnect()
        
    def get_account_value(self):
        """获取账户净值"""
        account_values = self.ib.accountValues()
        for v in account_values:
            if v.tag == 'NetLiquidation' and v.currency == 'USD':
                return float(v.value)
        return 0
    
    def get_positions(self):
        """获取当前持仓"""
        positions = self.ib.positions()
        result = []
        for pos in positions:
            result.append({
                'symbol': pos.contract.symbol,
                'quantity': pos.position,
                'avg_cost': pos.avgCost,
            })
        return pd.DataFrame(result)
    
    def place_order(self, symbol: str, quantity: int, action: str = 'BUY'):
        """下单
        
        Args:
            symbol: 股票代码
            quantity: 数量
            action: BUY/SELL
        """
        contract = Stock(symbol, 'SMART', 'USD')
        order = MarketOrder(action, quantity)
        
        trade = self.ib.placeOrder(contract, order)
        self.ib.sleep(1)  # 等待订单确认
        
        return {
            'symbol': symbol,
            'action': action,
            'quantity': quantity,
            'status': trade.orderStatus.status
        }
    
    def rebalance(self, target_weights: dict, use_yfinance=True):
        """调仓到目标权重

        Args:
            target_weights: {symbol: weight} 目标权重字典
            use_yfinance: 是否用yfinance获取价格(避免IBKR市场数据订阅问题)
        """
        account_value = self.get_account_value()
        current_positions = self.get_positions()

        orders = []
        for symbol, weight in target_weights.items():
            target_value = account_value * weight

            # 获取当前价格
            if use_yfinance:
                import yfinance as yf
                ticker = yf.Ticker(symbol)
                price = ticker.info.get('regularMarketPrice') or ticker.info.get('currentPrice')
            else:
                contract = Stock(symbol, 'SMART', 'USD')
                self.ib.qualifyContracts(contract)
                ticker = self.ib.reqMktData(contract)
                self.ib.sleep(2)
                price = ticker.marketPrice()

            if price and price > 0:
                target_qty = int(target_value / price)

                # 获取当前持仓
                current_qty = 0
                if not current_positions.empty:
                    pos = current_positions[current_positions['symbol'] == symbol]
                    if not pos.empty:
                        current_qty = int(pos.iloc[0]['quantity'])

                # 计算需要交易的数量
                delta = target_qty - current_qty
                if abs(delta) > 0:
                    action = 'BUY' if delta > 0 else 'SELL'
                    print(f"  计划{action} {abs(delta)}股 {symbol} @ ${price:.2f} (目标${target_value:,.0f})")
                    result = self.place_order(symbol, abs(delta), action)
                    orders.append(result)
                else:
                    print(f"  {symbol}: 无需调仓 (当前{current_qty}股)")

        return orders

"""美股板块ETF池定义"""

ETF_UNIVERSE = {
    # 科技
    "QQQ": {"name": "纳斯达克100", "sector": "科技"},
    "XLK": {"name": "科技板块", "sector": "科技"},
    "SOXX": {"name": "半导体", "sector": "科技"},
    
    # 金融
    "XLF": {"name": "金融板块", "sector": "金融"},
    "KRE": {"name": "区域银行", "sector": "金融"},
    
    # 能源
    "XLE": {"name": "能源板块", "sector": "能源"},
    "XOP": {"name": "石油天然气", "sector": "能源"},
    
    # 医疗
    "XLV": {"name": "医疗保健", "sector": "医疗"},
    "IBB": {"name": "生物科技", "sector": "医疗"},
    
    # 消费
    "XLY": {"name": "可选消费", "sector": "消费"},
    "XLP": {"name": "必需消费", "sector": "消费"},
    "XRT": {"name": "零售", "sector": "消费"},
    
    # 工业
    "XLI": {"name": "工业板块", "sector": "工业"},
    "IYT": {"name": "运输", "sector": "工业"},
    
    # 材料
    "XLB": {"name": "材料板块", "sector": "材料"},
    "GDX": {"name": "黄金矿业", "sector": "材料"},
    
    # 房地产
    "XLRE": {"name": "房地产", "sector": "房地产"},
    
    # 公用事业
    "XLU": {"name": "公用事业", "sector": "公用事业"},
    
    # 通信
    "XLC": {"name": "通信服务", "sector": "通信"},
    
    # 防御性
    "GLD": {"name": "黄金", "sector": "避险"},
}

BENCHMARK = "SPY"  # 标普500

def get_etf_codes():
    return list(ETF_UNIVERSE.keys())

def get_etf_map():
    return ETF_UNIVERSE

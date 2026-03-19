"""港股ETF池定义"""

ETF_UNIVERSE = {
    # 指数
    "2800.HK": {"name": "盈富基金", "sector": "大盘"},  # 恒生指数ETF
    "2828.HK": {"name": "恒生H股", "sector": "大盘"},

    # 科技
    "3033.HK": {"name": "恒生科技", "sector": "科技"},
    "3032.HK": {"name": "恒生互联网", "sector": "科技"},
    "3067.HK": {"name": "恒生资讯科技", "sector": "科技"},

    # 金融
    "2829.HK": {"name": "ishares金融", "sector": "金融"},
    "2827.HK": {"name": "ishares银行", "sector": "金融"},

    # 消费
    "3036.HK": {"name": "恒生消费", "sector": "消费"},
    "2826.HK": {"name": "ishares消费", "sector": "消费"},

    # 医疗
    "3069.HK": {"name": "恒生医疗", "sector": "医疗"},

    # 能源
    "3097.HK": {"name": "恒生能源", "sector": "能源"},

    # 地产
    "2832.HK": {"name": "ishares地产", "sector": "地产"},

    # 工业
    "2825.HK": {"name": "ishares工业", "sector": "工业"},

    # 材料
    "3009.HK": {"name": "恒生原材料", "sector": "材料"},

    # 公用事业
    "3008.HK": {"name": "恒生公用", "sector": "公用事业"},
}

BENCHMARK = "2800.HK"  # 盈富基金(恒生指数)

def get_etf_codes():
    return list(ETF_UNIVERSE.keys())

def get_etf_map():
    return ETF_UNIVERSE

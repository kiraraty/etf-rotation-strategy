"""ETF池定义：约20只主流A股板块ETF"""

from typing import Dict, List, NamedTuple


class ETFInfo(NamedTuple):
    code: str       # ETF代码
    name: str       # ETF简称
    sector: str     # 所属板块


# 主流板块ETF池（优化版：减少重叠，增加大盘）
DEFAULT_ETF_POOL: List[ETFInfo] = [
    # 大盘指数
    ETFInfo("510300", "沪深300ETF", "大盘"),
    # 科技（保留2个核心）
    ETFInfo("512480", "半导体ETF", "半导体"),
    ETFInfo("512720", "计算机ETF", "计算机"),
    # 新能源
    ETFInfo("516160", "新能车ETF", "新能源"),
    ETFInfo("515790", "光伏ETF", "光伏"),
    # 医疗
    ETFInfo("512010", "医药ETF", "医药"),
    ETFInfo("512170", "医疗ETF", "医疗"),
    # 消费
    ETFInfo("510150", "消费ETF", "消费"),
    ETFInfo("512690", "酒ETF", "酒"),
    # 金融
    ETFInfo("512800", "银行ETF", "银行"),
    ETFInfo("512880", "证券ETF", "证券"),
    ETFInfo("512200", "房地产ETF", "房地产"),
    # 工业/周期
    ETFInfo("512660", "军工ETF", "军工"),
    ETFInfo("512400", "有色ETF", "有色"),
    ETFInfo("516780", "稀土ETF", "稀土"),
    # 其他
    ETFInfo("159825", "农业ETF", "农业"),
    ETFInfo("512580", "环保ETF", "环保"),
]

# 基准ETF
BENCHMARK_ETF = ETFInfo("510300", "沪深300ETF", "基准")


def get_etf_pool() -> List[ETFInfo]:
    """获取当前ETF池"""
    return list(DEFAULT_ETF_POOL)


def get_etf_codes() -> List[str]:
    """获取所有ETF代码列表"""
    return [e.code for e in DEFAULT_ETF_POOL]


def get_etf_map() -> Dict[str, ETFInfo]:
    """获取 code -> ETFInfo 映射"""
    return {e.code: e for e in DEFAULT_ETF_POOL}

"""全局配置：权重参数、缓存TTL、数据源设置"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict

# 自动加载 .env（确保所有页面都能读到环境变量）
_env_file = Path(__file__).parent / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().strip().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())


@dataclass
class WeightConfig:
    """指标权重配置"""
    momentum_5d: float = 0.08
    momentum_10d: float = 0.12
    momentum_20d: float = 0.15
    rps: float = 0.20
    money_flow: float = 0.10
    volatility: float = 0.08
    breakout: float = 0.12
    volume_confirm: float = 0.10
    news_sentiment: float = 0.05

    def as_dict(self) -> Dict[str, float]:
        return {
            "momentum_5d": self.momentum_5d,
            "momentum_10d": self.momentum_10d,
            "momentum_20d": self.momentum_20d,
            "rps": self.rps,
            "money_flow": self.money_flow,
            "volatility": self.volatility,
            "breakout": self.breakout,
            "volume_confirm": self.volume_confirm,
            "news_sentiment": self.news_sentiment,
        }

    def total(self) -> float:
        return sum(self.as_dict().values())


@dataclass
class CacheConfig:
    """缓存配置"""
    memory_ttl_seconds: int = 3600       # Streamlit 内存缓存 1h
    parquet_ttl_seconds: int = 14400     # Parquet 文件缓存 4h
    cache_dir: str = ".cache"


@dataclass
class DataConfig:
    """数据采集配置"""
    request_interval: float = 0.3        # akshare 请求间隔(秒)
    default_period_days: int = 120       # 默认拉取120个交易日
    benchmark_code: str = "510300"       # 基准：沪深300ETF


@dataclass
class SignalConfig:
    """信号阈值配置"""
    strong_threshold: float = 70         # >=70 强势-关注
    neutral_threshold: float = 40        # 40~70 中性-观望
    # <40 弱势-回避


@dataclass
class AppConfig:
    """应用总配置"""
    weights: WeightConfig = field(default_factory=WeightConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    data: DataConfig = field(default_factory=DataConfig)
    signal: SignalConfig = field(default_factory=SignalConfig)


# 全局默认配置实例
DEFAULT_CONFIG = AppConfig()

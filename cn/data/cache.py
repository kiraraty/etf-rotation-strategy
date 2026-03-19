"""Parquet 文件缓存层"""

import os
import time
from pathlib import Path
from typing import Optional

import pandas as pd

from config import DEFAULT_CONFIG


def _cache_path(key: str) -> Path:
    """生成缓存文件路径"""
    cache_dir = Path(DEFAULT_CONFIG.cache.cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    safe_key = key.replace("/", "_").replace("\\", "_")
    return cache_dir / f"{safe_key}.parquet"


def read_cache(key: str) -> Optional[pd.DataFrame]:
    """读取 Parquet 缓存，过期返回 None"""
    path = _cache_path(key)
    if not path.exists():
        return None

    mtime = path.stat().st_mtime
    age = time.time() - mtime
    if age > DEFAULT_CONFIG.cache.parquet_ttl_seconds:
        path.unlink(missing_ok=True)
        return None

    try:
        return pd.read_parquet(path)
    except Exception:
        path.unlink(missing_ok=True)
        return None


def write_cache(key: str, df: pd.DataFrame) -> None:
    """写入 Parquet 缓存"""
    if df is None or df.empty:
        return
    path = _cache_path(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=True)


def clear_cache() -> int:
    """清除所有缓存文件，返回清除数量"""
    cache_dir = Path(DEFAULT_CONFIG.cache.cache_dir)
    if not cache_dir.exists():
        return 0
    count = 0
    for f in cache_dir.glob("*.parquet"):
        f.unlink()
        count += 1
    return count

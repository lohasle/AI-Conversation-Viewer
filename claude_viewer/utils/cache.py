"""
缓存工具模块
提供内存缓存和 TTL（Time To Live）支持
"""

import time
import hashlib
import json
from typing import Any, Optional, Callable
from functools import wraps
from collections import OrderedDict
import threading


class LRUCache:
    """LRU (Least Recently Used) 缓存实现"""
    
    def __init__(self, max_size: int = 100):
        self.cache = OrderedDict()
        self.max_size = max_size
        self.lock = threading.Lock()
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self.lock:
            if key not in self.cache:
                return None
            # 移到末尾（最近使用）
            self.cache.move_to_end(key)
            return self.cache[key]
    
    def set(self, key: str, value: Any):
        """设置缓存值"""
        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
            self.cache[key] = value
            # 如果超过最大容量，删除最旧的
            if len(self.cache) > self.max_size:
                self.cache.popitem(last=False)
    
    def delete(self, key: str):
        """删除缓存值"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
    
    def clear(self):
        """清空缓存"""
        with self.lock:
            self.cache.clear()
    
    def size(self) -> int:
        """获取缓存大小"""
        return len(self.cache)


class TTLCache:
    """带 TTL（Time To Live）的缓存实现"""
    
    def __init__(self, max_size: int = 100, default_ttl: int = 300):
        """
        Args:
            max_size: 最大缓存条目数
            default_ttl: 默认过期时间（秒）
        """
        self.cache = OrderedDict()
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.lock = threading.Lock()
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self.lock:
            if key not in self.cache:
                return None
            
            value, expire_time = self.cache[key]
            
            # 检查是否过期
            if time.time() > expire_time:
                del self.cache[key]
                return None
            
            # 移到末尾（最近使用）
            self.cache.move_to_end(key)
            return value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """设置缓存值"""
        with self.lock:
            ttl = ttl or self.default_ttl
            expire_time = time.time() + ttl
            
            if key in self.cache:
                self.cache.move_to_end(key)
            
            self.cache[key] = (value, expire_time)
            
            # 如果超过最大容量，删除最旧的
            if len(self.cache) > self.max_size:
                self.cache.popitem(last=False)
    
    def delete(self, key: str):
        """删除缓存值"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
    
    def clear(self):
        """清空缓存"""
        with self.lock:
            self.cache.clear()
    
    def cleanup_expired(self):
        """清理过期的缓存条目"""
        with self.lock:
            current_time = time.time()
            expired_keys = [
                key for key, (_, expire_time) in self.cache.items()
                if current_time > expire_time
            ]
            for key in expired_keys:
                del self.cache[key]
    
    def size(self) -> int:
        """获取缓存大小"""
        return len(self.cache)


def cache_key(*args, **kwargs) -> str:
    """生成缓存键"""
    key_data = {
        'args': args,
        'kwargs': kwargs
    }
    key_str = json.dumps(key_data, sort_keys=True, default=str)
    return hashlib.md5(key_str.encode()).hexdigest()


def cached(cache_instance: Any, ttl: Optional[int] = None, key_prefix: str = ""):
    """
    缓存装饰器
    
    Args:
        cache_instance: 缓存实例（LRUCache 或 TTLCache）
        ttl: 过期时间（仅用于 TTLCache）
        key_prefix: 缓存键前缀
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            key = f"{key_prefix}:{func.__name__}:{cache_key(*args, **kwargs)}"
            
            # 尝试从缓存获取
            cached_value = cache_instance.get(key)
            if cached_value is not None:
                return cached_value
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 存入缓存
            if isinstance(cache_instance, TTLCache):
                cache_instance.set(key, result, ttl)
            else:
                cache_instance.set(key, result)
            
            return result
        
        # 添加清除缓存的方法
        def clear_cache():
            cache_instance.clear()
        
        wrapper.clear_cache = clear_cache
        return wrapper
    
    return decorator


# 全局缓存实例
# 项目列表缓存（5分钟过期）
projects_cache = TTLCache(max_size=50, default_ttl=300)

# 会话列表缓存（3分钟过期）
sessions_cache = TTLCache(max_size=200, default_ttl=180)

# 会话内容缓存（10分钟过期）
conversation_cache = TTLCache(max_size=100, default_ttl=600)

# 搜索结果缓存（2分钟过期）
search_cache = TTLCache(max_size=50, default_ttl=120)

# 统计数据缓存（5分钟过期）
statistics_cache = TTLCache(max_size=10, default_ttl=300)


def clear_all_caches():
    """清空所有缓存"""
    projects_cache.clear()
    sessions_cache.clear()
    conversation_cache.clear()
    search_cache.clear()
    statistics_cache.clear()


def get_cache_stats() -> dict:
    """获取缓存统计信息"""
    return {
        "projects_cache": projects_cache.size(),
        "sessions_cache": sessions_cache.size(),
        "conversation_cache": conversation_cache.size(),
        "search_cache": search_cache.size(),
        "statistics_cache": statistics_cache.size(),
    }

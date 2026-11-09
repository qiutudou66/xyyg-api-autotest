"""Redis 访问封装。"""
import redis

from common import config


def create_redis():
    return redis.Redis(
        host=config.REDIS_HOST,
        port=config.REDIS_PORT,
        password=config.REDIS_PASSWORD,
        decode_responses=True,
    )


def scan_keys(r, pattern):
    """用 scan_iter 而不是 keys：keys 会阻塞 Redis，scan 是分页扫。"""
    return list(r.scan_iter(match=pattern, count=500))


def delete_pattern(r, pattern):
    keys = scan_keys(r, pattern)
    if keys:
        r.delete(*keys)
    return len(keys)

"""轮询等待工具。

秒杀下单、RabbitMQ 扇出、店铺缓存重建都是异步的，
接口返回成功不代表数据已经写好。固定 sleep(3) 要么慢、要么不稳定，
所以统一用「每隔一小段时间查一次，直到条件成立或超时」。
"""
import time


def wait_until(predicate, timeout=10.0, interval=0.2, desc=""):
    """反复执行 predicate，直到它返回真值。

    predicate 抛异常也当作「还没好」，继续等（比如 DB 里还查不到、Redis 还没写）。
    超时后抛出 AssertionError，并带上最后一次的结果，方便定位。
    """
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        try:
            last = predicate()
            if last:
                return last
        except Exception as e:  # 查询过程中数据还没准备好，属于正常情况
            last = e
        time.sleep(interval)
    raise AssertionError(f"等待超时（{timeout}s）: {desc}，最后一次结果: {last!r}")

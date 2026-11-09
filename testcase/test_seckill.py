"""秒杀用例：正常下单、重复下单、库存耗尽、并发、异步落库。

秒杀链路（读代码确认过的真实行为）：
1. Lua 在 Redis 里检查库存 + 一人一单，原子扣库存、写 order 集合、xadd 到 stream.orders；
2. 接口立刻返回 orderId —— 此时数据库里还没有订单；
3. 后台线程从 stream 消费，加 Redisson 锁、扣 DB 库存、写订单；
4. 所以断言必须「Redis 同步断言 + MySQL 轮询异步断言」两段做。
"""
import threading
from concurrent.futures import ThreadPoolExecutor

import allure
import pymysql
import pytest

from common.assert_util import assert_fail, assert_success
from common.client import ApiClient, auth_headers
from common.wait import wait_until

FEATURE = "秒杀"


def _redis_stock(r, voucher_id):
    value = r.get(f"seckill:stock:{voucher_id}")
    return None if value is None else int(value)


def _db_stock(db, voucher_id):
    return db.scalar("SELECT stock FROM tb_seckill_voucher WHERE voucher_id=%s", (voucher_id,))


def _order_count(db, voucher_id):
    return db.scalar("SELECT COUNT(*) FROM tb_voucher_order WHERE voucher_id=%s", (voucher_id,))


@allure.feature(FEATURE)
@allure.story("正常下单")
@pytest.mark.smoke
def test_seckill_success_and_async_order(seckill_api, shop_factory, voucher_factory, users, db, r):
    shop_id, _ = shop_factory()
    voucher_id, _ = voucher_factory(shop_id, stock=3)
    user = users.create()

    order_id = assert_success(seckill_api.seckill(voucher_id, user.token))
    assert isinstance(order_id, int), f"接口应该返回订单 id，实际返回 {order_id!r}"

    # Redis 是同步扣的，可以立刻断言
    assert _redis_stock(r, voucher_id) == 2
    assert r.sismember(f"seckill:order:{voucher_id}", str(user.user_id)) == 1

    # 数据库是异步写的，必须轮询等
    order = wait_until(
        lambda: db.one(
            "SELECT id, user_id, voucher_id FROM tb_voucher_order WHERE id=%s",
            (order_id,),
        ),
        timeout=10,
        desc="订单异步落库",
    )
    assert order["user_id"] == user.user_id
    assert order["voucher_id"] == voucher_id

    wait_until(lambda: _db_stock(db, voucher_id) == 2, timeout=10, desc="数据库库存扣减到 2")


@allure.feature(FEATURE)
@allure.story("重复下单")
def test_same_user_cannot_buy_twice(seckill_api, shop_factory, voucher_factory, users, db, r):
    shop_id, _ = shop_factory()
    voucher_id, _ = voucher_factory(shop_id, stock=5)
    user = users.create()

    assert_success(seckill_api.seckill(voucher_id, user.token))
    second = seckill_api.seckill(voucher_id, user.token)
    assert_fail(second, "没有购买资格！")

    assert _redis_stock(r, voucher_id) == 4
    wait_until(lambda: _order_count(db, voucher_id) == 1, timeout=10, desc="只生成一条订单")


@allure.feature(FEATURE)
@allure.story("库存耗尽")
@pytest.mark.slow
def test_stock_exhausted(seckill_api, shop_factory, voucher_factory, users, db, r):
    shop_id, _ = shop_factory()
    voucher_id, _ = voucher_factory(shop_id, stock=1)
    user_a = users.create()
    user_b = users.create()

    assert_success(seckill_api.seckill(voucher_id, user_a.token))
    assert_fail(seckill_api.seckill(voucher_id, user_b.token), "库存不足！")

    assert _redis_stock(r, voucher_id) == 0
    wait_until(lambda: _order_count(db, voucher_id) == 1, timeout=10, desc="只有一单成功")
    wait_until(lambda: _db_stock(db, voucher_id) == 0, timeout=10, desc="数据库库存扣到 0")


@allure.feature(FEATURE)
@allure.story("参数校验")
@pytest.mark.xfail(
    reason="缺陷：秒杀不存在的券，Lua 对 nil 做比较直接报错，被兜底成「服务器异常」",
    strict=True,
)
def test_seckill_nonexistent_voucher(seckill_api, users):
    user = users.create()
    resp = seckill_api.seckill(999999999, user.token)
    assert_fail(resp, "优惠券不存在")


@allure.feature(FEATURE)
@allure.story("时间窗口")
@pytest.mark.xfail(reason="缺陷：秒杀不校验 beginTime/endTime，过期券仍然能抢", strict=True)
def test_seckill_expired_voucher_should_fail(
    seckill_api, shop_factory, voucher_factory, users
):
    shop_id, _ = shop_factory()
    voucher_id, _ = voucher_factory(
        shop_id,
        stock=5,
        begin="2020-01-01T00:00:00",
        end="2020-01-02T00:00:00",
    )
    user = users.create()
    resp = seckill_api.seckill(voucher_id, user.token)
    assert_fail(resp, "活动已结束")


@allure.feature(FEATURE)
@allure.story("时间窗口")
@pytest.mark.xfail(reason="缺陷：秒杀不校验 beginTime/endTime，未开始的券也能抢", strict=True)
def test_seckill_not_started_voucher_should_fail(
    seckill_api, shop_factory, voucher_factory, users
):
    shop_id, _ = shop_factory()
    voucher_id, _ = voucher_factory(
        shop_id,
        stock=5,
        begin="2030-01-01T00:00:00",
        end="2031-01-01T00:00:00",
    )
    user = users.create()
    resp = seckill_api.seckill(voucher_id, user.token)
    assert_fail(resp, "活动未开始")


@allure.feature(FEATURE)
@allure.story("鉴权")
def test_seckill_without_token_returns_401(seckill_api, shop_factory, voucher_factory):
    shop_id, _ = shop_factory()
    voucher_id, _ = voucher_factory(shop_id, stock=1)
    resp = seckill_api.client.post(f"/voucher-order/seckill/{voucher_id}")
    assert resp.status_code == 401


@allure.feature(FEATURE)
@allure.story("并发")
@pytest.mark.slow
def test_concurrent_seckill_no_oversell(shop_factory, voucher_factory, users, db, r):
    """10 个用户同一时刻抢 5 张券：只能成功 5 个，不能超卖。

    为什么不用 pytest-xdist：它是「进程级并发」，启动时间参差不齐，
    做不了「同一时刻一起扣库存」的断言。这里用线程 + Barrier 把 10 个请求卡到同一起跑线。
    """
    shop_id, _ = shop_factory()
    initial_stock = 5
    voucher_id, _ = voucher_factory(shop_id, stock=initial_stock)

    buyers = [users.create() for _ in range(10)]
    barrier = threading.Barrier(len(buyers))

    def buy(user):
        # requests.Session 不是线程安全的，每个线程用自己的 client
        client = ApiClient()
        try:
            barrier.wait(timeout=10)
            return client.post(
                f"/voucher-order/seckill/{voucher_id}",
                headers=auth_headers(user.token),
                timeout=15,
            )
        finally:
            client.close()

    with ThreadPoolExecutor(max_workers=len(buyers)) as pool:
        responses = list(pool.map(buy, buyers))

    bodies = [resp.json() for resp in responses]
    success = [body for body in bodies if body.get("success") is True]
    failed = [body for body in bodies if body.get("success") is False]

    assert len(success) == initial_stock, (
        f"应该恰好成功 {initial_stock} 个，实际 {len(success)} 个；"
        f"失败信息={[b.get('errorMsg') for b in failed]}"
    )
    assert all(body.get("errorMsg") == "库存不足！" for body in failed)

    wait_until(lambda: _order_count(db, voucher_id) == initial_stock, timeout=15, desc="订单数=5")
    wait_until(lambda: _db_stock(db, voucher_id) == 0, timeout=15, desc="数据库库存=0")

    redis_stock = _redis_stock(r, voucher_id)
    db_stock = _db_stock(db, voucher_id)
    order_count = _order_count(db, voucher_id)
    assert redis_stock == 0
    assert redis_stock == db_stock == initial_stock - order_count, (
        f"三方不一致: redis={redis_stock}, db={db_stock}, orders={order_count}"
    )
    assert r.scard(f"seckill:order:{voucher_id}") == initial_stock


@allure.feature(FEATURE)
@allure.story("防重")
def test_db_unique_index_rejects_duplicate_order(shop_factory, voucher_factory, users, db):
    """第三道防线：即使 Redis 判断失效，数据库唯一索引 uk_user_voucher 也会拦下重复订单。"""
    shop_id, _ = shop_factory()
    voucher_id, _ = voucher_factory(shop_id, stock=5)
    user = users.create()

    db.execute(
        "INSERT INTO tb_voucher_order (id, user_id, voucher_id) VALUES (%s,%s,%s)",
        (9000000000001, user.user_id, voucher_id),
    )
    with pytest.raises(pymysql.err.IntegrityError):
        db.execute(
            "INSERT INTO tb_voucher_order (id, user_id, voucher_id) VALUES (%s,%s,%s)",
            (9000000000002, user.user_id, voucher_id),
        )

"""优惠券用例：普通券、秒杀券、按商铺查询。"""
import allure
import pytest

from common import config
from common.assert_util import assert_fail, assert_success

FEATURE = "优惠券"


def _voucher_payload(shop_id, title, **overrides):
    payload = {
        "shopId": shop_id,
        "title": title,
        "subTitle": "自动化测试用",
        "rules": "仅用于自动化测试",
        "payValue": 100,
        "actualValue": 200,
        "type": 0,
        "status": 1,
    }
    payload.update(overrides)
    return payload


@allure.feature(FEATURE)
@allure.story("查询优惠券")
@pytest.mark.smoke
def test_list_vouchers_of_shop(voucher_api):
    data = assert_success(voucher_api.list_by_shop(1))
    assert data, "1 号店铺应该有优惠券"
    ids = {item["id"] for item in data}
    assert 1 in ids and 10 in ids

    seckill = next(item for item in data if item["id"] == 10)
    assert seckill["type"] == 1
    assert seckill["stock"] == 100, "秒杀券应该带库存字段"
    assert seckill["beginTime"] and seckill["endTime"]


@allure.feature(FEATURE)
@allure.story("查询优惠券")
def test_list_vouchers_of_unknown_shop(voucher_api):
    assert assert_success(voucher_api.list_by_shop(999999999)) == []


@allure.feature(FEATURE)
@allure.story("新增普通券")
@pytest.mark.smoke
def test_add_normal_voucher(voucher_api, setup_user, db):
    title = f"{config.TEST_NAME_PREFIX}普通券"
    voucher_id = assert_success(
        voucher_api.add(_voucher_payload(1, title), token=setup_user.token)
    )
    row = db.one("SELECT id, title, type FROM tb_voucher WHERE id=%s", (voucher_id,))
    assert row is not None
    assert row["title"] == title
    assert row["type"] == 0


@allure.feature(FEATURE)
@allure.story("新增秒杀券")
def test_add_seckill_voucher_writes_db_and_redis(voucher_api, setup_user, db, r):
    title = f"{config.TEST_NAME_PREFIX}秒杀券"
    payload = _voucher_payload(
        1,
        title,
        type=1,
        stock=7,
        beginTime="2026-01-01T00:00:00",
        endTime="2030-01-01T00:00:00",
    )
    voucher_id = assert_success(voucher_api.add_seckill(payload, token=setup_user.token))

    row = db.one(
        "SELECT voucher_id, stock, begin_time, end_time FROM tb_seckill_voucher WHERE voucher_id=%s",
        (voucher_id,),
    )
    assert row is not None
    assert row["stock"] == 7
    assert r.get(f"seckill:stock:{voucher_id}") == "7"


@allure.feature(FEATURE)
@allure.story("新增秒杀券")
def test_list_only_online_vouchers(voucher_api, setup_user, db):
    """status=2（下架）的券不应该出现在店铺券列表里。"""
    title = f"{config.TEST_NAME_PREFIX}已下架券"
    voucher_id = assert_success(
        voucher_api.add(_voucher_payload(1, title, status=2), token=setup_user.token)
    )
    data = assert_success(voucher_api.list_by_shop(1))
    assert voucher_id not in {item["id"] for item in data}


@allure.feature(FEATURE)
@allure.story("新增秒杀券")
@pytest.mark.xfail(reason="缺陷：新增秒杀券不校验 stock，null 会 NPE 被兜底成「服务器异常」", strict=True)
def test_add_seckill_voucher_without_stock(voucher_api, setup_user):
    title = f"{config.TEST_NAME_PREFIX}无库存字段"
    payload = _voucher_payload(
        1,
        title,
        type=1,
        beginTime="2026-01-01T00:00:00",
        endTime="2030-01-01T00:00:00",
    )
    resp = voucher_api.add_seckill(payload, token=setup_user.token)
    assert_fail(resp, "库存不能为空")


@allure.feature(FEATURE)
@allure.story("新增秒杀券")
@pytest.mark.xfail(reason="缺陷：新增秒杀券不校验库存为负数", strict=True)
def test_add_seckill_voucher_with_negative_stock(voucher_api, setup_user):
    title = f"{config.TEST_NAME_PREFIX}负库存"
    payload = _voucher_payload(
        1,
        title,
        type=1,
        stock=-1,
        beginTime="2026-01-01T00:00:00",
        endTime="2030-01-01T00:00:00",
    )
    resp = voucher_api.add_seckill(payload, token=setup_user.token)
    assert_fail(resp, "库存不能小于 0")


@allure.feature(FEATURE)
@allure.story("新增秒杀券")
@pytest.mark.xfail(reason="缺陷：/voucher/** 被排除在登录拦截之外，未登录也能发券", strict=True)
def test_add_voucher_without_token_should_401(voucher_api):
    resp = voucher_api.add(_voucher_payload(1, f"{config.TEST_NAME_PREFIX}未登录发券"))
    assert resp.status_code == 401


@allure.feature(FEATURE)
@allure.story("新增秒杀券")
@pytest.mark.xfail(reason="缺陷：新增秒杀券不校验开始 / 结束时间先后", strict=True)
def test_add_seckill_voucher_with_reversed_time(voucher_api, setup_user):
    title = f"{config.TEST_NAME_PREFIX}时间倒置"
    payload = _voucher_payload(
        1,
        title,
        type=1,
        stock=5,
        beginTime="2030-01-01T00:00:00",
        endTime="2026-01-01T00:00:00",
    )
    resp = voucher_api.add_seckill(payload, token=setup_user.token)
    assert_fail(resp)

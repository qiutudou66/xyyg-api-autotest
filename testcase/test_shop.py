"""商铺与商铺类型用例。

店铺详情走的是「逻辑过期」缓存：
- Redis 里没有 cache:shop:{id} 时，接口直接返回「店铺不存在」（不会回查数据库）；
- 更新店铺后，缓存过期时间被置为当前时间，下一个请求返回旧数据并异步重建。
这两点是测试设计的关键。
"""
import allure
import pytest

from common import config
from common.assert_util import assert_fail, assert_success
from common.wait import wait_until

FEATURE = "商铺"


def _shop_payload(name, **overrides):
    payload = {
        "name": name,
        "typeId": 1,
        "images": "/imgs/shops/shop01.jpg",
        "area": "自动化测试区",
        "address": "自动化测试地址 1 号",
        "x": 112.9901,
        "y": 28.1801,
        "avgPrice": 12,
        "sold": 0,
        "comments": 0,
        "score": 50,
        "openHours": "09:00-21:00",
    }
    payload.update(overrides)
    return payload


@allure.feature(FEATURE)
@allure.story("店铺类型")
@pytest.mark.smoke
def test_list_shop_types(shop_api):
    data = assert_success(shop_api.list_types())
    assert len(data) == 10, f"期望 10 个店铺类型，实际 {len(data)}"
    sorts = [item["sort"] for item in data]
    assert sorts == sorted(sorts), f"店铺类型没有按 sort 升序返回: {sorts}"


@allure.feature(FEATURE)
@allure.story("店铺类型")
def test_shop_types_cached_in_redis(shop_api, r):
    """第一次查库并写缓存，第二次直接读缓存，结果一致。"""
    r.delete("cache:sort")
    first = assert_success(shop_api.list_types())
    assert r.exists("cache:sort") == 1, "查询店铺类型后没有写入 Redis 缓存"
    second = assert_success(shop_api.list_types())
    assert [x["id"] for x in first] == [x["id"] for x in second]


@allure.feature(FEATURE)
@allure.story("店铺详情")
@pytest.mark.smoke
def test_get_existing_shop(shop_api):
    data = assert_success(shop_api.get(1))
    assert data["id"] == 1
    assert data["name"]
    assert data["typeId"] == 1


@allure.feature(FEATURE)
@allure.story("店铺详情")
def test_get_nonexistent_shop(shop_api):
    resp = shop_api.get(999999999)
    assert_fail(resp, "店铺不存在")


@allure.feature(FEATURE)
@allure.story("店铺详情")
def test_new_shop_detail_not_visible_without_cache(shop_api, shop_factory):
    """刚创建的店铺没有预热缓存，详情接口会判成「不存在」。

    这是逻辑过期方案的真实行为：缓存未命中直接返回 null，不回查数据库。
    """
    shop_id, _ = shop_factory()
    assert_fail(shop_api.get(shop_id), "店铺不存在")


@allure.feature(FEATURE)
@allure.story("店铺列表")
def test_query_shops_by_type(shop_api):
    data = assert_success(shop_api.by_type(1))
    assert 1 <= len(data) <= 5, f"默认分页每页 5 条，实际 {len(data)}"
    assert all(item["typeId"] == 1 for item in data)


@allure.feature(FEATURE)
@allure.story("店铺列表")
def test_query_shops_by_type_with_location(shop_api):
    data = assert_success(shop_api.by_type(1, x=112.9901, y=28.1801))
    assert data, "按距离查询应该返回店铺"
    assert all("distance" in item for item in data), "按距离查询的结果缺少 distance 字段"


@allure.feature(FEATURE)
@allure.story("店铺列表")
def test_query_shops_by_unknown_type(shop_api):
    assert assert_success(shop_api.by_type(999)) == []


@allure.feature(FEATURE)
@allure.story("店铺搜索")
def test_search_shop_by_name(shop_api):
    data = assert_success(shop_api.by_name("食堂"))
    assert data, "按关键字「食堂」应该能搜到店铺"
    assert all("食堂" in item["name"] for item in data)


@allure.feature(FEATURE)
@allure.story("店铺搜索")
def test_search_shop_with_blank_name(shop_api):
    data = assert_success(shop_api.by_name(""))
    assert 1 <= len(data) <= 10


@allure.feature(FEATURE)
@allure.story("新增店铺")
def test_create_shop(shop_api, shop_factory, db):
    shop_id, name = shop_factory()
    row = db.one("SELECT id, name, type_id FROM tb_shop WHERE id=%s", (shop_id,))
    assert row is not None
    assert row["name"] == name
    assert row["type_id"] == 1


@allure.feature(FEATURE)
@allure.story("新增店铺")
@pytest.mark.xfail(reason="缺陷：/shop/** 被排除在登录拦截之外，未登录也能新增店铺", strict=True)
def test_create_shop_without_token_should_401(shop_api):
    name = f"{config.TEST_NAME_PREFIX}未登录店铺"
    resp = shop_api.create(_shop_payload(name), token=None)
    assert resp.status_code == 401


@allure.feature(FEATURE)
@allure.story("更新店铺")
def test_update_shop_and_cache_rebuild(shop_api, shop_factory, setup_user):
    shop_id, _ = shop_factory()
    new_name = f"{config.TEST_NAME_PREFIX}改名后的店铺"
    payload = {"id": shop_id, "name": new_name}
    assert_success(shop_api.update(payload, token=setup_user.token))

    # 更新后缓存会异步重建，轮询直到读到新名字
    data = wait_until(
        lambda: (lambda d: d if d and d.get("name") == new_name else None)(
            assert_success(shop_api.get(shop_id))
        ),
        timeout=5,
        desc="店铺缓存重建为新的名称",
    )
    assert data["name"] == new_name


@allure.feature(FEATURE)
@allure.story("更新店铺")
def test_update_shop_without_id(shop_api, setup_user):
    resp = shop_api.update({"name": "没有 id 的更新"}, token=setup_user.token)
    assert_fail(resp, "商户id不能为空")

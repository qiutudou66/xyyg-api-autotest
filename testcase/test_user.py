"""用户资料、签到相关用例。"""
import datetime

import allure
import pytest

from common.assert_util import assert_fail, assert_success

FEATURE = "用户"


@allure.feature(FEATURE)
@allure.story("当前用户")
def test_me_with_token(user_api, users):
    user = users.create()
    data = assert_success(user_api.me(user.token))
    assert data["id"] == user.user_id
    assert "phone" not in data, "当前用户接口不应该把手机号返回给前端"


@allure.feature(FEATURE)
@allure.story("用户查询")
def test_get_user_by_id(user_api, users):
    user = users.create()
    data = assert_success(user_api.get_user(user.user_id, token=user.token))
    assert data["id"] == user.user_id
    assert data["nickName"] == user.nickname
    assert "phone" not in data, "用户公开资料不应该包含手机号"


@allure.feature(FEATURE)
@allure.story("用户查询")
def test_get_nonexistent_user(user_api, users):
    user = users.create()
    resp = user_api.get_user(999999999, token=user.token)
    assert_fail(resp, "用户不存在")


@allure.feature(FEATURE)
@allure.story("用户详情")
def test_user_info_empty_for_new_user(user_api, users):
    """新用户没有填过资料，详情接口返回 data=null，而不是报错。"""
    user = users.create()
    data = assert_success(user_api.info(user.user_id, token=user.token))
    assert data is None


@allure.feature(FEATURE)
@allure.story("用户详情")
def test_user_info_nonexistent_id(user_api, users):
    user = users.create()
    data = assert_success(user_api.info(999999999, token=user.token))
    assert data is None


@allure.feature(FEATURE)
@allure.story("签到")
@pytest.mark.smoke
def test_sign_writes_redis_bitmap(user_api, users, r):
    """签到：Redis bitmap 的「今天」那一位应该被置 1。"""
    user = users.create()
    assert_success(user_api.sign(user.token))

    today = datetime.date.today()
    key = f"sign:{user.user_id}:{today.strftime('%Y%m')}"
    assert r.getbit(key, today.day - 1) == 1, "签到后 Redis bitmap 没有被置位"


@allure.feature(FEATURE)
@allure.story("签到")
def test_sign_count_zero_before_sign(user_api, users):
    user = users.create()
    assert assert_success(user_api.sign_count(user.token)) == 0


@allure.feature(FEATURE)
@allure.story("签到")
def test_sign_count_after_sign(user_api, users):
    """签到 1 天后，连续签到天数应该是 1。"""
    user = users.create()
    assert_success(user_api.sign(user.token))
    count = assert_success(user_api.sign_count(user.token))
    assert count == 1


@allure.feature(FEATURE)
@allure.story("鉴权")
def test_sign_without_token_returns_401(user_api):
    resp = user_api.client.post("/user/sign")
    assert resp.status_code == 401

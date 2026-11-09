"""关注用例：关注 / 取关 / 是否关注 / 共同关注。

关注关系存两份：
- MySQL tb_follow：持久化、判断是否关注、扇出时查粉丝；
- Redis Set follows:{userId}：共同关注用集合交集算，快。
两份必须同步，所以断言时两边都查。
"""
import allure
import pytest

from common.assert_util import assert_success

FEATURE = "关注"


@allure.feature(FEATURE)
@allure.story("关注")
@pytest.mark.smoke
def test_follow_user(follow_api, users, db, r):
    user = users.create()
    target = users.create()

    assert_success(follow_api.follow(target.user_id, True, user.token))

    row = db.one(
        "SELECT id FROM tb_follow WHERE user_id=%s AND follow_user_id=%s",
        (user.user_id, target.user_id),
    )
    assert row is not None, "关注后数据库没有记录"
    assert r.sismember(f"follows:{user.user_id}", str(target.user_id)) == 1


@allure.feature(FEATURE)
@allure.story("是否关注")
@pytest.mark.smoke
def test_is_follow(follow_api, users):
    user = users.create()
    target = users.create()

    assert assert_success(follow_api.is_follow(target.user_id, user.token)) is False
    assert_success(follow_api.follow(target.user_id, True, user.token))
    assert assert_success(follow_api.is_follow(target.user_id, user.token)) is True


@allure.feature(FEATURE)
@allure.story("取关")
def test_unfollow_user(follow_api, users, db, r):
    user = users.create()
    target = users.create()

    assert_success(follow_api.follow(target.user_id, True, user.token))
    assert_success(follow_api.follow(target.user_id, False, user.token))

    row = db.one(
        "SELECT id FROM tb_follow WHERE user_id=%s AND follow_user_id=%s",
        (user.user_id, target.user_id),
    )
    assert row is None, "取关后数据库记录还在"
    assert r.sismember(f"follows:{user.user_id}", str(target.user_id)) == 0


@allure.feature(FEATURE)
@allure.story("共同关注")
def test_common_follow(follow_api, users):
    user_a = users.create()
    user_b = users.create()
    common = users.create()

    assert_success(follow_api.follow(common.user_id, True, user_a.token))
    assert_success(follow_api.follow(common.user_id, True, user_b.token))

    data = assert_success(follow_api.commons(user_b.user_id, user_a.token))
    assert common.user_id in {item["id"] for item in data}


@allure.feature(FEATURE)
@allure.story("共同关注")
def test_common_follow_empty(follow_api, users):
    user_a = users.create()
    user_b = users.create()
    assert_success(follow_api.follow(users.create().user_id, True, user_a.token))

    data = assert_success(follow_api.commons(user_b.user_id, user_a.token))
    assert data == []


@allure.feature(FEATURE)
@allure.story("鉴权")
def test_follow_without_token_returns_401(follow_api, users):
    target = users.create()
    resp = follow_api.client.post(f"/follow/{target.user_id}/true")
    assert resp.status_code == 401


@allure.feature(FEATURE)
@allure.story("重复关注")
@pytest.mark.xfail(reason="缺陷：重复关注不幂等，tb_follow 没有唯一索引，会插入两条记录", strict=True)
def test_follow_twice_is_idempotent(follow_api, users, db):
    user = users.create()
    target = users.create()
    assert_success(follow_api.follow(target.user_id, True, user.token))
    assert_success(follow_api.follow(target.user_id, True, user.token))

    count = db.scalar(
        "SELECT COUNT(*) FROM tb_follow WHERE user_id=%s AND follow_user_id=%s",
        (user.user_id, target.user_id),
    )
    assert count == 1


@allure.feature(FEATURE)
@allure.story("边界")
@pytest.mark.xfail(reason="缺陷：允许关注自己", strict=True)
def test_cannot_follow_self(follow_api, users):
    user = users.create()
    assert_success(follow_api.follow(user.user_id, True, user.token))
    assert assert_success(follow_api.is_follow(user.user_id, user.token)) is False


@allure.feature(FEATURE)
@allure.story("边界")
@pytest.mark.xfail(reason="缺陷：关注不存在的用户也能成功（没有用户存在性校验）", strict=True)
def test_follow_nonexistent_user(follow_api, users):
    user = users.create()
    resp = follow_api.follow(999999999, True, user.token)
    assert resp.json().get("success") is False

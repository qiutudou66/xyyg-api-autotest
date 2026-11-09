"""校园动态用例：发布、详情、热门、点赞、关注流。

关注流是 RabbitMQ 异步扇出：
发博 → feed.exchange → feed.fanout.queue → 消费者写每个粉丝的 Redis ZSet。
所以「发博成功」不等于「粉丝立刻能刷到」，必须轮询 feed:{userId}。
"""
import time

import allure
import pytest

from common import config
from common.assert_util import assert_fail, assert_success

FEATURE = "动态"


def _blog_payload(title, **overrides):
    payload = {
        "shopId": 1,
        "title": title,
        "images": "/imgs/blogs/blog1.jpg",
        "content": "这是一条自动化测试动态",
        "liked": 0,
        "comments": 0,
    }
    payload.update(overrides)
    return payload


@allure.feature(FEATURE)
@allure.story("发布动态")
@pytest.mark.smoke
def test_publish_blog(blog_api, users, db):
    user = users.create()
    title = f"{config.TEST_NAME_PREFIX}发布动态"
    blog_id = assert_success(blog_api.save(_blog_payload(title), token=user.token))

    row = db.one("SELECT id, user_id, title FROM tb_blog WHERE id=%s", (blog_id,))
    assert row is not None
    assert row["user_id"] == user.user_id
    assert row["title"] == title


@allure.feature(FEATURE)
@allure.story("发布动态")
def test_publish_blog_without_token_returns_401(blog_api):
    resp = blog_api.client.post("/blog", json=_blog_payload(f"{config.TEST_NAME_PREFIX}未登录"))
    assert resp.status_code == 401


@allure.feature(FEATURE)
@allure.story("发布动态")
def test_publish_blog_with_empty_content_should_fail(blog_api, users):
    user = users.create()
    resp = blog_api.save(
        _blog_payload(f"{config.TEST_NAME_PREFIX}空内容", content=""),
        token=user.token,
    )
    assert_fail(resp, "内容不能为空")


@allure.feature(FEATURE)
@allure.story("动态详情")
@pytest.mark.smoke
def test_blog_detail(blog_api, users):
    user = users.create()
    blog_id = assert_success(
        blog_api.save(_blog_payload(f"{config.TEST_NAME_PREFIX}详情"), token=user.token)
    )
    data = assert_success(blog_api.detail(blog_id, token=user.token))
    assert data["id"] == blog_id
    assert data["name"] == user.nickname
    assert "icon" in data


@allure.feature(FEATURE)
@allure.story("动态详情")
def test_blog_detail_not_exists(blog_api, users):
    user = users.create()
    assert_fail(blog_api.detail(999999999, token=user.token), "博客不存在")


@allure.feature(FEATURE)
@allure.story("热门动态")
def test_hot_blogs_contains_published(blog_api, users):
    user = users.create()
    blog_id = assert_success(
        blog_api.save(_blog_payload(f"{config.TEST_NAME_PREFIX}热门"), token=user.token)
    )
    data = assert_success(blog_api.hot(1, token=user.token))
    assert 1 <= len(data) <= 10
    assert blog_id in {item["id"] for item in data}


@allure.feature(FEATURE)
@allure.story("点赞")
@pytest.mark.smoke
def test_like_and_unlike(blog_api, users, db, r):
    user = users.create()
    blog_id = assert_success(
        blog_api.save(_blog_payload(f"{config.TEST_NAME_PREFIX}点赞"), token=user.token)
    )

    # 点赞
    assert_success(blog_api.like(blog_id, user.token))
    assert db.scalar("SELECT liked FROM tb_blog WHERE id=%s", (blog_id,)) == 1
    assert r.zscore(f"blog:liked:{blog_id}", str(user.user_id)) is not None

    detail = assert_success(blog_api.detail(blog_id, token=user.token))
    assert detail["isLike"] is True
    likes = assert_success(blog_api.likes(blog_id, token=user.token))
    assert user.user_id in {item["id"] for item in likes}

    # 再点一次 = 取消点赞
    assert_success(blog_api.like(blog_id, user.token))
    assert db.scalar("SELECT liked FROM tb_blog WHERE id=%s", (blog_id,)) == 0
    assert r.zscore(f"blog:liked:{blog_id}", str(user.user_id)) is None
    assert assert_success(blog_api.likes(blog_id, token=user.token)) == []


@allure.feature(FEATURE)
@allure.story("点赞")
def test_like_nonexistent_blog_should_fail(blog_api, users):
    user = users.create()
    assert_fail(blog_api.like(999999999, user.token), "博客不存在")


@allure.feature(FEATURE)
@allure.story("我的动态")
def test_my_blogs(blog_api, users):
    user = users.create()
    blog_id = assert_success(
        blog_api.save(_blog_payload(f"{config.TEST_NAME_PREFIX}我的动态"), token=user.token)
    )
    data = assert_success(blog_api.my_blogs(user.token))
    assert blog_id in {item["id"] for item in data}


@allure.feature(FEATURE)
@allure.story("用户动态")
def test_blogs_of_user(blog_api, users):
    user = users.create()
    blog_id = assert_success(
        blog_api.save(_blog_payload(f"{config.TEST_NAME_PREFIX}他人主页"), token=user.token)
    )
    data = assert_success(blog_api.by_user(user.user_id, token=user.token))
    assert blog_id in {item["id"] for item in data}


@allure.feature(FEATURE)
@allure.story("关注流")
@pytest.mark.slow
def test_follow_feed_via_rabbitmq(blog_api, follow_api, users, r):
    author = users.create()
    fan = users.create()
    assert_success(follow_api.follow(author.user_id, True, fan.token))

    title = f"{config.TEST_NAME_PREFIX}关注流动态"
    blog_id = assert_success(blog_api.save(_blog_payload(title), token=author.token))

    # 等 RabbitMQ 消费者把这条动态写进粉丝的收件箱
    from common.wait import wait_until

    wait_until(
        lambda: r.zscore(f"feed:{fan.user_id}", str(blog_id)) is not None,
        timeout=10,
        desc="RabbitMQ 扇出到粉丝 feed",
    )

    data = assert_success(blog_api.follow_feed(9999999999999, 0, token=fan.token))
    assert data is not None, "关注流为空，扇出可能没生效"
    assert blog_id in {item["id"] for item in data["list"]}


@allure.feature(FEATURE)
@allure.story("关注流")
@pytest.mark.slow
def test_follow_feed_empty_for_non_follower(blog_api, users):
    author = users.create()
    stranger = users.create()
    blog_id = assert_success(
        blog_api.save(_blog_payload(f"{config.TEST_NAME_PREFIX}非粉丝"), token=author.token)
    )
    # 给 RabbitMQ 一点时间；陌生人没关注作者，收件箱不该有这条
    time.sleep(1)
    data = assert_success(blog_api.follow_feed(9999999999999, 0, token=stranger.token))
    assert data is None or blog_id not in {item["id"] for item in data.get("list", [])}

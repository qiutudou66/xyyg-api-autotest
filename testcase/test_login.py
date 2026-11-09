"""登录链路用例：验证码 → 登录 → token。

重点：
- 业务失败 HTTP 仍是 200，必须断言响应体里的 success；
- 验证码存在 Redis 的 login:code:{phone}，TTL 只有 2 分钟；
- 新手机号登录会自动注册。
"""
import allure
import pytest
import yaml

from common import config
from common.assert_util import assert_fail, assert_success, assert_true

FEATURE = "登录鉴权"


def _load_phone_cases():
    path = config.ROOT / "data" / "login_phone_cases.yaml"
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)["cases"]


def _phone_params():
    params = []
    for case in _load_phone_cases():
        marks = []
        if case.get("xfail_reason"):
            marks.append(pytest.mark.xfail(reason=case["xfail_reason"], strict=True))
        params.append(pytest.param(case["phone"], case["success"], id=case["id"], marks=marks))
    return params


@allure.feature(FEATURE)
@allure.story("发送验证码")
@pytest.mark.parametrize("phone, expected_success", _phone_params())
@pytest.mark.smoke
def test_send_code_phone_validation(user_api, r, phone, expected_success):
    """手机号格式校验：合法号返回成功，非法号返回「手机号格式错误」。"""
    resp = user_api.send_code(phone)
    if expected_success:
        assert_success(resp)
    else:
        assert_fail(resp, "手机号格式错误")
    # 顺手清掉本用例产生的验证码，避免污染后续用例
    if phone:
        r.delete(f"login:code:{phone}")


@allure.feature(FEATURE)
@allure.story("登录")
@pytest.mark.smoke
def test_login_new_phone_auto_register(user_api, users, db):
    """新手机号登录：登录成功，并且在 tb_user 里自动建了一条用户。"""
    user = users.create()

    row = db.one("SELECT id, phone, nick_name FROM tb_user WHERE phone=%s", (user.phone,))
    assert row is not None, f"新手机号 {user.phone} 登录后没有自动注册"
    assert row["id"] == user.user_id
    assert row["nick_name"].startswith("用户")


@allure.feature(FEATURE)
@allure.story("登录")
def test_login_wrong_code(user_api, users, r):
    """验证码错误：business fail，HTTP 仍是 200。"""
    phone = f"{config.TEST_PHONE_PREFIX}0901"
    assert_success(user_api.send_code(phone))
    real_code = r.get(f"login:code:{phone}")
    assert real_code, "前置条件失败：Redis 里没有验证码"

    wrong_code = "000000" if real_code != "000000" else "111111"
    resp = user_api.login(phone, code=wrong_code)
    assert_fail(resp, "验证码错误")


@allure.feature(FEATURE)
@allure.story("登录")
def test_login_missing_code(user_api, users):
    """只传手机号不传验证码：同样返回「验证码错误」，不能登录成功。"""
    phone = f"{config.TEST_PHONE_PREFIX}0902"
    assert_success(user_api.send_code(phone))
    resp = user_api.login(phone)
    assert_fail(resp, "验证码错误")


@allure.feature(FEATURE)
@allure.story("登录")
def test_login_code_expired(user_api, r):
    """验证码过期（Redis key 被删）：登录失败。"""
    phone = f"{config.TEST_PHONE_PREFIX}0903"
    assert_success(user_api.send_code(phone))
    code = r.get(f"login:code:{phone}")
    r.delete(f"login:code:{phone}")

    resp = user_api.login(phone, code=code)
    assert_fail(resp, "验证码错误")


@allure.feature(FEATURE)
@allure.story("登录")
def test_login_code_cannot_be_reused(user_api, r):
    """同一个验证码只能用一次：第二次应该被拒绝。"""
    phone = f"{config.TEST_PHONE_PREFIX}0904"
    assert_success(user_api.send_code(phone))
    code = r.get(f"login:code:{phone}")

    first = user_api.login(phone, code=code)
    second = user_api.login(phone, code=code)

    assert_success(first)
    assert_fail(second, "验证码错误")


@allure.feature(FEATURE)
@allure.story("token")
def test_token_saved_in_redis_with_ttl(user_api, users, r):
    """登录成功后 token 落在 Redis，TTL 约 36000 分钟。"""
    user = users.create()
    raw = r.get(f"login:token:{user.token}")
    assert raw is not None, "Redis 中没有 login:token:{token}"
    ttl = r.ttl(f"login:token:{user.token}")
    assert ttl > 2_000_000, f"token TTL 异常，只有 {ttl} 秒"


@allure.feature(FEATURE)
@allure.story("token")
def test_token_refreshed_on_request(user_api, users, r):
    """每次带 token 请求都会续期：手动把 TTL 改成 60 秒，请求后应恢复到 30 天量级。"""
    user = users.create()
    key = f"login:token:{user.token}"
    r.expire(key, 60)
    assert r.ttl(key) <= 60

    resp = user_api.me(user.token)
    assert_success(resp)

    ttl = r.ttl(key)
    assert ttl > 30_000 * 60, f"token 没有被续期，TTL={ttl}"


@allure.feature(FEATURE)
@allure.story("鉴权")
def test_me_without_token_returns_401(user_api):
    """不带 token 访问受保护接口：HTTP 401。"""
    resp = user_api.me("")
    assert resp.status_code == 401, f"期望 401，实际 {resp.status_code} {resp.text}"


@allure.feature(FEATURE)
@allure.story("鉴权")
def test_me_with_invalid_token_returns_401(user_api):
    """伪造 token：HTTP 401。"""
    resp = user_api.me("not-a-real-token")
    assert resp.status_code == 401


@allure.feature(FEATURE)
@allure.story("鉴权")
@pytest.mark.smoke
def test_me_with_token_returns_current_user(user_api, users):
    """带正确 token：返回当前登录用户。"""
    user = users.create()
    data = assert_success(user_api.me(user.token))
    assert data["id"] == user.user_id


@allure.feature(FEATURE)
@allure.story("鉴权")
def test_token_invalid_after_deleted(user_api, users, r):
    """删除 Redis 里的 token 后，再请求应该 401（模拟过期 / 退出登录）。"""
    user = users.create()
    r.delete(f"login:token:{user.token}")
    resp = user_api.me(user.token)
    assert resp.status_code == 401


@allure.feature(FEATURE)
@allure.story("退出登录")
@pytest.mark.xfail(reason="缺陷：文档写 /user/logout 可用，实际固定返回「功能未完成」", strict=True)
def test_logout_should_work(user_api, users):
    """登出接口应该使 token 失效。"""
    user = users.create()
    assert_success(user_api.logout(user.token))
    assert_true(user_api.me(user.token).status_code == 401, "登出后 token 仍可用")

import pytest
from common.assert_util import assert_fail, assert_success
@pytest.fixture(scope="session")
def token(api,r):
    """获取 token 的 fixture"""
    phone = "13800000002"
    resp = api.post(
        url="/user/code",
        params={"phone": phone}
    )
    code=r.get(f"login:code:{phone}")
    assert code is not None, "Redis 中没有验证码"
    resp = api.post(
        url="/user/login",
        json={"phone": phone, "code": code}
    )
    assert resp.status_code == 200, f"登录请求失败: {resp.status_code} {resp.text}"
    body = resp.json()
    assert body["success"] == True,body
    return body["data"]

def test_withtoken(api,token):
    resp = api.get(
        url="/user/me", 
        headers={"Authorization": token}
    )
    body = resp.json()
    assert body["success"] == True,body
    assert "id" in body["data"]

def test_withouttoken(api,r):
    resp = api.get(
        url="/user/me", 
    )
    assert resp.status_code == 401

def test_login_wrong_code(api, r):
      phone = "13900000030"
      api.post("/user/code", params={"phone": phone})
      real_code = r.get(f"login:code:{phone}")
      assert real_code is not None, "前置条件失败：Redis 里没有验证码"

      wrong_code = "000000" if real_code != "000000" else "111111"
      resp = api.post("/user/login", json={"phone": phone, "code": wrong_code})
      assert_fail(resp, "验证码错误")

@pytest.mark.xfail(
      reason="缺陷#2: 登录成功后不删除验证码，同一验证码 2 分钟内可重复登录",
      strict=True,
  )
def test_login_code_reuse(api, r):
      phone = "13900000031"
      api.post("/user/code", params={"phone": phone})
      code = r.get(f"login:code:{phone}")
      assert code is not None

      first = api.post("/user/login", json={"phone": phone, "code": code})
      second = api.post("/user/login", json={"phone": phone, "code": code})

      assert_success(first)
      assert_fail(second, "验证码错误")      # 期望第二次被拒

def test_token_expired(api, r):
      phone = "13900000032"
      api.post("/user/code", params={"phone": phone})
      code = r.get(f"login:code:{phone}")
      token = assert_success(api.post("/user/login", json={"phone": phone, "code": code}))

      r.delete(f"login:token:{token}")      # 手动让 token 失效

      resp = api.get("/user/me", headers={"authorization": token})
      assert resp.status_code == 401, f"期望 401，实际 {resp.status_code} body={resp.text}"
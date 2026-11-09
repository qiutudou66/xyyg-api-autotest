"""全局 fixture。

这里集中放「多个测试文件都要用的东西」：
- 连接后端 / Redis / MySQL 的客户端；
- 造测试用户、测试店铺、测试优惠券的工厂；
- 整个测试会话开始前 / 结束后清理测试数据；
- AI 服务的 mock。
"""
import itertools
import json
from dataclasses import dataclass

import pytest

from common import config
from common.assert_util import assert_success
from common.cleanup import cleanup_test_data
from common.client import ApiClient, auth_headers
from common.db import DB
from common.mock_ai import MockAI
from common.redis_util import create_redis


@dataclass
class TestUser:
    phone: str
    token: str
    user_id: int
    nickname: str

    @property
    def headers(self):
        return auth_headers(self.token)


class UserFactory:
    """按 1390000xxxx 的手机号段造新用户。

    这个系统「新手机号登录即注册」，所以造用户 = 发验证码 + 读 Redis + 登录。
    """

    def __init__(self, api, r):
        self.api = api
        self.r = r
        self._seq = itertools.count(1)

    def create(self, phone=None):
        phone = phone or f"{config.TEST_PHONE_PREFIX}{next(self._seq):04d}"
        resp = self.api.post("/user/code", params={"phone": phone})
        assert_success(resp)

        code = self.r.get(f"login:code:{phone}")
        assert code, f"Redis 里没有 {phone} 的验证码，发码接口可能没生效"

        resp = self.api.post("/user/login", json={"phone": phone, "code": code})
        token = assert_success(resp)

        raw = self.r.get(f"login:token:{token}")
        assert raw, "登录成功但 Redis 里没有 token"
        dto = json.loads(raw)
        return TestUser(phone=phone, token=token, user_id=dto["id"], nickname=dto.get("nickName", ""))


@pytest.fixture(scope="session")
def api():
    client = ApiClient()
    yield client
    client.close()


@pytest.fixture(scope="session")
def r():
    client = create_redis()
    yield client
    client.close()


@pytest.fixture(scope="session")
def db():
    client = DB()
    yield client
    client.close()


@pytest.fixture(scope="session", autouse=True)
def clean_environment(db, r):
    """整套用例开始前先清残留，结束后再清一次。

    为什么开始前也要清：上一次跑一半失败，数据库里可能留着同名测试数据，
    不清的话这次用例会被脏数据影响（比如「一人一单」直接判定重复）。
    """
    cleanup_test_data(db, r)
    yield
    cleanup_test_data(db, r)


@pytest.fixture(scope="session")
def users(api, r, clean_environment):
    # 显式依赖 clean_environment，保证「先清残留，再造用户」
    return UserFactory(api, r)


@pytest.fixture(scope="session")
def setup_user(users):
    """给「造数据」的 fixture 用，不算业务用例。"""
    return users.create()


@pytest.fixture(scope="session")
def shop_factory(api, setup_user):
    counter = itertools.count(1)

    def create(name=None, type_id=1):
        name = name or f"{config.TEST_NAME_PREFIX}测试店铺{next(counter):03d}"
        payload = {
            "name": name,
            "typeId": type_id,
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
        shop_id = assert_success(api.post("/shop", json=payload, headers=setup_user.headers))
        return shop_id, name

    return create


@pytest.fixture(scope="session")
def voucher_factory(api, setup_user):
    counter = itertools.count(1)

    def create(shop_id, stock=5, begin="2026-01-01T00:00:00", end="2030-01-01T00:00:00", title=None):
        title = title or f"{config.TEST_NAME_PREFIX}秒杀券{next(counter):03d}"
        payload = {
            "shopId": shop_id,
            "title": title,
            "subTitle": "自动化测试用",
            "rules": "仅用于自动化测试",
            "payValue": 100,
            "actualValue": 200,
            "type": 1,
            "status": 1,
            "stock": stock,
            "beginTime": begin,
            "endTime": end,
        }
        voucher_id = assert_success(api.post("/voucher/seckill", json=payload, headers=setup_user.headers))
        return voucher_id, title

    return create


@pytest.fixture(scope="session")
def mock_ai():
    server = MockAI(config.AI_MOCK_HOST, config.AI_MOCK_PORT).start()
    yield server
    server.stop()


# ---------- API 层 fixture：用例里只调业务方法，不直接写 requests ----------
@pytest.fixture(scope="session")
def user_api(api):
    from api.user_api import UserApi

    return UserApi(api)


@pytest.fixture(scope="session")
def shop_api(api):
    from api.shop_api import ShopApi

    return ShopApi(api)


@pytest.fixture(scope="session")
def voucher_api(api):
    from api.voucher_api import VoucherApi

    return VoucherApi(api)


@pytest.fixture(scope="session")
def seckill_api(api):
    from api.seckill_api import SeckillApi

    return SeckillApi(api)


@pytest.fixture(scope="session")
def blog_api(api):
    from api.blog_api import BlogApi

    return BlogApi(api)


@pytest.fixture(scope="session")
def follow_api(api):
    from api.follow_api import FollowApi

    return FollowApi(api)


@pytest.fixture(scope="session")
def upload_api(api):
    from api.upload_api import UploadApi

    return UploadApi(api)


@pytest.fixture(scope="session")
def chat_api(api):
    from api.chat_api import ChatApi

    return ChatApi(api)

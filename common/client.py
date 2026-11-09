"""接口客户端：统一拼 base_url、统一超时、复用连接。

继承 requests.Session 而不是每次 requests.post：
1. 底层 TCP 连接可以复用，几十条用例跑下来快很多；
2. 以后要加统一 header / cookie / 重试，只改这一处。
"""
import requests

from common import config


class ApiClient(requests.Session):
    def __init__(self, base_url: str = None, timeout: int = None):
        super().__init__()
        self.base_url = (base_url or config.BASE_URL).rstrip("/")
        self.timeout = timeout or config.REQUEST_TIMEOUT

    def request(self, method, url, **kwargs):
        # 只写 /user/login 这种相对路径时，自动补上 http://127.0.0.1:8081
        if not url.startswith("http"):
            url = self.base_url + "/" + url.lstrip("/")
        kwargs.setdefault("timeout", self.timeout)
        return super().request(method, url, **kwargs)


def auth_headers(token: str) -> dict:
    """项目约定的鉴权头：authorization: <token>，没有 Bearer 前缀。"""
    return {"authorization": token}

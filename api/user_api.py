"""用户相关接口封装：只负责发请求，不写断言。"""
from common.client import auth_headers


class UserApi:
    def __init__(self, client):
        self.client = client

    def send_code(self, phone):
        return self.client.post("/user/code", params={"phone": phone})

    def login(self, phone, code=None, password=None):
        payload = {"phone": phone}
        if code is not None:
            payload["code"] = code
        if password is not None:
            payload["password"] = password
        return self.client.post("/user/login", json=payload)

    def me(self, token):
        return self.client.get("/user/me", headers=auth_headers(token))

    def logout(self, token):
        return self.client.post("/user/logout", headers=auth_headers(token))

    def get_user(self, user_id, token=None):
        headers = auth_headers(token) if token else None
        return self.client.get(f"/user/{user_id}", headers=headers)

    def info(self, user_id, token=None):
        headers = auth_headers(token) if token else None
        return self.client.get(f"/user/info/{user_id}", headers=headers)

    def sign(self, token):
        return self.client.post("/user/sign", headers=auth_headers(token))

    def sign_count(self, token):
        return self.client.get("/user/sign/count", headers=auth_headers(token))

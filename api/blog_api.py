"""动态（探店笔记）接口封装。"""
from common.client import auth_headers


class BlogApi:
    def __init__(self, client):
        self.client = client

    def save(self, payload, token):
        return self.client.post("/blog", json=payload, headers=auth_headers(token))

    def like(self, blog_id, token):
        return self.client.put(f"/blog/like/{blog_id}", headers=auth_headers(token))

    def my_blogs(self, token, current=1):
        return self.client.get("/blog/of/me", params={"current": current}, headers=auth_headers(token))

    def hot(self, current=1, token=None):
        headers = auth_headers(token) if token else None
        return self.client.get("/blog/hot", params={"current": current}, headers=headers)

    def detail(self, blog_id, token=None):
        headers = auth_headers(token) if token else None
        return self.client.get(f"/blog/{blog_id}", headers=headers)

    def likes(self, blog_id, token=None):
        headers = auth_headers(token) if token else None
        return self.client.get(f"/blog/likes/{blog_id}", headers=headers)

    def by_user(self, user_id, current=1, token=None):
        headers = auth_headers(token) if token else None
        return self.client.get(
            "/blog/of/user",
            params={"user_id": user_id, "current": current},
            headers=headers,
        )

    def follow_feed(self, last_id, offset=0, token=None):
        headers = auth_headers(token) if token else None
        return self.client.get(
            "/blog/of/follow",
            params={"lastId": last_id, "offset": offset},
            headers=headers,
        )

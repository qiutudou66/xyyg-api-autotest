"""关注接口封装。"""
from common.client import auth_headers


class FollowApi:
    def __init__(self, client):
        self.client = client

    def follow(self, target_user_id, is_follow, token):
        return self.client.post(
            f"/follow/{target_user_id}/{str(is_follow).lower()}",
            headers=auth_headers(token),
        )

    def is_follow(self, target_user_id, token):
        return self.client.post(
            f"/follow/or/not/{target_user_id}",
            headers=auth_headers(token),
        )

    def commons(self, other_user_id, token):
        return self.client.get(
            f"/follow/common/{other_user_id}",
            headers=auth_headers(token),
        )

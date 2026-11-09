"""优惠券接口封装。"""
from common.client import auth_headers


class VoucherApi:
    def __init__(self, client):
        self.client = client

    def add(self, payload, token=None):
        headers = auth_headers(token) if token else None
        return self.client.post("/voucher", json=payload, headers=headers)

    def add_seckill(self, payload, token=None):
        headers = auth_headers(token) if token else None
        return self.client.post("/voucher/seckill", json=payload, headers=headers)

    def list_by_shop(self, shop_id):
        return self.client.get(f"/voucher/list/{shop_id}")

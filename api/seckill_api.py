"""秒杀下单接口封装。"""
from common.client import auth_headers


class SeckillApi:
    def __init__(self, client):
        self.client = client

    def seckill(self, voucher_id, token):
        return self.client.post(
            f"/voucher-order/seckill/{voucher_id}",
            headers=auth_headers(token),
        )

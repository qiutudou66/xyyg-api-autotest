"""商铺 / 商铺类型接口封装。"""
from common.client import auth_headers


class ShopApi:
    def __init__(self, client):
        self.client = client

    def list_types(self):
        return self.client.get("/shop-type/list")

    def get(self, shop_id):
        return self.client.get(f"/shop/{shop_id}")

    def create(self, payload, token=None):
        headers = auth_headers(token) if token else None
        return self.client.post("/shop", json=payload, headers=headers)

    def update(self, payload, token=None):
        headers = auth_headers(token) if token else None
        return self.client.put("/shop", json=payload, headers=headers)

    def by_type(self, type_id, current=1, x=None, y=None):
        params = {"typeId": type_id, "current": current}
        if x is not None and y is not None:
            params.update({"x": x, "y": y})
        return self.client.get("/shop/of/type", params=params)

    def by_name(self, name, current=1):
        return self.client.get("/shop/of/name", params={"name": name, "current": current})

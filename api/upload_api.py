"""图片上传接口封装。"""
from common.client import auth_headers


class UploadApi:
    def __init__(self, client):
        self.client = client

    def upload_blog_image(self, file_obj, filename, content_type="image/png", token=None):
        headers = auth_headers(token) if token else None
        return self.client.post(
            "/upload/blog",
            files={"file": (filename, file_obj, content_type)},
            headers=headers,
        )

    def delete_blog_image(self, name, token=None):
        headers = auth_headers(token) if token else None
        return self.client.get("/upload/blog/delete", params={"name": name}, headers=headers)

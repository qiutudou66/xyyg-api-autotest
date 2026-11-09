"""AI 对话接口封装。"""
class ChatApi:
    def __init__(self, client):
        self.client = client

    def chat(self, payload):
        return self.client.post("/chat", json=payload)

    def chat_image(self, file_obj, filename="photo.png", content_type="image/png"):
        return self.client.post(
            "/chat/image",
            files={"file": (filename, file_obj, content_type)},
        )

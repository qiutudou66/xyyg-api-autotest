"""AI 服务 mock。

校园优购的 Java 后端把 AI 请求写死发到 http://localhost:8000/chat。
测试时在这里起一个假的 FastAPI，好处是：
1. 不依赖大模型，不花钱、不受网络影响；
2. 可以精确控制「成功 / 业务失败 / 服务不可用」三种返回；
3. 能记录 Java 到底转发了什么（用来验证历史记录截断等清洗逻辑）。

mock 的是「外部依赖」，不是「被测系统」——被测的 Java 代码仍然真实执行。
"""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class MockAI:
    def __init__(self, host="127.0.0.1", port=8000):
        self.host = host
        self.port = port
        self.state = {
            "mode": "ok",          # ok / fail / down
            "last_chat": None,     # Java 转发过来的 JSON
            "last_image": None,    # Java 转发过来的图片大小 / Content-Type
        }
        self.server = None
        self.thread = None

    def start(self):
        state = self.state

        class Handler(BaseHTTPRequestHandler):
            def _send_json(self, payload, status=200):
                raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_POST(self):
                length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(length)

                if self.path == "/chat":
                    try:
                        state["last_chat"] = json.loads(body.decode("utf-8"))
                    except Exception:
                        state["last_chat"] = {"raw": body.decode("utf-8", "replace")}

                    if state["mode"] == "down":
                        self._send_json({"success": False}, status=500)
                    elif state["mode"] == "fail":
                        self._send_json({"success": False, "message": "mock upstream failure"})
                    else:
                        self._send_json({"success": True, "data": {"answer": "mock-answer"}})
                    return

                if self.path == "/chat-image":
                    state["last_image"] = {
                        "size": len(body),
                        "content_type": self.headers.get("Content-Type", ""),
                    }
                    if state["mode"] == "down":
                        self._send_json({"success": False}, status=500)
                    elif state["mode"] == "fail":
                        self._send_json({"success": False, "message": "mock image failure"})
                    else:
                        self._send_json({"success": True, "data": {"answer": "mock-image-answer"}})
                    return

                self._send_json({"detail": "not found"}, status=404)

            def log_message(self, *args):
                pass  # 不刷屏

        self.server = ThreadingHTTPServer((self.host, self.port), Handler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()

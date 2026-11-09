"""集中管理测试配置。

优先读环境变量，读不到就用本机开发环境的默认值。
这样 CI / 别人电脑上只需要改环境变量，不用改代码。
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# 项目根目录（common/ 的上一级）
ROOT = Path(__file__).resolve().parent.parent

# .env 可选：存在就加载，不存在也不报错
load_dotenv(ROOT / ".env")

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8081")

REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "123456")

MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "123456")
MYSQL_DB = os.getenv("MYSQL_DB", "hmdp")

# 所有测试用户都用这个前缀，清理数据时按前缀删，避免误伤真实用户
TEST_PHONE_PREFIX = os.getenv("TEST_PHONE_PREFIX", "1390000")

# 测试造的店铺 / 优惠券 / 动态统一带这个前缀，方便按前缀清理
TEST_NAME_PREFIX = "AUTOTEST_"

# Java 后端把 AI 请求写死发到 localhost:8000，mock 服务必须监听这个端口
AI_MOCK_HOST = os.getenv("AI_MOCK_HOST", "127.0.0.1")
AI_MOCK_PORT = int(os.getenv("AI_MOCK_PORT", "8000"))

REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "10"))

# 后端 SystemConstants.IMAGE_UPLOAD_DIR 指向的目录，上传用例要验证文件真的落盘
IMAGE_UPLOAD_DIR = os.getenv("IMAGE_UPLOAD_DIR", r"D:\code.java\hm-dianping\frontend\public\imgs")

# 临时文件统一放 E 盘，别占 C 盘
TEST_TEMP_DIR = os.getenv("TEST_TEMP_DIR", r"E:\tmp_hmdp\autotest")

"""MySQL 访问封装。

测试用数据库主要做两件事：
1. 断言异步落库的结果（订单、库存、动态）；
2. 清理测试造出来的数据。
"""
import pymysql
from pymysql.cursors import DictCursor

from common import config


class DB:
    def __init__(self):
        self.conn = pymysql.connect(
            host=config.MYSQL_HOST,
            port=config.MYSQL_PORT,
            user=config.MYSQL_USER,
            password=config.MYSQL_PASSWORD,
            database=config.MYSQL_DB,
            charset="utf8mb4",
            cursorclass=DictCursor,
            autocommit=True,  # 清理数据不需要手动 commit
        )

    def query(self, sql, params=None):
        with self.conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()

    def one(self, sql, params=None):
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def scalar(self, sql, params=None):
        row = self.one(sql, params)
        if not row:
            return None
        return next(iter(row.values()))

    def execute(self, sql, params=None):
        with self.conn.cursor() as cur:
            return cur.execute(sql, params or ())

    def close(self):
        self.conn.close()

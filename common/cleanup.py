"""测试数据清理。

约定：测试制造的数据全部带固定前缀
- 用户手机号：1390000xxxx（config.TEST_PHONE_PREFIX）
- 店铺/优惠券/动态标题：AUTOTEST_xxx（config.TEST_NAME_PREFIX）

清理只认前缀，绝不按「全表清空」处理，避免碰掉真实数据。
"""
import json

from common import config
from common.redis_util import scan_keys


def _ids(rows, key="id"):
    return [row[key] for row in rows]


def _placeholders(values):
    return ",".join(["%s"] * len(values))


def cleanup_test_data(db, r):
    phone_like = config.TEST_PHONE_PREFIX + "%"
    name_like = config.TEST_NAME_PREFIX + "%"

    users = db.query("SELECT id, phone FROM tb_user WHERE phone LIKE %s", (phone_like,))
    user_ids = _ids(users)

    shops = db.query("SELECT id FROM tb_shop WHERE name LIKE %s", (name_like,))
    shop_ids = _ids(shops)

    vouchers = []
    if shop_ids:
        vouchers = db.query(
            f"SELECT id FROM tb_voucher WHERE title LIKE %s OR shop_id IN ({_placeholders(shop_ids)})",
            [name_like] + shop_ids,
        )
    else:
        vouchers = db.query("SELECT id FROM tb_voucher WHERE title LIKE %s", (name_like,))
    voucher_ids = _ids(vouchers)

    blogs = []
    if user_ids:
        blogs = db.query(
            f"SELECT id FROM tb_blog WHERE title LIKE %s OR user_id IN ({_placeholders(user_ids)})",
            [name_like] + user_ids,
        )
    else:
        blogs = db.query("SELECT id FROM tb_blog WHERE title LIKE %s", (name_like,))
    blog_ids = _ids(blogs)

    # 先删子表，再删主表，避免外键 / 逻辑依赖
    if blog_ids:
        ph = _placeholders(blog_ids)
        db.execute(f"DELETE FROM tb_blog_comments WHERE blog_id IN ({ph})", blog_ids)
    if user_ids:
        ph = _placeholders(user_ids)
        db.execute(f"DELETE FROM tb_blog_comments WHERE user_id IN ({ph})", user_ids)
        db.execute(f"DELETE FROM tb_sign WHERE user_id IN ({ph})", user_ids)
        db.execute(f"DELETE FROM tb_user_info WHERE user_id IN ({ph})", user_ids)
        db.execute(
            f"DELETE FROM tb_follow WHERE user_id IN ({ph}) OR follow_user_id IN ({ph})",
            user_ids + user_ids,
        )
    if voucher_ids:
        ph = _placeholders(voucher_ids)
        db.execute(f"DELETE FROM tb_voucher_order WHERE voucher_id IN ({ph})", voucher_ids)
        db.execute(f"DELETE FROM tb_seckill_voucher WHERE voucher_id IN ({ph})", voucher_ids)
        db.execute(f"DELETE FROM tb_voucher WHERE id IN ({ph})", voucher_ids)
    if blog_ids:
        ph = _placeholders(blog_ids)
        db.execute(f"DELETE FROM tb_blog WHERE id IN ({ph})", blog_ids)
    if user_ids:
        ph = _placeholders(user_ids)
        db.execute(f"DELETE FROM tb_user WHERE id IN ({ph})", user_ids)
    if shop_ids:
        ph = _placeholders(shop_ids)
        db.execute(f"DELETE FROM tb_shop WHERE id IN ({ph})", shop_ids)

    # ---------- Redis ----------
    for vid in voucher_ids:
        r.delete(f"seckill:stock:{vid}", f"seckill:order:{vid}")

    for uid in user_ids:
        r.delete(f"follows:{uid}", f"feed:{uid}")
        for key in scan_keys(r, f"sign:{uid}:*"):
            r.delete(key)

    for bid in blog_ids:
        r.delete(f"blog:liked:{bid}", f"feed:done:{bid}")

    # 动态 ID 可能已经被扇出到别人的 feed ZSet 里，按 member 删掉
    if blog_ids:
        for key in scan_keys(r, "feed:*"):
            try:
                if r.type(key) == "zset":
                    r.zrem(key, *[str(bid) for bid in blog_ids])
            except Exception:
                pass

    # 只删测试用户对应的 token / 验证码，别把开发者自己的登录态踢掉。
    # token 里存的是 UserDTO（id/nickName/icon），没有手机号，所以按用户 id 匹配。
    test_id_set = {str(uid) for uid in user_ids}
    for key in scan_keys(r, "login:token:*"):
        try:
            raw = r.get(key)
            if raw and str(json.loads(raw).get("id")) in test_id_set:
                r.delete(key)
        except Exception:
            pass
    for key in scan_keys(r, "login:code:*"):
        if key.split("login:code:", 1)[-1].startswith(config.TEST_PHONE_PREFIX):
            r.delete(key)

    # 测试店铺可能被预热过缓存
    for sid in shop_ids:
        r.delete(f"cache:shop:{sid}")

    return {
        "users": len(user_ids),
        "shops": len(shop_ids),
        "vouchers": len(voucher_ids),
        "blogs": len(blog_ids),
    }

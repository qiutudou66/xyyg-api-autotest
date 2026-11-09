# 缺陷清单

> 全部由自动化用例复现，不是读代码猜的。
> 对应用例用 `pytest.mark.xfail(strict=True)` 标记：缺陷存在时显示 xfailed；
> 哪天修好了，用例会意外通过，strict 模式会报 XPASS，提醒你回来更新用例。

| # | 缺陷 | 复现用例 | 预期 | 实际 |
|---|---|---|---|---|
| 1 | 验证码可重放 | `test_login_code_cannot_be_reused` | 同一验证码第二次登录被拒 | 2 分钟内可重复登录，登录成功后没有删除 `login:code:{phone}` |
| 2 | 手机号正则把逗号当合法字符 | `test_send_code_phone_validation[comma_in_phone]` | `15,00000000` 判为非法 | 返回成功；正则 `5[0-3,5-9]` 中的逗号被当成字符 |
| 3 | 登出接口与文档不一致 | `test_logout_should_work` | 登出成功且 token 失效 | 固定返回 `success=false, errorMsg="功能未完成"`，OpenAPI 却写 200 OK |
| 4 | 签到天数永远为 0 | `test_sign_count_after_sign` | 签到 1 天后返回 1 | 返回 0；代码 `if(result != null) return Result.ok(0)` 写反了 |
| 5 | 秒杀不存在的券返回「服务器异常」 | `test_seckill_nonexistent_voucher` | 「优惠券不存在」 | Lua 对 `nil` 做比较抛错，被全局兜底成「服务器异常」 |
| 6 | 秒杀不校验时间窗口 | `test_seckill_expired_voucher_should_fail`、`test_seckill_not_started_voucher_should_fail` | 过期/未开始的券不能抢 | 都能抢成功并生成订单 |
| 7 | 新增秒杀券不校验库存 | `test_add_seckill_voucher_without_stock`、`test_add_seckill_voucher_with_negative_stock` | 返回可读的参数错误 | 不传 stock 触发 NPE → 「服务器异常」；负数直接入库 |
| 8 | 新增秒杀券不校验时间先后 | `test_add_seckill_voucher_with_reversed_time` | 开始时间必须早于结束时间 | 时间倒置也能创建成功 |
| 9 | 写接口鉴权缺失 | `test_create_shop_without_token_should_401`、`test_add_voucher_without_token_should_401`、`test_upload_without_token_should_401` | 未登录返回 401 | 未登录也能新增店铺、发券、上传图片 |
| 10 | 上传不校验文件类型 | `test_upload_txt_should_be_rejected` | 只允许图片 | `.txt` 也能上传成功 |
| 11 | 超大文件错误不可读 | `test_upload_too_large`、`test_chat_image_too_large` | 「文件大小不能超过 10MB」 | 被 Spring multipart 限制拦下后兜底成「服务器异常」 |
| 12 | 重复关注不幂等 | `test_follow_twice_is_idempotent` | 同一个人只能关注一次 | `tb_follow` 没有唯一索引，插入了两条 |
| 13 | 关注自己 / 关注不存在的用户 | `test_cannot_follow_self`、`test_follow_nonexistent_user` | 拒绝并给出提示 | 都返回成功 |
| 14 | 空动态可以发布 | `test_publish_blog_with_empty_content_should_fail` | 「内容不能为空」 | 空字符串也能入库 |
| 15 | 给不存在的动态点赞返回成功 | `test_like_nonexistent_blog_should_fail` | 「博客不存在」 | 返回 `success=true` |

统计：21 条 xfail 用例，归为 15 类缺陷。

## 面试挑哪三个讲

优先讲业务影响大、能说清定位过程的：

1. **秒杀不校验时间窗口**：过期券还能抢，直接影响钱和库存。
2. **写接口鉴权缺失**：未登录能发券、传图，属于接口设计问题。
3. **签到天数永远为 0**：逻辑写反，简单但很典型，能体现你看得懂代码。

不要把它包装成「高危漏洞」「生产事故」。这是个人项目，诚实说「设计缺陷 / 校验缺失」。

# 校园优购 · 接口自动化测试

被测系统：`D:\code.java\hm-dianping`（校园优购，Spring Boot + MySQL + Redis + RabbitMQ）。

本仓库只放测试代码，不改被测系统。

## 快速运行

```bash
# 1. 启动被测系统（MySQL、Redis、RabbitMQ 要先起）
#    后端监听 8081；Redis/RabbitMQ 在 WSL 里时用 127.0.0.1（localhost 转发）
cd /d/code.java/hm-dianping
REDIS_HOST=127.0.0.1 RABBITMQ_HOST=127.0.0.1 mvn -q spring-boot:run

# 2. 安装依赖
./.venv/Scripts/python.exe -m pip install -r requirements.txt

# 3. 跑全部用例
./.venv/Scripts/python.exe -m pytest

# 4. 看报告
# HTML: reports/report.html（双击即可）
# Allure 原始结果: reports/allure-results（需要另装 allure-commandline 才能 serve）
```

如果 Redis / MySQL 不在默认地址，复制 `.env.example` 为 `.env` 后修改。
`.env` 已被 `.gitignore` 忽略，不要提交。

## 目录说明

```
hmdp-autotest/
├─ api/            接口封装层：一个模块一个文件，只发请求，不写断言
├─ common/         公共组件：客户端、断言、等待、DB、Redis、清理、AI mock
├─ data/           YAML 测试数据，用例与数据分离
├─ testcase/       用例层：只写业务逻辑和断言
├─ conftest.py     全局 fixture：连接、造数据、清理
├─ pytest.ini      测试配置
├─ legacy/         M1 阶段的旧用例，仅留作记录，不参与自动收集
└─ requirements.txt
```

分层原则：

- `api/` 只负责「怎么发请求」；
- `testcase/` 只负责「断言什么」；
- `common/` 提供可复用的基础设施；
- 测试数据统一带前缀（用户 `1390000xxxx`，名称 `AUTOTEST_`），会话开始和结束各清理一次。

## 测试范围

| 模块 | 覆盖内容 |
|---|---|
| 登录 | 发码、手机号边界、验证码错误/过期/重放、token 保存与续期、401 |
| 用户 | 当前用户、用户查询、资料详情、签到 bitmap、签到天数 |
| 商铺 | 类型列表与缓存、详情缓存、按类型/距离/名称查询、新增、更新、鉴权 |
| 优惠券 | 普通券、秒杀券、库存写 Redis、下架券过滤、参数校验 |
| 秒杀 | 正常下单、重复下单、库存耗尽、过期/未开始、并发 10 抢 5、三方一致、唯一索引 |
| 动态 | 发布、详情、热门、点赞/取消、我的动态、关注流（RabbitMQ 异步） |
| 关注 | 关注、取关、是否关注、共同关注、重复关注、边界 |
| 上传 | 上传/删除、未登录、非法类型、超大文件 |
| AI | 文本对话、参数校验、历史清洗、上游失败/不可用、图片识别（本地 mock） |

## 已知缺陷

部分用例用 `pytest.mark.xfail(strict=True)` 标记「期望正确行为、实际是缺陷」。
这些用例在报告里显示为 xfailed，不是失败；缺陷详情见 [`docs/DEFECTS.md`](docs/DEFECTS.md)。

# 校园优购 · 接口自动化测试

[![API 自动化测试](https://github.com/qiutudou66/xyyg-api-autotest/actions/workflows/ci.yml/badge.svg)](https://github.com/qiutudou66/xyyg-api-autotest/actions/workflows/ci.yml)

被测系统：[campus-yougou](https://github.com/qiutudou66/campus-yougou)（Spring Boot + MySQL + Redis + RabbitMQ）。

| 指标 | 数值 |
|---|---|
| 用例数 | 106（83 passed + 16 xfailed + 参数化展开） |
| 接口覆盖 | 33 / 33（口径见 [`docs/接口覆盖矩阵.md`](docs/接口覆盖矩阵.md)） |
| 本地全量耗时 | 约 6 秒 |
| CI | push 跑冒烟，每天定时跑全量，报告作为 artifact 上传 |

## 快速运行

### 方式一：Docker 起中间件（推荐）

```bash
docker compose up -d

# 首次启动后导入初始化数据
docker exec -i hmdp-mysql mysql -uroot -p123456 hmdp \
  < ../hm-dianping/src/main/resources/db/hmdp.sql
```

### 方式二：已有 MySQL / Redis / RabbitMQ

复制 `.env.example` 为 `.env`，按自己的环境改地址和密码。`.env` 已被 `.gitignore` 忽略。

### 启动被测系统并跑测试

```bash
# 1. 启动后端（监听 8081）
cd ../hm-dianping
mvn -q spring-boot:run

# 2. 安装依赖并跑用例
cd ../hmdp-autotest
./.venv/Scripts/python.exe -m pip install -r requirements.txt
./.venv/Scripts/python.exe -m pytest

# 3. 看报告
# HTML：reports/report.html
# Allure：reports/allure-results（需要 allure-commandline 才能 serve）
```

## 分组执行

```bash
pytest -m smoke     # 核心链路，CI 每次 push 跑这组
pytest -m slow      # 并发、RabbitMQ 异步、大文件
pytest -m "not slow"  # 排除慢用例
```

可用 marker 在 `pytest.ini` 里声明：

- `smoke`：登录、商铺、优惠券、秒杀下单、动态、关注、上传的核心路径，22 条（含参数化展开）；
- `slow`：10 并发抢券、RabbitMQ 异步扇出、超大文件上传。

## 目录说明

```
hmdp-autotest/
├─ api/            接口封装层：一个模块一个文件，只发请求，不写断言
├─ common/         公共组件：客户端、断言、等待、DB、Redis、清理、AI mock
├─ data/           YAML 测试数据，用例与数据分离
├─ testcase/       用例层：只写业务逻辑和断言
├─ docs/           缺陷清单、接口覆盖矩阵
├─ .github/        GitHub Actions CI
├─ conftest.py     全局 fixture：连接、造数据、清理
├─ docker-compose.yml  本地一键起 MySQL / Redis / RabbitMQ
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

接口级明细（每个接口对应哪些用例、哪些没覆盖）见 [`docs/接口覆盖矩阵.md`](docs/接口覆盖矩阵.md)。

## 缺陷管理

用例用 `pytest.mark.xfail(strict=True)` 标记「期望正确行为、实际是缺陷」：

- 缺陷存在时显示 **xfailed**，不影响流水线；
- 缺陷修好后用例会意外通过，strict 模式报 **XPASS**，提醒回来把用例改成正常断言。

当前共 15 类缺陷，**已修复 5 类**并转为回归用例：

| 缺陷 | 修复位置 |
|---|---|
| 签到天数永远为 0 | `UserServiceImpl.signCount()` 判空逻辑写反 |
| 验证码可重放 | `UserServiceImpl.login()` 校验通过后删除 Redis key |
| 手机号正则把逗号当合法字符 | `RegexPatterns.PHONE_REGEX` 的 `5[0-3,5-9]` 改为 `5[0-35-9]` |
| 空动态可以发布 | `BlogServiceImpl.saveBlog()` 增加空内容校验 |
| 给不存在的动态点赞返回成功 | `BlogServiceImpl.likeBlog()` 先校验动态存在 |

剩余 10 类见 [`docs/DEFECTS.md`](docs/DEFECTS.md)。

## 已知限制

- **暂不支持并行执行**。`conftest.py` 里的造数 factory、`itertools.count` 计数器和会话级清理都依赖单进程状态，直接开 `pytest-xdist -n auto` 会让不同 worker 抢同一批测试数据。改造方向：每个 worker 分配独立手机号段、清理逻辑按前缀隔离。
- **接口覆盖率 100% 不等于逻辑覆盖 100%**，未覆盖维度（越权、并发极限、MQ 丢消息、安全扫描等）列在覆盖矩阵文末。
- **用例不能依赖开发库残留数据**。干净环境（CI）第一次跑通前踩过两个坑：详情接口的「逻辑过期」方案要求缓存预热，而本地 Redis 早被前端请求预热过；秒杀券 10 号是开发库里手工加的，初始化 SQL 里只有一张普通券。现在分别用 `warm_shop_cache` fixture（调一次 PUT 触发写缓存）和 `voucher_factory`（用例自己造券）消除，整套用例在空库 + 空 Redis 上可复现。
- **docker-compose 未在本机验证**：开发机没有装 Docker，CI 用的是 GitHub Actions service containers 的等价配置。

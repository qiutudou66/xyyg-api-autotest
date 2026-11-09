"""AI 对话用例。

Java 后端只是转发方，真正的 AI 能力在 Python FastAPI。
测试用 mock 服务替换外部依赖：
- 控制变量：能稳定制造「成功 / 业务失败 / 服务不可用」；
- 成本为零：不调用大模型，不受网络和 key 影响；
- 能验证转发逻辑：mock 记录 Java 清洗后的 history，测试再断言。
"""
from pathlib import Path

import allure
import pytest

from common import config
from common.assert_util import assert_fail, assert_success

FEATURE = "AI 助手"

TINY_PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64


@pytest.fixture(autouse=True)
def reset_mock(mock_ai):
    """每条用例开始前把 mock 恢复成默认状态，避免用例之间互相影响。"""
    mock_ai.state["mode"] = "ok"
    mock_ai.state["last_chat"] = None
    mock_ai.state["last_image"] = None
    yield


@pytest.fixture
def png_file(tmp_path):
    path = Path(config.TEST_TEMP_DIR)
    path.mkdir(parents=True, exist_ok=True)
    file_path = path / "chat_autotest.png"
    file_path.write_bytes(TINY_PNG)
    yield file_path
    file_path.unlink(missing_ok=True)


@allure.feature(FEATURE)
@allure.story("文本对话")
def test_chat_success(chat_api, mock_ai):
    data = assert_success(chat_api.chat({"question": "学校附近有什么好吃的"}))
    assert data == "mock-answer"
    assert mock_ai.state["last_chat"]["question"] == "学校附近有什么好吃的"
    assert mock_ai.state["last_chat"]["history"] == []


@allure.feature(FEATURE)
@allure.story("参数校验")
def test_chat_empty_question(chat_api):
    assert_fail(chat_api.chat({"question": ""}), "问题不能为空")


@allure.feature(FEATURE)
@allure.story("参数校验")
def test_chat_blank_question(chat_api):
    assert_fail(chat_api.chat({"question": "   "}), "问题不能为空")


@allure.feature(FEATURE)
@allure.story("参数校验")
def test_chat_without_body(api):
    assert_fail(api.post("/chat"), "问题不能为空")


@allure.feature(FEATURE)
@allure.story("历史记录清洗")
def test_history_is_filtered_truncated_and_limited(chat_api, mock_ai):
    valid = []
    for i in range(4):
        valid.append({"role": "user", "content": f"问题{i}"})
        valid.append({"role": "assistant", "content": f"回答{i}"})

    long_content = "x" * 3000
    payload = {
        "question": "现在的问题",
        "history": valid
        + [
            {"role": "system", "content": "不该被转发"},
            {"role": "user", "content": "   "},
            {"role": "user", "content": long_content},
        ],
    }
    assert_success(chat_api.chat(payload))

    forwarded = mock_ai.state["last_chat"]["history"]
    assert len(forwarded) == 6, f"最多保留 6 条历史，实际 {len(forwarded)}"
    assert all(item["role"] in ("user", "assistant") for item in forwarded)
    assert all(item["content"].strip() for item in forwarded)
    assert all(len(item["content"]) <= 2000 for item in forwarded)

    # 过滤后顺序是 valid 的 8 条 + 超长内容，取最后 6 条
    assert forwarded[0] == valid[3]
    assert forwarded[-1]["content"] == "x" * 2000


@allure.feature(FEATURE)
@allure.story("上游异常")
def test_ai_business_failure(chat_api, mock_ai):
    mock_ai.state["mode"] = "fail"
    assert_fail(chat_api.chat({"question": "hi"}), "AI 服务处理失败：mock upstream failure")


@allure.feature(FEATURE)
@allure.story("上游异常")
def test_ai_service_down(chat_api, mock_ai):
    mock_ai.state["mode"] = "down"
    assert_fail(chat_api.chat({"question": "hi"}), "AI 服务暂时不可用，请稍后再试")


@allure.feature(FEATURE)
@allure.story("图片识别")
def test_chat_image_success(chat_api, mock_ai, png_file):
    with open(png_file, "rb") as f:
        data = assert_success(chat_api.chat_image(f, "chat_autotest.png"))
    assert data == "mock-image-answer"
    assert mock_ai.state["last_image"]["content_type"].startswith("multipart/form-data")


@allure.feature(FEATURE)
@allure.story("图片识别")
def test_chat_image_empty(chat_api):
    assert_fail(chat_api.chat_image(b"", "empty.png"), "图片不能为空")


@allure.feature(FEATURE)
@allure.story("图片识别")
def test_chat_image_upstream_failure(chat_api, mock_ai, png_file):
    mock_ai.state["mode"] = "fail"
    with open(png_file, "rb") as f:
        resp = chat_api.chat_image(f, "chat_autotest.png")
    assert_fail(resp, "AI 服务处理失败：mock image failure")


@allure.feature(FEATURE)
@allure.story("图片识别")
@pytest.mark.xfail(reason="缺陷：超过 10MB 被 multipart 限制拦下，错误被兜底成「服务器异常」", strict=True)
@pytest.mark.slow
def test_chat_image_too_large(chat_api, tmp_path):
    big = Path(config.TEST_TEMP_DIR) / "chat_big.png"
    big.parent.mkdir(parents=True, exist_ok=True)
    big.write_bytes(b"0" * (11 * 1024 * 1024))
    try:
        with open(big, "rb") as f:
            resp = chat_api.chat_image(f, "chat_big.png")
        assert_fail(resp, "图片不能超过 10MB")
    finally:
        big.unlink(missing_ok=True)

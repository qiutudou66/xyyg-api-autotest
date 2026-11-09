"""图片上传用例。

真实行为（读代码确认）：
- 上传目录是后端 SystemConstants.IMAGE_UPLOAD_DIR 写死的 Windows 路径；
- 接口不校验文件后缀，任何类型都能传；
- /upload/** 被排除在登录拦截外，未登录也能传、也能删；
- 超过 10MB 会被 Spring 的 multipart 限制拦下，但错误被兜底成「服务器异常」。
"""
from pathlib import Path

import allure
import pytest

from common import config
from common.assert_util import assert_fail, assert_success

FEATURE = "图片上传"

# 最小 PNG 文件头，足够让后端按文件名后缀存盘
TINY_PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64


@pytest.fixture(scope="module")
def upload_dir():
    Path(config.TEST_TEMP_DIR).mkdir(parents=True, exist_ok=True)
    return Path(config.TEST_TEMP_DIR)


@pytest.fixture
def png_file(upload_dir):
    path = upload_dir / "autotest.png"
    path.write_bytes(TINY_PNG)
    yield path
    path.unlink(missing_ok=True)


@pytest.fixture
def txt_file(upload_dir):
    path = upload_dir / "autotest.txt"
    path.write_bytes(b"not an image")
    yield path
    path.unlink(missing_ok=True)


@pytest.fixture
def big_png(upload_dir):
    path = upload_dir / "autotest_big.png"
    path.write_bytes(b"0" * (11 * 1024 * 1024))
    yield path
    path.unlink(missing_ok=True)


def _disk_path(relative_name):
    return Path(config.IMAGE_UPLOAD_DIR) / relative_name.lstrip("/")


@allure.feature(FEATURE)
@allure.story("上传图片")
@pytest.mark.smoke
def test_upload_png(upload_api, png_file):
    with open(png_file, "rb") as f:
        name = assert_success(upload_api.upload_blog_image(f, "autotest.png"))

    assert name.endswith(".png")
    assert _disk_path(name).exists(), f"接口返回了 {name}，但磁盘上没有文件"

    # 用例自己收尾，避免在真实上传目录里留垃圾
    assert_success(upload_api.delete_blog_image(name))


@allure.feature(FEATURE)
@allure.story("上传图片")
def test_delete_uploaded_image(upload_api, png_file):
    with open(png_file, "rb") as f:
        name = assert_success(upload_api.upload_blog_image(f, "autotest.png"))
    path = _disk_path(name)
    assert path.exists()

    assert_success(upload_api.delete_blog_image(name))
    assert not path.exists(), "删除接口返回成功，但文件还在"


@allure.feature(FEATURE)
@allure.story("删除图片")
def test_delete_directory_is_rejected(upload_api):
    assert_fail(upload_api.delete_blog_image("blogs"), "错误的文件名称")


@allure.feature(FEATURE)
@allure.story("鉴权")
@pytest.mark.xfail(reason="缺陷：/upload/** 被排除在登录拦截之外，未登录也能上传图片", strict=True)
def test_upload_without_token_should_401(upload_api, png_file):
    with open(png_file, "rb") as f:
        resp = upload_api.upload_blog_image(f, "autotest.png")
    assert resp.status_code == 401


@allure.feature(FEATURE)
@allure.story("文件类型")
@pytest.mark.xfail(reason="缺陷：上传不校验文件类型，.txt 也能当图片上传", strict=True)
def test_upload_txt_should_be_rejected(upload_api, txt_file):
    with open(txt_file, "rb") as f:
        resp = upload_api.upload_blog_image(f, "autotest.txt", content_type="text/plain")
    body = resp.json()
    if body.get("success") is True:
        # 失败时也要把文件删掉，别留垃圾
        upload_api.delete_blog_image(body["data"])
    assert_fail(resp, "只能上传图片")


@allure.feature(FEATURE)
@allure.story("文件大小")
@pytest.mark.xfail(
    reason="缺陷：超过 10MB 被兜底成「服务器异常」，没有可读的文件大小提示",
    strict=True,
)
@pytest.mark.slow
def test_upload_too_large(upload_api, big_png):
    with open(big_png, "rb") as f:
        resp = upload_api.upload_blog_image(f, "autotest_big.png")
    assert_fail(resp, "文件大小不能超过 10MB")

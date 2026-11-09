"""统一断言器。

这个项目的后端约定：业务失败时 HTTP 仍然是 200，靠响应体里的 success 判断。
所以不能只断言状态码，必须同时看 success / errorMsg。
"""
import allure


def _attach(resp):
    """断言失败时把请求和响应挂到 Allure 报告里，排查问题不用再翻日志。"""
    try:
        allure.attach(
            f"{resp.request.method} {resp.url}\n\n{resp.request.body or ''}",
            name="请求",
            attachment_type=allure.attachment_type.TEXT,
        )
        allure.attach(resp.text[:2000], name="响应", attachment_type=allure.attachment_type.TEXT)
    except Exception:
        # 报告只是辅助，不能因为挂附件失败把测试本身搞挂
        pass


def assert_status(resp, expected=200):
    """断言 HTTP 状态码。"""
    if resp.status_code != expected:
        _attach(resp)
        raise AssertionError(
            f"\n URL: {resp.request.method} {resp.url}"
            f"\n 期望状态码: {expected}"
            f"\n 实际状态码: {resp.status_code}"
            f"\n 响应体: {resp.text[:500]}"
        )
    return resp


def assert_success(resp):
    """断言 HTTP 200 且 success=True，返回 data 字段。"""
    assert_status(resp, 200)
    body = resp.json()
    if "success" not in body:
        _attach(resp)
        raise AssertionError(f"响应体中没有 success 字段: {body}")
    if body.get("success") is not True:
        _attach(resp)
        raise AssertionError(
            f"\n URL: {resp.request.method} {resp.url}"
            f"\n 期望: success=True"
            f"\n 实际: success={body.get('success')}, errorMsg={body.get('errorMsg')!r}"
        )
    return body.get("data")


def assert_fail(resp, expected_msg=None):
    """断言 HTTP 200 且 success=False；给了 expected_msg 时再比错误文案。"""
    assert_status(resp, 200)
    body = resp.json()
    if body.get("success") is not False:
        _attach(resp)
        raise AssertionError(
            f"\n URL: {resp.request.method} {resp.url}"
            f"\n 期望: success=False"
            f"\n 实际: {body}"
        )
    actual_msg = body.get("errorMsg")
    if expected_msg is not None and actual_msg != expected_msg:
        _attach(resp)
        raise AssertionError(
            f"\n URL: {resp.request.method} {resp.url}"
            f"\n 期望 errorMsg: {expected_msg!r}"
            f"\n 实际 errorMsg: {actual_msg!r}"
        )
    return actual_msg


def assert_true(condition, message):
    """普通布尔断言，失败时把 message 原样抛出来。"""
    if not condition:
        raise AssertionError(message)

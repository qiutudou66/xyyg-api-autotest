
import pytest

from common.assert_util import assert_status
@pytest.mark.parametrize(
    "phone, expected_success",
    [
        ("13800000002", True),
        ("1380000000", False),
        ("138000000044", False),
        ("12800000004", False),
        ("1380000000a", False),
        ("", False),
        pytest.param(
            "15,00000000",
            False,
            marks=pytest.mark.xfail(
                reason="缺陷：正则5[0-3,5-9]逗号被当做数字处理",
                strict=True,
            ),
        ),
    ],
    ids=[
        "truenum",
        "tooshort",
        "toolong",
        "firstnumerror",
        "containletter",
        "emptynum",
        "invalidformat",
    ]
)
def test_send_code_phone_validation(api,phone, expected_success):
    """手机号校验"""
    resp = api.post(
        url="/user/code",
        params={"phone": phone}
    )
    assert_status(resp, 200)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body.get("success") is expected_success,body

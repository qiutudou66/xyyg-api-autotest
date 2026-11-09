import requests
from common.assert_util import assert_status

resp = requests.get("http://127.0.0.1:8081/user/me")
assert_status(resp, 999)
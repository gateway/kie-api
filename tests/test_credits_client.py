import httpx

from kie_api.clients.credits import CreditsClient
from kie_api.config import KieSettings


def test_credits_client_normalizes_primary_credit_endpoint() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/chat/credit"
        return httpx.Response(
            200,
            json={"code": 200, "msg": "success", "data": {"remainingCredits": 123.5}},
        )

    client = CreditsClient(
        KieSettings(api_key="test-key"),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    result = client.get_balance()

    assert result.success is True
    assert result.balance_available is True
    assert result.available_credits == 123.5
    assert result.endpoint_path == "/api/v1/chat/credit"


def test_credits_client_falls_back_when_primary_endpoint_is_missing() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/chat/credit":
            return httpx.Response(404, json={"code": 404, "msg": "not found"})
        return httpx.Response(
            200,
            json={"code": 200, "msg": "success", "data": {"credits": "42", "unit": "credits"}},
        )

    client = CreditsClient(
        KieSettings(api_key="test-key"),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    result = client.get_balance()

    assert result.success is True
    assert result.balance_available is True
    assert result.available_credits == 42.0
    assert result.endpoint_path == "/api/v1/user/credits"

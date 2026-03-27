from kie_api.config import KieSettings


def test_settings_load_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("KIE_API_KEY", "env-key")
    monkeypatch.setenv("KIE_MARKET_BASE_URL", "https://api.example.test")
    monkeypatch.setenv("KIE_UPLOAD_BASE_URL", "https://upload.example.test")
    monkeypatch.setenv("KIE_WEBHOOK_SECRET", "secret")
    monkeypatch.setenv("KIE_CONNECT_TIMEOUT_SECONDS", "3")
    monkeypatch.setenv("KIE_READ_TIMEOUT_SECONDS", "7")
    monkeypatch.setenv("KIE_UPLOAD_READ_TIMEOUT_SECONDS", "15")
    monkeypatch.setenv("KIE_WARN_CREDIT_THRESHOLD", "4")
    monkeypatch.setenv("KIE_CONFIRM_CREDIT_THRESHOLD", "9")

    settings = KieSettings.from_env()

    assert settings.api_key == "env-key"
    assert settings.market_base_url == "https://api.example.test"
    assert settings.upload_base_url == "https://upload.example.test"
    assert settings.webhook_secret == "secret"
    assert settings.json_timeout().connect == 3
    assert settings.json_timeout().read == 7
    assert settings.upload_timeout().read == 15
    assert settings.warn_credit_threshold == 4
    assert settings.confirm_credit_threshold == 9


def test_settings_allow_explicit_injection() -> None:
    settings = KieSettings(api_key="injected", webhook_secret="hook-secret")

    assert settings.api_key == "injected"
    assert settings.webhook_secret == "hook-secret"

"""Runtime configuration for KIE.AI clients."""

from __future__ import annotations

import os
from typing import Dict, List, Optional

import httpx
from pydantic import BaseModel, ConfigDict, Field


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    return float(value) if value is not None else default


def _env_csv(name: str, default: str) -> List[str]:
    value = os.getenv(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


class KieSettings(BaseModel):
    """Settings for talking to KIE APIs."""

    model_config = ConfigDict(extra="ignore")

    api_key: Optional[str] = Field(default_factory=lambda: os.getenv("KIE_API_KEY"))
    market_base_url: str = Field(
        default_factory=lambda: os.getenv("KIE_MARKET_BASE_URL", "https://api.kie.ai")
    )
    upload_base_url: str = Field(
        default_factory=lambda: os.getenv("KIE_UPLOAD_BASE_URL", "https://kieai.redpandaai.co")
    )
    webhook_secret: Optional[str] = Field(default_factory=lambda: os.getenv("KIE_WEBHOOK_SECRET"))
    create_task_path: str = Field(
        default_factory=lambda: os.getenv("KIE_CREATE_TASK_PATH", "/api/v1/jobs/createTask")
    )
    status_path: str = Field(
        default_factory=lambda: os.getenv("KIE_STATUS_PATH", "/api/v1/jobs/recordInfo")
    )
    credits_path: str = Field(
        default_factory=lambda: os.getenv("KIE_CREDITS_PATH", "/api/v1/chat/credit")
    )
    credit_fallback_paths: List[str] = Field(
        default_factory=lambda: _env_csv("KIE_CREDIT_FALLBACK_PATHS", "/api/v1/user/credits")
    )
    upload_stream_path: str = Field(
        default_factory=lambda: os.getenv("KIE_UPLOAD_STREAM_PATH", "/api/file-stream-upload")
    )
    upload_url_path: str = Field(
        default_factory=lambda: os.getenv("KIE_UPLOAD_URL_PATH", "/api/file-url-upload")
    )
    upload_base64_path: str = Field(
        default_factory=lambda: os.getenv("KIE_UPLOAD_BASE64_PATH", "/api/file-base64-upload")
    )
    upload_default_path: str = Field(
        default_factory=lambda: os.getenv("KIE_UPLOAD_DEFAULT_PATH", "images/user-uploads")
    )
    trusted_uploaded_media_hosts: List[str] = Field(
        default_factory=lambda: _env_csv(
            "KIE_TRUSTED_UPLOADED_MEDIA_HOSTS",
            "tempfile.redpandaai.co,kieai.redpandaai.co",
        )
    )
    connect_timeout_seconds: float = Field(
        default_factory=lambda: _env_float("KIE_CONNECT_TIMEOUT_SECONDS", 10.0)
    )
    read_timeout_seconds: float = Field(
        default_factory=lambda: _env_float("KIE_READ_TIMEOUT_SECONDS", 60.0)
    )
    write_timeout_seconds: float = Field(
        default_factory=lambda: _env_float("KIE_WRITE_TIMEOUT_SECONDS", 60.0)
    )
    pool_timeout_seconds: float = Field(
        default_factory=lambda: _env_float("KIE_POOL_TIMEOUT_SECONDS", 10.0)
    )
    upload_read_timeout_seconds: float = Field(
        default_factory=lambda: _env_float("KIE_UPLOAD_READ_TIMEOUT_SECONDS", 120.0)
    )
    warn_credit_threshold: Optional[float] = Field(
        default_factory=lambda: (
            float(os.getenv("KIE_WARN_CREDIT_THRESHOLD"))
            if os.getenv("KIE_WARN_CREDIT_THRESHOLD")
            else None
        )
    )
    confirm_credit_threshold: Optional[float] = Field(
        default_factory=lambda: (
            float(os.getenv("KIE_CONFIRM_CREDIT_THRESHOLD"))
            if os.getenv("KIE_CONFIRM_CREDIT_THRESHOLD")
            else None
        )
    )
    warn_cost_usd_threshold: Optional[float] = Field(
        default_factory=lambda: (
            float(os.getenv("KIE_WARN_COST_USD_THRESHOLD"))
            if os.getenv("KIE_WARN_COST_USD_THRESHOLD")
            else None
        )
    )
    confirm_cost_usd_threshold: Optional[float] = Field(
        default_factory=lambda: (
            float(os.getenv("KIE_CONFIRM_COST_USD_THRESHOLD"))
            if os.getenv("KIE_CONFIRM_COST_USD_THRESHOLD")
            else None
        )
    )
    wait_poll_interval_seconds: float = Field(
        default_factory=lambda: _env_float("KIE_WAIT_POLL_INTERVAL_SECONDS", 20.0)
    )
    wait_timeout_seconds: float = Field(
        default_factory=lambda: _env_float("KIE_WAIT_TIMEOUT_SECONDS", 900.0)
    )

    @classmethod
    def from_env(cls) -> "KieSettings":
        return cls()

    def auth_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def json_timeout(self) -> httpx.Timeout:
        return httpx.Timeout(
            connect=self.connect_timeout_seconds,
            read=self.read_timeout_seconds,
            write=self.write_timeout_seconds,
            pool=self.pool_timeout_seconds,
        )

    def upload_timeout(self) -> httpx.Timeout:
        return httpx.Timeout(
            connect=self.connect_timeout_seconds,
            read=self.upload_read_timeout_seconds,
            write=self.write_timeout_seconds,
            pool=self.pool_timeout_seconds,
        )

    def is_trusted_uploaded_url(self, value: str) -> bool:
        host = httpx.URL(value).host
        if not host:
            return False
        return any(
            host == trusted_host or host.endswith(f".{trusted_host}")
            for trusted_host in self.trusted_uploaded_media_hosts
        )

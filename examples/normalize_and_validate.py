"""Normalize and validate a local request without hitting KIE."""

from kie_api import normalize_request, validate_request
from kie_api.models import RawUserRequest


def main() -> None:
    raw_request = RawUserRequest(
        model_key="kling-3.0",
        prompt="a portrait subject turning toward camera",
        images=["https://example.com/start.png"],
        options={"duration": 5, "mode": "pro"},
    )
    normalized = normalize_request(raw_request)
    result = validate_request(normalized)
    print(result.model_dump())


if __name__ == "__main__":
    main()

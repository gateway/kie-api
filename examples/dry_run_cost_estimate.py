"""Estimate request cost from the local pricing snapshot without any API key."""

from kie_api import estimate_request_cost
from kie_api.models import RawUserRequest


def main() -> None:
    estimate = estimate_request_cost(
        RawUserRequest(
            model_key="kling-3.0-t2v",
            prompt="A polished commercial shot of a product reveal.",
            options={"duration": 10, "mode": "pro", "sound": True},
        )
    )
    print(estimate.model_dump())


if __name__ == "__main__":
    main()

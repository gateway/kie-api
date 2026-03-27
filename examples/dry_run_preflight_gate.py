"""Show warning and confirmation behavior using the dry-run preflight gate."""

from kie_api import run_preflight
from kie_api.config import KieSettings
from kie_api.models import RawUserRequest


def main() -> None:
    request = RawUserRequest(
        model_key="kling-3.0-t2v",
        prompt="A polished commercial shot of a product reveal.",
        options={"duration": 10, "mode": "pro", "sound": True},
    )

    decision = run_preflight(
        request,
        settings=KieSettings(
            warn_credit_threshold=15,
            confirm_credit_threshold=25,
        ),
    )
    print(decision.model_dump())


if __name__ == "__main__":
    main()

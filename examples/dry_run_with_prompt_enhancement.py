"""Dry-run a request through normalization, validation, and prompt enhancement."""

from kie_api import dry_run_prompt_enhancement, normalize_request, validate_request
from kie_api.models import RawUserRequest


def main() -> None:
    request = normalize_request(
        RawUserRequest(
            model_key="nano-banana-pro",
            prompt="make this portrait more cinematic",
            images=["https://example.com/source.png"],
            enhance=True,
        ),
    )

    validation = validate_request(request)
    enhancement = dry_run_prompt_enhancement(request)

    print("validation")
    print(validation.model_dump())
    print("enhancement")
    print(enhancement.model_dump())


if __name__ == "__main__":
    main()

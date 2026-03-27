"""Run the reusable request fixtures through normalization, validation, and payload build."""

from kie_api import REQUEST_FIXTURES, build_submission_payload, validate_request
from kie_api.enums import ValidationState


def main() -> None:
    ready_states = {
        ValidationState.READY,
        ValidationState.READY_WITH_DEFAULTS,
        ValidationState.READY_WITH_WARNING,
    }

    for fixture in REQUEST_FIXTURES.values():
        result = validate_request(fixture.request)
        print(f"[{fixture.key}] state={result.state}")
        print(result.model_dump())
        if result.state in ready_states:
            print(build_submission_payload(result))
        print("-" * 60)


if __name__ == "__main__":
    main()

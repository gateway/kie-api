"""Build a KIE payload locally from already-uploaded KIE media."""

from kie_api import build_submission_payload, validate_request
from kie_api.enums import ValidationState
from kie_api.models import RawUserRequest


def main() -> None:
    raw_request = RawUserRequest(
        model_key="kling-3.0-motion",
        images=["https://tempfile.redpandaai.co/kieai/183531/images/user-uploads/subject.png"],
        videos=["https://kieai.redpandaai.co/kieai/183531/videos/user-uploads/motion.mov"],
        options={"mode": "720p", "character_orientation": "image"},
    )
    validation = validate_request(raw_request)
    if validation.state not in {
        ValidationState.READY,
        ValidationState.READY_WITH_DEFAULTS,
        ValidationState.READY_WITH_WARNING,
    }:
        print(validation.model_dump())
        return
    print(build_submission_payload(validation))


if __name__ == "__main__":
    main()

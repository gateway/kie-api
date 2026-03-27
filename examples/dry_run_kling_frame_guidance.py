from pathlib import Path

from kie_api import (
    build_submission_payload,
    get_latest_successful_run,
    get_run_by_id,
    normalize_request,
    validate_request,
)
from kie_api.models import RawUserRequest


outputs_root = Path("outputs")
latest_nano = get_latest_successful_run(output_root=str(outputs_root), model_key="nano-banana-2")
first_frame = None

if latest_nano is not None:
    run = get_run_by_id(latest_nano.run_id, output_root=str(outputs_root))
    if run is not None and run.outputs:
        first_frame = str(Path(run.run_dir) / run.outputs[0].relative_path)

single_image_request = RawUserRequest(
    model_key="kling-3.0-i2v",
    prompt="Animate this still into a subtle cinematic move.",
    images=[first_frame or "https://example.com/start-frame.png"],
    options={"duration": 5, "mode": "pro"},
)

first_last_request = RawUserRequest(
    model_key="kling-3.0-i2v",
    prompt="Animate smoothly from the first frame to the last frame.",
    images=[
        first_frame or "https://example.com/start-frame.png",
        "https://example.com/end-frame.png",
    ],
    options={"duration": 5, "mode": "pro"},
)

for label, request in (
    ("single_image", single_image_request),
    ("first_last_frames", first_last_request),
):
    normalized = normalize_request(request)
    validation = validate_request(normalized)
    payload = build_submission_payload(validation) if validation.normalized_request else {}
    print(f"\n[{label}]")
    print("state:", validation.state)
    print("frame_guidance_mode:", validation.normalized_request.debug.get("frame_guidance_mode"))
    print("image_urls:", payload.get("input", {}).get("image_urls"))

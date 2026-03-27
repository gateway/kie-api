from kie_api import (
    apply_enhanced_prompt,
    build_submission_payload,
    normalize_request,
    resolve_prompt_context,
)
from kie_api.models import RawUserRequest


request = RawUserRequest(
    model_key="nano-banana-pro",
    prompt="Make this portrait look more cinematic and premium.",
    images=["https://tempfile.redpandaai.co/kieai/183531/images/user-uploads/ref.png"],
    enhance=True,
)

normalized = normalize_request(request)
prompt_context = resolve_prompt_context(normalized)

print("Resolved preset:", prompt_context.resolved_preset_key)
print("Input pattern:", prompt_context.input_pattern)
print("Rendered system prompt:")
print(prompt_context.rendered_system_prompt or "<none>")
print("User prompt:")
print(prompt_context.raw_prompt or "<none>")

# Replace this with your own wrapper-side LLM call.
llm_enhanced_prompt = (
    "Cinematic premium portrait, clean composition, refined lighting, "
    "elevated production value, preserve the subject and overall intent."
)

ready_for_submit = apply_enhanced_prompt(
    normalized,
    llm_enhanced_prompt,
    enhanced_prompt=llm_enhanced_prompt,
)
payload = build_submission_payload(ready_for_submit)

print(payload["input"]["prompt"])

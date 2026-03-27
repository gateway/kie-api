# Prompt Presets

Prompt presets are editable package resources. They are the built-in prompt strategies `kie-api` uses to help wrappers generate model-aware system prompts without hardcoding prompt rules in another repo.

The repo still keeps backward compatibility with the older term `prompt profile`, but `preset` is now the preferred term.

## Where they live

Each preset is a folder under:

- `src/kie_api/resources/prompt_profiles/<preset_key>/metadata.yaml`
- `src/kie_api/resources/prompt_profiles/<preset_key>/prompt.md`

Example:

- `src/kie_api/resources/prompt_profiles/nano_banana_pro_image_edit_v1/metadata.yaml`
- `src/kie_api/resources/prompt_profiles/nano_banana_pro_image_edit_v1/prompt.md`

## File format

`metadata.yaml` can contain:
- `key`
- `label`
- `version`
- `description`
- `applies_to_models`
- `applies_to_task_modes`
- `applies_to_input_patterns`
- `variables`
- `rules`
- `notes`
- `status`
- `source`

`prompt.md` contains the preset template body. It may include placeholders such as:
- `{{user_prompt}}`
- `{{model_key}}`
- `{{task_mode}}`
- `{{input_pattern}}`
- `{{image_count}}`
- `{{video_count}}`
- `{{audio_count}}`

`resolve_prompt_context(...)` renders the template into `rendered_system_prompt` for the wrapper to pass into its own LLM.

## How model defaults are chosen

Model specs choose their default preset key in:

- `specs/models/*.yaml`

Look for:

```yaml
prompt:
  default_profile_keys_by_input_pattern:
    prompt_only: nano_banana_pro_text_to_image_v1
    image_edit: nano_banana_pro_image_edit_v1
```

## How to change a model default without Python code

1. Edit the relevant model file under `specs/models/`.
2. Change either:
   - `prompt.default_profile_key`
   - or `prompt.default_profile_keys_by_input_pattern`
3. If you are preparing a packaged build, sync the bundled model mirror:

```bash
python scripts/sync_packaged_specs.py
```

Editable local development uses `specs/models/` directly. Packaged installs use the bundled mirror under `src/kie_api/resources/specs/models/`.

To check for drift without copying:

```bash
python scripts/sync_packaged_specs.py --check
```

## How to edit a prompt preset without Python code

1. Edit `prompt.md` for wording changes.
2. Edit `metadata.yaml` for labels, rules, version, or model bindings.
3. Run tests:

```bash
. .venv/bin/activate
python -m pytest
```

## Resolver behavior

The resolver chooses one effective preset per request in this order:
1. explicit request key
2. model spec `prompt.default_profile_keys_by_input_pattern[input_pattern]`
3. model spec `prompt.default_profile_key`
4. best built-in preset match for:
   - model
   - task mode
   - input pattern

Request-level overrides:
- `RawUserRequest.prompt_profile_key` overrides the built-in default preset choice
- `RawUserRequest.prompt_preset_key` is accepted as an alias
- `RawUserRequest.system_prompt_override` overrides the rendered preset for that request only

Wrapper-side resolution:
- use `resolve_prompt_context(...)` to load the effective preset metadata and rendered system prompt for a request
- use `apply_enhanced_prompt(...)` to set the final enhanced prompt before submission

## Notes

- Prompt presets are local dry-run resources. They do not require a KIE API key.
- The current enhancement backend remains deterministic by default unless an upstream backend is injected.
- `kie-api` owns built-in preset definitions and rendering behavior.
- A future Control API can store database-backed overrides and pass the winning preset key into `kie-api`.

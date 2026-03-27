"""Load model specs, prompt profiles, and pricing snapshots from resources."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from importlib import resources
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple, Union

import yaml

from ..enums import PromptInputPattern, PromptResolutionSource, TaskMode
from ..exceptions import ModelNotFoundError, SpecValidationError
from .models import ModelSpec, PricingSnapshot, PromptProfile

try:
    from importlib.abc import Traversable
except ImportError:  # pragma: no cover - Python <3.9 fallback
    from importlib_resources.abc import Traversable  # type: ignore


SpecsRoot = Union[Path, Traversable]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _default_specs_root() -> SpecsRoot:
    repo_specs = _repo_root() / "specs"
    if repo_specs.exists():
        return repo_specs
    return resources.files("kie_api").joinpath("resources", "specs")


def _default_prompt_profiles_root() -> SpecsRoot:
    repo_profiles = _repo_root() / "src" / "kie_api" / "resources" / "prompt_profiles"
    if repo_profiles.exists():
        return repo_profiles
    return resources.files("kie_api").joinpath("resources", "prompt_profiles")


def _default_pricing_root() -> SpecsRoot:
    repo_pricing = _repo_root() / "src" / "kie_api" / "resources" / "pricing"
    if repo_pricing.exists():
        return repo_pricing
    return resources.files("kie_api").joinpath("resources", "pricing")


def _join(path: SpecsRoot, *parts: str) -> SpecsRoot:
    current = path
    for part in parts:
        current = current.joinpath(part)
    return current


def _exists(path: SpecsRoot) -> bool:
    if isinstance(path, Path):
        return path.exists()
    return path.is_dir() or path.is_file()


def _iter_yaml_files(path: SpecsRoot) -> Iterable[SpecsRoot]:
    if isinstance(path, Path):
        yield from sorted(path.glob("*.yaml"))
        return
    yield from sorted(
        (item for item in path.iterdir() if item.is_file() and item.name.endswith(".yaml")),
        key=lambda item: item.name,
    )


def _read_yaml(path: SpecsRoot) -> dict:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise SpecValidationError(f"failed to parse YAML at {path}") from exc
    if not isinstance(payload, dict):
        raise SpecValidationError(f"expected YAML object at {path}")
    return payload


def _read_text(path: SpecsRoot) -> str:
    return path.read_text(encoding="utf-8")


def load_model_spec_file(path: SpecsRoot) -> ModelSpec:
    try:
        return ModelSpec.model_validate(_read_yaml(path))
    except Exception as exc:  # pragma: no cover - pydantic errors vary
        if isinstance(exc, SpecValidationError):
            raise
        raise SpecValidationError(f"invalid model spec at {path}") from exc


def load_prompt_profile_file(path: SpecsRoot) -> PromptProfile:
    try:
        return PromptProfile.model_validate(_read_yaml(path))
    except Exception as exc:  # pragma: no cover - pydantic errors vary
        if isinstance(exc, SpecValidationError):
            raise
        raise SpecValidationError(f"invalid prompt profile at {path}") from exc


def load_prompt_profile_dir(path: SpecsRoot) -> PromptProfile:
    metadata_path = _join(path, "metadata.yaml")
    prompt_path = _join(path, "prompt.md")
    if not _exists(metadata_path):
        raise SpecValidationError(f"missing prompt profile metadata: {metadata_path}")
    if not _exists(prompt_path):
        raise SpecValidationError(f"missing prompt profile markdown: {prompt_path}")

    payload = _read_yaml(metadata_path)
    payload["prompt_markdown"] = _read_text(prompt_path)
    payload["source_path"] = str(path)
    try:
        return PromptProfile.model_validate(payload)
    except Exception as exc:  # pragma: no cover - pydantic errors vary
        raise SpecValidationError(f"invalid prompt profile directory at {path}") from exc


def load_pricing_snapshot_file(path: SpecsRoot) -> PricingSnapshot:
    try:
        return PricingSnapshot.model_validate(_read_yaml(path))
    except Exception as exc:  # pragma: no cover - pydantic errors vary
        if isinstance(exc, SpecValidationError):
            raise
        raise SpecValidationError(f"invalid pricing snapshot at {path}") from exc


@dataclass
class SpecRegistry:
    model_specs: Dict[str, ModelSpec]
    prompt_profiles: Dict[str, PromptProfile]
    specs_root: SpecsRoot
    prompt_profiles_root: SpecsRoot

    def get_model(self, key: str) -> ModelSpec:
        try:
            return self.model_specs[key]
        except KeyError as exc:
            raise ModelNotFoundError(f"unknown model key: {key}") from exc

    def get_prompt_profile(self, key: str) -> PromptProfile:
        try:
            return self.prompt_profiles[key]
        except KeyError as exc:
            raise SpecValidationError(f"unknown prompt profile: {key}") from exc

    def list_prompt_profiles_for_model(self, model_key: str) -> Iterable[PromptProfile]:
        return (
            profile
            for profile in self.prompt_profiles.values()
            if model_key in profile.applies_to_models
        )

    def resolve_prompt_profile(
        self,
        model_key: str,
        requested_key: Optional[str] = None,
        *,
        task_mode: Optional[TaskMode] = None,
        input_pattern: Optional[PromptInputPattern] = None,
    ) -> Optional[PromptProfile]:
        match = self.resolve_prompt_profile_match(
            model_key,
            requested_key=requested_key,
            task_mode=task_mode,
            input_pattern=input_pattern,
        )
        return match[0]

    def resolve_prompt_profile_match(
        self,
        model_key: str,
        requested_key: Optional[str] = None,
        *,
        task_mode: Optional[TaskMode] = None,
        input_pattern: Optional[PromptInputPattern] = None,
    ) -> Tuple[Optional[PromptProfile], PromptResolutionSource]:
        if requested_key:
            return self.get_prompt_profile(requested_key), PromptResolutionSource.REQUEST_OVERRIDE
        spec = self.get_model(model_key)
        if input_pattern and input_pattern in spec.prompt.default_profile_keys_by_input_pattern:
            return (
                self.get_prompt_profile(spec.prompt.default_profile_keys_by_input_pattern[input_pattern]),
                PromptResolutionSource.MODEL_DEFAULT,
            )
        default_key = spec.prompt.default_profile_key
        if default_key:
            return self.get_prompt_profile(default_key), PromptResolutionSource.MODEL_DEFAULT

        candidates = [
            profile
            for profile in self.list_prompt_profiles_for_model(model_key)
            if _profile_matches_request(profile, task_mode=task_mode, input_pattern=input_pattern)
        ]
        if candidates:
            candidates.sort(key=_prompt_profile_sort_key, reverse=True)
            return candidates[0], PromptResolutionSource.BEST_MATCH

        generic = next(iter(self.list_prompt_profiles_for_model(model_key)), None)
        if generic:
            return generic, PromptResolutionSource.BEST_MATCH
        return None, PromptResolutionSource.NONE

    def iter_models(self) -> Iterable[ModelSpec]:
        return self.model_specs.values()


def load_registry(
    specs_root: Optional[SpecsRoot] = None,
    prompt_profiles_root: Optional[SpecsRoot] = None,
) -> SpecRegistry:
    resolved_root = specs_root or _default_specs_root()
    models_dir = _join(resolved_root, "models")
    profiles_dir = prompt_profiles_root or _default_prompt_profiles_root()

    if not _exists(models_dir):
        raise SpecValidationError(f"model specs directory not found: {models_dir}")
    if not _exists(profiles_dir):
        raise SpecValidationError(f"prompt profiles directory not found: {profiles_dir}")

    model_specs = {}
    for path in _iter_yaml_files(models_dir):
        spec = load_model_spec_file(path)
        if spec.key in model_specs:
            raise SpecValidationError(f"duplicate model key detected: {spec.key}")
        model_specs[spec.key] = spec

    prompt_profiles = {}
    for path in _iter_prompt_profile_entries(profiles_dir):
        profile = (
            load_prompt_profile_dir(path)
            if _is_dir(path)
            else load_prompt_profile_file(path)
        )
        if profile.key in prompt_profiles:
            raise SpecValidationError(f"duplicate prompt profile key detected: {profile.key}")
        prompt_profiles[profile.key] = profile

    return SpecRegistry(
        model_specs=model_specs,
        prompt_profiles=prompt_profiles,
        specs_root=resolved_root,
        prompt_profiles_root=profiles_dir,
    )


def load_latest_pricing_snapshot(pricing_root: Optional[SpecsRoot] = None) -> PricingSnapshot:
    resolved_root = pricing_root or _default_pricing_root()
    if not _exists(resolved_root):
        raise SpecValidationError(f"pricing directory not found: {resolved_root}")
    candidates = []
    for path in _iter_yaml_files(resolved_root):
        snapshot = load_pricing_snapshot_file(path)
        candidates.append((path, snapshot))
    if not candidates:
        raise SpecValidationError(f"no pricing snapshot files found in: {resolved_root}")
    candidates.sort(key=lambda item: _pricing_snapshot_sort_key(item[1], item[0]))
    return candidates[-1][1]


def _iter_prompt_profile_entries(path: SpecsRoot) -> Iterable[SpecsRoot]:
    if isinstance(path, Path):
        for item in sorted(path.iterdir(), key=lambda current: current.name):
            if item.is_dir():
                yield item
            elif item.is_file() and item.suffix == ".yaml":
                yield item
        return
    for item in sorted(path.iterdir(), key=lambda current: current.name):
        if item.is_dir():
            yield item
        elif item.is_file() and item.name.endswith(".yaml"):
            yield item


def _is_dir(path: SpecsRoot) -> bool:
    if isinstance(path, Path):
        return path.is_dir()
    return path.is_dir()


def _pricing_snapshot_sort_key(snapshot: PricingSnapshot, path: SpecsRoot):
    released_on = _parse_snapshot_date(snapshot.released_on)
    version_date = _parse_snapshot_date(snapshot.version)
    name = path.name if not isinstance(path, Path) else path.name
    return (
        released_on or date.min,
        version_date or date.min,
        snapshot.version,
        name,
    )


def _profile_matches_request(
    profile: PromptProfile,
    *,
    task_mode: Optional[TaskMode],
    input_pattern: Optional[PromptInputPattern],
) -> bool:
    if profile.applies_to_task_modes and task_mode not in profile.applies_to_task_modes:
        return False
    if profile.applies_to_input_patterns and input_pattern not in profile.applies_to_input_patterns:
        return False
    return True


def _prompt_profile_sort_key(profile: PromptProfile):
    return (
        0 if str(profile.status) == "deprecated" else 1,
        1 if profile.applies_to_task_modes else 0,
        1 if profile.applies_to_input_patterns else 0,
        len(profile.applies_to_task_modes),
        len(profile.applies_to_input_patterns),
        profile.key,
    )


def _parse_snapshot_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    candidate = value[:10]
    try:
        return date.fromisoformat(candidate)
    except ValueError:
        return None

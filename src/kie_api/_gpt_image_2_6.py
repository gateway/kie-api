"""Request rules shared by the four GPT Image 2.6 Market cards."""

from __future__ import annotations

import re
import stat
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image

from .enums import MediaRole, MediaType, TaskMode
from .models import InvalidInput, MediaReference, NormalizedRequest
from .registry.models import ModelSpec

MODEL_KEYS = frozenset(
    f"gpt-image-2-6-{tier}-{mode}-to-image"
    for tier in ("flare", "sunburst")
    for mode in ("text", "image")
)
EDIT_ROLE_FIELDS = {MediaRole.MASK: "mask_url", MediaRole.MARKUP: "markup"}
REFERENCE_ROLES = {None, MediaRole.REFERENCE}
FORMAT_OPTIONS = {
    "output_compression": {"jpeg", "webp"},
    "frame_count": {"gif"},
    "frame_duration_ms": {"gif"},
    "size": {"gif"},
    "svg_model": {"svg"},
}


def reference_images(request: NormalizedRequest) -> list[MediaReference]:
    return [item for item in request.images if item.role in REFERENCE_ROLES]


def validate_edit_roles(request: NormalizedRequest) -> list[InvalidInput]:
    errors = []
    for field, items in (
        ("images", request.images), ("videos", request.videos), ("audios", request.audios)
    ):
        for index, item in enumerate(items):
            if item.role in EDIT_ROLE_FIELDS and not (
                field == "images" and item.media_type == MediaType.IMAGE
                and request.model_key in MODEL_KEYS and request.task_mode == TaskMode.IMAGE_EDIT
            ):
                errors.append(InvalidInput(
                    field=f"{field}[{index}].role",
                    code="unsupported_image_edit_role",
                    message="Mask and markup roles are only supported as GPT Image 2.6 edit images.",
                    received=item.role.value,
                ))
    return errors


def validate_request_options(request: NormalizedRequest, spec: ModelSpec) -> list[InvalidInput]:
    options = request.options
    output_format = options.get("output_format") or "png"
    errors: list[InvalidInput] = []

    def invalid(field: str, message: str, code: str = "invalid_gpt_image_2_6_combination") -> None:
        errors.append(InvalidInput(field=field, code=code, message=message))

    for field, formats in FORMAT_OPTIONS.items():
        if field in spec.options and options.get(field) is not None and (
            not isinstance(output_format, str) or output_format not in formats
        ):
            invalid(field, f"'{field}' requires output_format: {' or '.join(sorted(formats))}.")

    background = options.get("background")
    if background is not None and (options.get("resolution") or "1K") != "1K":
        invalid("background", "The playground only supports explicit background at 1K.")
    if background == "transparent" and output_format not in ("png", "webp", "gif"):
        invalid("background", "Transparent background requires PNG, WebP or GIF output.")

    for field in ("output_compression", "frame_count", "frame_duration_ms"):
        if isinstance(options.get(field), bool):
            invalid(field, f"'{field}' must be an integer.", "invalid_integer")
    duration = options.get("frame_duration_ms")
    if type(duration) is int and duration % 10:
        invalid("frame_duration_ms", "GIF frame duration must be a multiple of 10 ms.")

    size = options.get("size")
    count = options.get("frame_count")
    if count is None:
        count = 9  # KIE's GIF default, used to validate an explicit size
    if output_format == "gif" and "size" in spec.options and isinstance(size, str) and size != "auto":
        if type(count) is int and 2 <= count <= 16 and not _valid_gif_size(size, count):
            invalid(
                "size",
                "GIF size must use positive multiples of 16 (WIDTHxHEIGHT) and fit a sprite "
                "sheet with sides up to 3840 px, area up to 8,294,400 px² and aspect ratio up to 3:1.",
                "invalid_gif_size",
            )

    if request.provider_model != spec.provider_model:
        invalid("provider_model", f"The provider model must be '{spec.provider_model}'.", "invalid_provider_model")
    if request.multi_prompt:
        invalid("multi_prompt", "GPT Image 2.6 accepts one prompt.", "unsupported_multi_prompt")
    final_prompt = request.final_prompt_used
    if final_prompt and final_prompt != request.prompt and (
        not final_prompt.strip() or len(final_prompt) > (spec.prompt.max_chars or 32000)
    ):
        invalid("final_prompt_used", "The final prompt must contain 1–32,000 characters.", "invalid_final_prompt")
    return errors


def edit_image_byte_limit(spec: ModelSpec, role: MediaRole | None) -> int | None:
    constraints = spec.input_constraints
    if constraints is None or role == MediaRole.MARKUP:
        return None
    limit_mb = constraints.mask_max_mb if role == MediaRole.MASK else constraints.image_max_mb
    return int(limit_mb * 1024**2) if limit_mb is not None else None


def validate_edit_images(request: NormalizedRequest, spec: ModelSpec) -> list[InvalidInput]:
    errors: list[InvalidInput] = []

    def invalid(field: str, message: str) -> None:
        errors.append(InvalidInput(field=field, code="invalid_gpt_image_2_6_media", message=message))

    auxiliary = [item for item in request.images if item.role in EDIT_ROLE_FIELDS]
    if len(auxiliary) > 1:
        invalid("images", "Provide at most one mask or one markup, never both.")
    if any(item.role == MediaRole.MASK for item in auxiliary) and request.options.get(
        "output_format"
    ) in ("gif", "svg"):
        invalid("images", "Masks cannot be used for GIF or SVG output.")

    constraints = spec.input_constraints
    reference_sizes: list[tuple[int, int] | None] = []
    auxiliary_sizes: list[tuple[str, MediaRole, tuple[int, int]]] = []
    for index, item in enumerate(request.images):
        field = f"images[{index}]"
        if item.media_type != MediaType.IMAGE or item.role not in REFERENCE_ROLES | EDIT_ROLE_FIELDS.keys():
            invalid(field, "Use an image with reference, mask or markup role.")
            continue
        size = None
        if item.path and item.url:
            invalid(field, "Provide either a local image path or an image URL.")
        elif item.path:
            try:
                path = Path(item.path)
                file_stat = path.stat()
                if not stat.S_ISREG(file_stat.st_mode):
                    invalid(field, "Local image path must identify a regular file.")
                    continue
                byte_limit = edit_image_byte_limit(spec, item.role)
                if byte_limit is not None and file_stat.st_size > byte_limit:
                    label = "Mask" if item.role == MediaRole.MASK else "Reference image"
                    invalid(field, f"{label} exceeds {byte_limit / 1024**2:g} MB.")
                    continue
                with Image.open(path) as image:
                    if item.role in EDIT_ROLE_FIELDS:
                        allowed = {"PNG"} if item.role == MediaRole.MARKUP else {"PNG", "WEBP"}
                        alpha_min = (
                            image.convert("RGBA").getchannel("A").getextrema()[0]
                            if image.format in allowed else 255
                        )
                        if item.role == MediaRole.MARKUP and alpha_min == 255:
                            invalid(field, "Markup must be a transparent PNG.")
                        if item.role == MediaRole.MASK and alpha_min != 0:
                            invalid(field, "Mask must be a PNG or WebP with alpha-zero pixels marking the edit region.")
                        if image.format in allowed:
                            size = _display_size(image)
                            auxiliary_sizes.append((field, item.role, size))
                    else:
                        formats = constraints.image_formats if constraints else None
                        if formats and (image.format or "").lower() not in formats:
                            invalid(field, "Reference image must be JPEG, PNG or WebP.")
                        else:
                            image.load()
                            size = _display_size(image)
            except (OSError, ValueError, SyntaxError, Image.DecompressionBombError):
                invalid(field, "Image bytes could not be decoded.")
        elif not _is_web_url(item.url):
            invalid(field, "Image URLs must be HTTP(S) URLs without user credentials.")
        if item.role in REFERENCE_ROLES:
            reference_sizes.append(size)

    first_size = reference_sizes[0] if reference_sizes else None
    for field, role, size in auxiliary_sizes:
        if first_size is not None and size != first_size:
            invalid(field, f"{role.value.capitalize()} dimensions must match the first reference image.")
    return errors


def _display_size(image: Image.Image) -> tuple[int, int]:
    # EXIF rotations 5–8 swap display width and height.
    return image.size[::-1] if image.getexif().get(274) in {5, 6, 7, 8} else image.size


def _is_web_url(value: str | None) -> bool:
    try:
        parsed = urlparse(value or "")
        return bool(parsed.scheme in {"http", "https"} and parsed.hostname and parsed.username is None)
    except ValueError:
        return False


def _valid_gif_size(size: str, count: int) -> bool:
    match = re.fullmatch(r"([0-9]{1,4})x([0-9]{1,4})", size)
    if not match:
        return False
    width, height = map(int, match.groups())
    if min(width, height) == 0 or width % 16 or height % 16:
        return False
    columns, rows = (4, 2) if count <= 8 else (3, 3) if count == 9 else (4, 3) if count <= 12 else (4, 4)
    for x, y in ((columns, rows), (rows, columns)):
        short, long = sorted((width * x, height * y))
        if long <= 3840 and short * long <= 8_294_400 and long <= 3 * short:
            return True
    return False

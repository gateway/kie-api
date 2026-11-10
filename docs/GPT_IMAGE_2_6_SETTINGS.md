# GPT Image 2.6 settings guide

The SDK supports four cards. They are `gpt-image-2-6-flare-text-to-image`, `gpt-image-2-6-flare-image-to-image`, `gpt-image-2-6-sunburst-text-to-image`, and `gpt-image-2-6-sunburst-image-to-image`. Available starting in version 0.2.0.

OpenAI documentation explains the image controls. Kie's playground and API determine which fields the SDK sends, along with their defaults, limits and billing.

## Choosing and steering the image

| Setting | Meaning |
| --- | --- |
| Model | Sunburst prioritizes demanding detail/edit accuracy; Flare targets faster iteration. Compare the same inputs. |
| Prompt | Describe the desired result and, for editing, what changes and what stays. Kie allows 32,000 characters. |
| Reference images | Kie editing accepts up to 16; their order matters when the prompt refers to image 1, image 2, etc. |
| Aspect ratio | Shape of the canvas; landscape, portrait or square. Kie also offers auto. |
| Resolution | Kie's 1K/2K/4K tiers map to dimensions by ratio; they are not universal exact side lengths. |
| Quality | low, medium, high, xhigh, max, auto. Controls rendered detail. Kie defaults to medium. No fixed cost or latency multiplier is established here. |
| Complexity | low, medium, high; default high. Controls planning before rendering, independently of quality. |
| Background | auto, opaque, transparent. Validate format compatibility and inspect actual alpha. Kie's playground and API descriptions disagree on some restrictions. |
| Moderation | auto or low; Kie defaults to low. This adjusts filtering, not visual quality. |
| Output compression | 0–100, JPEG/WebP only; controls file encoding rather than generation detail. |

## Editing regions

A mask supplies an alpha-based editable region. Markup supplies visible annotations on a transparent PNG overlay aligned with the first reference image. The box/circle workflow is markup: explain which marked object should change and ask for annotation removal. Kie accepts `mask_url` or `markup`, never both, and disallows masks for GIF/SVG. In the Sunburst smoke, a PNG mask selected the left object for recoloring while the background changed. The markup edit recolored the target and removed the magenta box. Treat either tool as guidance when surrounding pixels must be preserved.

## Output-specific controls

PNG is a useful default for lossless raster originals and transparency. JPEG is for opaque raster delivery. WebP supports compact raster delivery and alpha. GIF is an animation; SVG is a vector document requiring its own inspection/preview path.

For GIF, `frame_count` is 2–16 (default 9) and `frame_duration_ms` is 20–2000 (default 200). The SDK requires multiples of 10 ms per Kie's schema. Nine 200 ms frames make a 1.8-second cycle. Text-to-image also accepts `size` for per-frame dimensions, such as `512x512`; both sides must be positive multiples of 16, and the full sprite sheet must fit. Image-to-image does not accept that field. Kie’s OpenAPI prose conflicts on transparent GIF support. The Sunburst text-to-image smoke returned a transparent 512 × 512 GIF with two 200 ms frames. The animated WebP preview retained timing and alpha.

For SVG, SDK option `svg_model` maps to Kie’s `svg.model`, selecting the text model that authors the SVG. Default: gpt-5.6-luna; alternatives: gpt-6-sol and gpt-5.6-terra. This adds author-model token billing to image token billing. OpenAI’s upstream API documents SVG for generation. Kie returned a valid SVG from the Sunburst image-to-image endpoint in the live smoke.

When you create a run artifact, the SDK checks the image format from the file itself. GIFs keep their original bytes, an animated WebP preview by default, and a static thumbnail. The original and preview records expose frame count, one-cycle duration, and total plays when inspection completes. SVG originals are download-only. The SDK records a preview warning and leaves the inline preview paths empty.

The Sunburst SVG generation task returned `getapib.org`, outside the default download allowlist. For an SVG URL obtained from authenticated task status, use a separate download configuration after checking that exact hostname. The SDK can fetch the result without sending credentials or following redirects. The SVG edit smoke returned a different host already accepted by the default policy.

```python
from urllib.parse import urlsplit

from kie_api import KieSettings
from kie_api.clients.download import DownloadClient

if urlsplit(result_url).hostname != "getapib.org":
    raise ValueError("Unexpected SVG result host")

svg_settings = KieSettings(trusted_download_hosts=["getapib.org"])
with DownloadClient(svg_settings) as downloader:
    downloader.download_to_path(result_url, "result.svg", anonymous=True)
```

## SDK example

```python
from kie_api import RawUserRequest, prepare_request_for_submission, run_preflight, validate_request

request = RawUserRequest(
    model_key="gpt-image-2-6-sunburst-image-to-image",
    prompt="Make the marked mug blue. Remove the annotation. Keep the table and lighting.",
    images=[
        "mug.png",
        {"path": "circle-overlay.png", "role": "markup"},
    ],
    options={"quality": "medium", "complexity": "low", "output_format": "png"},
)

validation = validate_request(request)
# Once validation is ready, this estimates without submitting and warns that cost is unknown.
preflight = run_preflight(validation)
# This uploads media with your configured KIE_API_KEY; it does not start generation.
prepared = prepare_request_for_submission(validation)
```

Plain image entries are references, as are entries with `role: reference`. Use `role: mask` for an alpha mask or `role: markup` for an annotated overlay. An entry can specify a local `path` or a remote `url`. For the alpha-mask workflow, the SDK accepts decoded PNG or WebP with alpha-zero pixels. The Kie playground lists JPEG, PNG, and WebP uploads up to 30 MB for both edit cards. The SDK enforces the mask limit on local files and hosted downloads. JPEG mask behavior and WebP alpha-mask acceptance still need live Kie checks. A fully transparent mask represents an edit across the entire canvas. A mask with no alpha-zero pixels is rejected; the SDK never inverts opaque black-and-white masks. Markup must decode as a transparent PNG. When the first reference and auxiliary file are local, the SDK checks alignment against the displayed dimensions after EXIF orientation.

Dry runs cannot verify remote bytes. Preparation validates local files and uploads third-party sources through Kie. Immediately before sending a generation request, the SDK downloads the exact hosted references and auxiliary image from configured trusted upload hosts, without credentials or redirects. It checks bytes, supported formats, size limits, transparency and alignment; an unreadable, expired or invalid hosted input stops the request before generation. Temporary inspection copies are removed. File extensions, MIME headers and caller metadata do not establish image type.

## Suggested comparisons

Start a controlled Sunburst baseline with PNG, 1K, medium quality and default complexity. Compare high quality while holding everything else fixed; try max only for an unmet detail requirement. For a focused edit, compare lower complexity. For dense layouts, compare planning settings with quality held fixed. Record visual accuracy, unintended changes, latency, cost and output metadata independently.

## Deeper interpretation and acceptance checks

Quality and complexity are independent controls. A useful test design is a two-by-two comparison: medium/high quality crossed with low/high complexity, using the same prompt, references and dimensions. Treat this as an experiment, not four guaranteed visual outcomes. Quality targets rendering detail; complexity changes planning. For a small recolor, lower complexity may suffice. For an open-ended layout with interacting objects, higher complexity is worth comparing. Higher complexity is not an instruction to add more objects.

Background is a three-value API input, best represented by Auto / Opaque / Transparent choices. Opaque means no see-through background; transparent means an alpha cutout. For a character cutout, request transparent plus PNG and describe the isolated character in the prompt. Verify decoded alpha and inspect the character against light and dark backgrounds; a checkerboard painted into the image is not transparency.

The upstream Python edit reference explicitly defines mask alpha=0 as editable. An ordinary opaque black-and-white RGB image is therefore not sufficient. If an editor's mask uses white=edit, convert that convention to transparent=edit deliberately. The upstream reference specifies matching dimensions and first-image targeting. Do not assume intermediate alpha has a documented proportional edit-strength interpretation. The generation guide says masks guide the model and are not exact spatial locks; strict preservation requires compositing and a separate acceptance check. The upstream reference and guide disagree on file-size limits, while Kie has its own transport limits; do not import those upstream size caps into Kie's validators blindly.

Markup is a separate raster PNG annotation layer, with transparency outside its visible marks, at the first image's dimensions after orientation. It is not a JSON list of rectangles. A UI may keep coordinates internally, then rasterize them to the PNG sent to Kie. Do not flatten the annotations onto the source. Test a marked target, removal of annotation marks, and preservation of an unmarked control object. Kie transports the overlay URL in markup; upstream OpenAI supports different file/URL wrappers.

Moderation changes content-filter strictness. Low is less restrictive, not filtering disabled. Keep it separate from quality and complexity in labels and tests.

Additional source: [OpenAI Python edit reference](https://developers.openai.com/api/reference/python/resources/images/methods/edit.md). Definitions checked on 2026-11-10. See the verification scope below for tested Kie behavior.

## Reference links

- [OpenAI image prompting](https://developers.openai.com/api/docs/guides/image-prompting)
- [OpenAI image generation](https://developers.openai.com/api/docs/guides/image-generation)
- [Kie model playground and pricing](https://kie.ai/gpt-image-2-6)
- [Kie Sunburst generation contract](https://docs.kie.ai/market/gpt/gpt-image-2-6-sunburst-text-to-image.md)
- [Kie Sunburst editing contract](https://docs.kie.ai/market/gpt/gpt-image-2-6-sunburst-image-to-image.md)

## Verification scope

Nine live Kie tasks passed on 2026-11-10: transparent PNG generation and reference editing on both Flare and Sunburst, plus Sunburst PNG mask editing, PNG markup editing, GIF generation, SVG generation, and SVG reference editing. Artifact checks covered decoded transparency, GIF timing and animated preview preservation, and download-only SVG handling. Masks and markup guided the target edit but did not guarantee preservation of surrounding pixels.

This is coverage of those combinations, not every quality, resolution, format, and auxiliary-input combination. JPEG masks and WebP alpha masks need further live verification. Media Studio integration and its UI acceptance testing are separate from this SDK release.

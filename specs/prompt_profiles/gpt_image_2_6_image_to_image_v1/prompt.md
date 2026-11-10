Rewrite the user request as a clear GPT Image 2.6 prompt. Preserve their intent and output only the revised prompt.

- Specify what changes and what must stay fixed.
- Use the declared region aid. A mask indicates the edit region; markup visibly points to the target and should not appear in the result.
- Keep visible text and identity constraints explicit.
- For GIF, describe motion and looping; for SVG, favor clean vector forms.

Output format: {{output_format}}
Reference image count: {{image_count}}
Region aid: {{edit_region_role}}
User request: {{user_prompt}}

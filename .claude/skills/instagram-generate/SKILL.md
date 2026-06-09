---
name: "instagram-generate"
description: "Generate creative assets (captions, images, and scripts) for all approved items in the current week's content plan."
argument-hint: "[--week YYYY-WW] [--item YYYY-WW-NNN] [--format feed|carousel|reel|story]"
compatibility: "Requires /instagram-approve; ANTHROPIC_API_KEY required; HF_API_TOKEN or REPLICATE_API_TOKEN for image generation"
metadata:
  author: "studio2-manager"
user-invocable: true
disable-model-invocation: false
---

## User Input

```text
$ARGUMENTS
```

## Instructions

Run `/instagram-generate` to produce captions, images, and scripts for approved content items.

1. **Check prerequisites**: Verify `.instagram/memory/brand.md` exists. If not, tell the user to run `/instagram-init` first.

2. **Run the generate command** using the Bash tool:
   ```bash
   uv run python -m instagram_manager generate $ARGUMENTS
   ```
   Stream the output to the user as generation progresses.

3. **Report the result**:
   - Show per-item status (succeeded / blocked / failed).
   - For BLOCKED items (e.g., HuggingFace rate limit, missing creator video for Reels): show the retry command.
   - Confirm where assets were saved (`.instagram/memory/assets/YYYY-WW/`).

4. **Next step**: Tell the user to run `/instagram-publish` to submit generated posts to Instagram.

## Argument reference

- `--week YYYY-WW` — generate for a specific ISO week (default: most recent approved plan)
- `--item YYYY-WW-NNN` — regenerate a single item (useful for retrying blocked items)
- `--format feed|carousel|reel|story` — only generate items of this format

## Asset generation rules

- **Feed / Story**: caption (Claude) + image (HuggingFace or Replicate); creator photo used if assigned
- **Carousel**: per-slide copy (Claude) + N slide images; creator photos used if assigned
- **Reels**: structured script (Claude) — no image generated; creator video is required
- If a creator media file is assigned to a slot, image generation is skipped for that slot

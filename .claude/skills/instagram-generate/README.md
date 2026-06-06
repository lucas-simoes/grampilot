# /instagram-generate

Generate creative assets (captions, images, and scripts) for all approved items in the
current week's content plan.

## Invocation

```
/instagram-generate
/instagram-generate --week 2026-23
/instagram-generate --item 2026-23-003
/instagram-generate --format carousel
```

## How to run

```bash
python -m instagram_manager generate [--week YYYY-WW] [--item ITEM_ID] [--format FORMAT]
```

## What it does

For each approved ContentItem:
1. **Feed/Story**: Generates caption (Claude) + image (HuggingFace / Replicate)
2. **Carousel**: Generates per-slide copy (Claude) + N slide images
3. **Reels**: Generates structured script (intro/body/CTA) + caption. No image generated — Reels require a creator-provided video.

If a creator-provided media file is assigned to the slot (from `/instagram-media`), it is
used as the primary asset and image generation is skipped.

## Prerequisites

- `/instagram-approve` must have been run
- `ANTHROPIC_API_KEY` must be set
- For image generation: `HF_API_TOKEN` (HuggingFace) or `REPLICATE_API_TOKEN`

## Expected output

```
Generating assets for plan 2026-23 (7 items)...

[1/7] 2026-23-001 feed      ✓ caption.txt  ✓ image_01.jpg
[2/7] 2026-23-002 carousel  ✓ caption.txt  ✓ 6 slides
[3/7] 2026-23-003 reel      ✓ script.md    (no image — provide video via /instagram-media)
[4/7] 2026-23-004 story     ✗ BLOCKED: image generation failed (HF rate limit)
      → Retry with: /instagram-generate --item 2026-23-004

Generation complete: 6/7 succeeded, 1 blocked.
Assets saved to .instagram/memory/assets/2026-23/
```

## Error handling

- Image generation failure → item marked BLOCKED, retryable with `--item`
- Text generation failure → item marked FAILED, plan generation aborts
- Missing plan → "Plan not found. Run /instagram-plan first."
- Unapproved plan → "Plan must be approved. Run /instagram-approve first."

## Next step

Run `/instagram-publish` to submit generated posts to Instagram.

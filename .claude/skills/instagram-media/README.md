# /instagram-media

Manage the creator media library — add photos, videos, and audio files to use as
primary assets in your content plan.

## Invocation

```
/instagram-media                                           # List all files
/instagram-media add <file-path>                          # Add file (auto-detects type)
/instagram-media add <file-path> --slot 2026-23-003 --desc "Description"
/instagram-media assign <media-id> --slot 2026-23-004    # Assign to a plan slot
/instagram-media analyze                                   # Run Claude Vision style analysis
/instagram-media remove <media-id>                        # Remove from index
```

## How to run

```bash
python -m instagram_manager media [add|list|assign|analyze|remove] [args]
```

## What it does

### `add`
Copies the file to `.instagram/media/`, registers it in the media index, and optionally
assigns it to a plan slot. If the file is a photo and `auto_update: true` is set in
`config.yml`, re-runs style analysis automatically.

### `list` (default)
Shows all media files split into assigned and unassigned. Also detects any files dropped
directly into `.instagram/media/` since the last invocation.

### `assign`
Links an existing media file to a specific ContentItem slot in the current plan.

### `analyze`
Reads up to `max_photos` creator photos using Claude Vision and writes a cached style
profile to `.instagram/memory/style-profile.md`. Used by `/instagram-generate` to enrich
AI image generation prompts.

### `remove`
Removes the entry from the media index. **Does not delete the file** from `.instagram/media/`.

## Media type rules

| Type   | Publishable | Role |
|--------|-------------|------|
| Photo  | ✅ Yes      | Primary asset for feed/carousel/story; used in style analysis |
| Video  | ✅ Yes      | Required primary asset for Reels |
| Audio  | ❌ No       | Soundtrack reference for Reels scripts only; never uploaded |

## Prerequisites

- `.instagram/memory/brand.md` must exist (run `/instagram-init` first)
- For `analyze`: `ANTHROPIC_API_KEY` must be set

## Expected output

### List
```
Creator Media Library — 5 files

UNASSIGNED
  media-001  photo  photo-beach-sunset.jpg    2026-06-04
  media-002  audio  summer-vibe.mp3           2026-06-05

ASSIGNED TO PLAN
  media-003  photo  recipe-flatlay.jpg        → 2026-23-002 (feed)
  media-004  video  reel-cooking.mp4          → 2026-23-003 (reel)

Style profile: ✓ up to date (2026-06-05, 4 photos)
```

## Next step

After adding and assigning media, run `/instagram-generate` to produce content assets.
Creator media files are used as the primary asset — AI generation only runs for slots
without an assigned file.

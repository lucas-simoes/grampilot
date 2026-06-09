---
name: "instagram-media"
description: "Manage the creator media library: add, list, assign, analyze, or remove photos, videos, and audio files."
argument-hint: "[add <file>] [list] [assign <id> --slot <slot>] [analyze] [remove <id>]"
compatibility: "Requires /instagram-init to have been run; analyze requires ANTHROPIC_API_KEY"
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

Run `/instagram-media` to manage your creator media library.

1. **Run the media command** using the Bash tool:
   ```bash
   uv run python -m instagram_manager media $ARGUMENTS
   ```
   Stream the output to the user.

2. **Report the result** based on the subcommand:
   - **list** (default): Show assigned and unassigned files, style profile status.
   - **add**: Confirm the file was copied to `.instagram/media/` and registered.
   - **assign**: Confirm the media was linked to the plan slot.
   - **analyze**: Report how many photos were sampled and that `style-profile.md` was updated.
   - **remove**: Confirm removal from the index (file stays on disk).

3. **Subcommand hints** (if user ran `/instagram-media` with no arguments, show available subcommands):
   - `add <file-path> [--slot YYYY-WW-NNN] [--desc "..."]`
   - `list` — list all media files (default)
   - `assign <media-id> --slot YYYY-WW-NNN`
   - `analyze` — run Claude Vision style analysis on creator photos
   - `remove <media-id>`

## Media type rules

- **Photo** (JPG/PNG/WebP/HEIC): publishable; used for feed/carousel/story and style analysis
- **Video** (MP4/MOV): publishable; required primary asset for Reels
- **Audio** (MP3/WAV/M4A): reference only — never uploaded; annotates Reels scripts

## Next step

After adding and assigning media, run `/instagram-generate` to produce content assets.

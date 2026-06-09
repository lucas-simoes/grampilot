---
name: "instagram-publish"
description: "Publish approved, asset-ready posts to Instagram immediately via the Meta Graph API."
argument-hint: "[--week YYYY-WW] [--item YYYY-WW-NNN] [--all]"
compatibility: "Requires /instagram-generate; META_ACCESS_TOKEN and META_IG_USER_ID in .env"
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

Run `/instagram-publish` to publish generated posts to Instagram via the Meta Graph API.

1. **Check prerequisites**: Verify `META_ACCESS_TOKEN` and `META_IG_USER_ID` are set in `.env`. If not, stop and tell the user.

2. **Run the publish command** using the Bash tool:
   ```bash
   uv run python -m instagram_manager publish $ARGUMENTS
   ```
   Stream the output to the user.

3. **Report the result**:
   - Show per-item status: published (with post ID) / failed / blocked.
   - If token is near expiry (< 7 days): surface the warning prominently.
   - If token is expired: stop and tell the user to renew before retrying.
   - For blocked Reels (no creator video): show the fix command (`/instagram-media assign`).

4. **Next step**: After publishing, tell the user to wait 48 hours then run `/instagram-insights` to fetch performance metrics.

## Argument reference

- `--week YYYY-WW` — publish all generated items for a specific ISO week
- `--item YYYY-WW-NNN` — publish a single item
- `--all` — publish all generated items across all weeks (use with caution)

## Important notes

- Posts are published **immediately** — there is no scheduled publish via the Meta API.
- To publish at a specific time, schedule the CLI with OS cron (see README.md).
- Audio files are never uploaded to Meta; they are reference-only for Reels scripts.

# /instagram-publish

Publish approved, asset-ready posts to Instagram immediately via the Meta Graph API.

## Invocation

```
/instagram-publish
/instagram-publish --week 2026-23
/instagram-publish --item 2026-23-001
/instagram-publish --all
```

## How to run

```bash
python -m instagram_manager publish [--week YYYY-WW] [--item ITEM_ID] [--all]
```

## What it does

For each `generated` ContentItem:
1. Checks token expiry (warns if < 7 days; halts if expired)
2. Reads assets from `.instagram/memory/assets/YYYY-WW/<item_id>/`
3. Creates a media container via `POST /v18.0/{IG_USER_ID}/media`
4. Publishes the container via `POST /v18.0/{IG_USER_ID}/media_publish`
5. Records the platform post ID and marks the item as `published`
6. Logs all events to `.instagram/memory/logs/events.jsonl`

## Publishing model

Posts are published **immediately** when this skill runs. There is no native scheduled
publishing via the Meta API for Instagram. The `intended_time` from your content plan
is kept as operator reference. To publish at a specific time, schedule the CLI command
using OS cron:

```bash
# Publish every day at 09:00
0 9 * * * cd /your/project && python -m instagram_manager publish >> .instagram/memory/logs/cron.log 2>&1
```

## Prerequisites

- Plan must be approved (`/instagram-approve` must have been run)
- Assets must be generated (`/instagram-generate` must have been run)
- `META_ACCESS_TOKEN` and `META_IG_USER_ID` must be set in `.env`
- For Reels: a creator video must be assigned to the slot via `/instagram-media`

## Expected output

```
Publishing plan 2026-23 (6 generated items)...

⚠  Token expires in 12 days. Renew before 2026-06-17.

[1/6] 2026-23-001 feed      ✓ Published — post ID: 17924300001
[2/6] 2026-23-002 carousel  ✓ Published — post ID: 17924300002
[3/6] 2026-23-003 reel      ✗ BLOCKED — no creator video assigned
      → Assign with: /instagram-media assign <media-id> --slot 2026-23-003
[4/6] 2026-23-004 story     ✓ Published — post ID: 17924300004

Published: 3/6 succeeded | 0 failed | 1 blocked | 2 skipped
```

## Error handling

- **Token expired**: Halts immediately; no posts submitted; re-auth instructions displayed
- **Token < 7 days**: Warning shown; publishing continues
- **API error on item**: Item marked failed; next item processed; summary shown
- **Reel with no video**: Item marked blocked; shown in summary with fix command
- **Missing assets**: Item skipped with BLOCKED status

## Next step

After publishing, run `/instagram-insights` (after 48h) to retrieve performance metrics.

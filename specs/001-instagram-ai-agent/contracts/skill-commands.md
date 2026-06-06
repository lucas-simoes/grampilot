# Skill Command Contracts

**Branch**: `001-instagram-ai-agent` | **Date**: 2026-06-05 (updated with Creator Media Library)

Each contract defines: invocation syntax, inputs, outputs, side effects, error conditions,
and the exit states produced. Skills are Claude Code slash commands defined under
`.claude/skills/instagram-*/`.

---

## `/instagram-init`

**Purpose**: First-run onboarding — creates the `.instagram/` directory structure, brand
profile, config file, and validates credentials.

**Invocation**:
```
/instagram-init
/instagram-init --reset          # Reinitialise without deleting existing plans/assets
```

**Inputs**:
- Interactive Q&A with the operator to populate brand profile fields
- Existing `.env` file (if credentials already configured)

**Outputs (CLI)**:
```
✓ .instagram/ directory created
✓ Brand profile written to .instagram/memory/brand.md
✓ Config written to .instagram/config.yml
✓ META_ACCESS_TOKEN validated (account: @handle, expires: 2026-08-04)
✓ ANTHROPIC_API_KEY validated
✓ HF_API_TOKEN validated
✓ Setup complete. Run /instagram-plan to generate your first weekly calendar.
```

**Side effects**:
- Creates `.instagram/` directory tree
- Writes `.instagram/memory/brand.md` from brand profile template
- Writes `.instagram/config.yml`
- Appends `.env` to `.gitignore` if not present

**Error conditions**:
| Error | Message | Resolution |
|-------|---------|------------|
| Missing `META_ACCESS_TOKEN` | `✗ META_ACCESS_TOKEN not set in .env` | Operator must add token |
| Invalid token | `✗ Meta API returned 401 — token invalid or expired` | Generate new token |
| Missing `ANTHROPIC_API_KEY` | `✗ ANTHROPIC_API_KEY not set` | Add to .env |

---

## `/instagram-plan`

**Purpose**: Generate a 7-day content calendar for the upcoming week.

**Invocation**:
```
/instagram-plan
/instagram-plan --week 2026-24    # Plan a specific ISO week
/instagram-plan --theme "summer"  # Override theme for the week
```

**Inputs**:
- `.instagram/memory/brand.md` (brand profile — MUST exist)
- `.instagram/memory/insights/YYYY-WW.json` (previous week's insights — optional)
- `ANTHROPIC_API_KEY` (env)

**Outputs (CLI)**:
```
Generating weekly plan for 2026-23 (2026-06-01 → 2026-06-07)...

📅 Weekly Plan — 2026-23

Mon 01/06 09:00 [feed]     "5 dicas para começar a semana produtiva"
Tue 02/06 18:00 [carousel]  "Guia completo: rotina matinal em 6 slides"
Wed 03/06 12:00 [story]     "Bastidores: como preparamos nosso conteúdo"
...

Plan saved to .instagram/memory/plans/2026-23.md
Review, edit the plan file, then run /instagram-approve to proceed.
```

**Side effects**:
- Writes `.instagram/memory/plans/YYYY-WW.md` (human-readable)
- Writes `.instagram/memory/plans/YYYY-WW.json` (machine-readable, status: "draft")
- Appends a `planned` event to `.instagram/memory/logs/events.jsonl`

**Error conditions**:
| Error | Message | Resolution |
|-------|---------|------------|
| No brand profile | `✗ .instagram/memory/brand.md not found — run /instagram-init first` | Run init |
| Claude API error | `✗ Text generation failed: <reason>` | Retry or check API key |
| Plan already exists | `Plan 2026-23 already exists (status: approved). Use --force to overwrite.` | Use flag |

---

## `/instagram-approve`

**Purpose**: Transition the current week's plan from `draft` to `approved`, gating all
downstream skills.

**Invocation**:
```
/instagram-approve
/instagram-approve --week 2026-23
```

**Inputs**:
- `.instagram/memory/plans/YYYY-WW.json` (MUST exist, status MUST be "draft")

**Outputs (CLI)**:
```
Plan 2026-23 approved. ✓
7 items ready for asset generation.
Run /instagram-generate to produce creative assets.
```

**Side effects**:
- Updates `status` field in `YYYY-WW.json` to `"approved"` and sets `approved_at`
- Appends an `approved` event to the log

**Error conditions**:
| Error | Message |
|-------|---------|
| No plan for week | `✗ No draft plan found for 2026-23. Run /instagram-plan first.` |
| Plan already approved | `Plan 2026-23 is already approved.` |

---

## `/instagram-media`

**Purpose**: Manage the creator media library — add files with optional annotation, list
contents, assign files to plan slots, run Claude Vision style analysis, and remove files.

**Invocation**:
```
/instagram-media                          # List all files (assigned and unassigned)
/instagram-media add <file-path>          # Add file; auto-triggers style re-analysis if photo
/instagram-media add <file-path> --slot 2026-23-003 --desc "Golden hour at the beach"
/instagram-media assign <media-id> --slot 2026-23-004
/instagram-media analyze                  # Run Claude Vision on photos → style-profile.md
/instagram-media remove <media-id>
```

**Inputs**:
- `<file-path>`: local filesystem path to the media file
- `.instagram/memory/media-index.json` (current library state)
- `ANTHROPIC_API_KEY` (only for `analyze` subcommand)

**Outputs (CLI)**:

*`/instagram-media` (list)*:
```
Creator Media Library — 5 files

UNASSIGNED
  media-001  photo  photo-beach-sunset.jpg      2026-06-04
  media-002  audio  summer-vibe-ref.mp3         2026-06-05

ASSIGNED TO PLAN
  media-003  photo  recipe-flatlay.jpg          → 2026-23-002 (feed)
  media-004  video  reel-cooking-process.mp4    → 2026-23-003 (reel)
  media-005  photo  plating-closeup.jpg         → 2026-23-005 (carousel slide 1)

Style profile: ✓ up to date (2026-06-05, 4 photos)
```

*`/instagram-media add` (with photo)*:
```
✓ Added: photo-beach-sunset.jpg (media-001)
✓ Style profile updated (5 photos analysed → style-profile.md)
```

*`/instagram-media analyze`*:
```
Analysing 8 creator photos with Claude Vision...
✓ Style profile written to .instagram/memory/style-profile.md
  Colour: warm earth tones, natural light
  Composition: flat-lay, centered subjects, clean backgrounds
  Mood: calm, artisanal
```

**Side effects**:
- `add`: copies file reference into `media-index.json`; if photo and `auto_update: true`
  in config, re-runs style analysis automatically
- `assign`: updates `assigned_item` in `media-index.json`
- `analyze`: reads up to `max_photos` creator photos via Claude Vision; overwrites
  `style-profile.md` atomically
- `remove`: removes entry from `media-index.json`; does NOT delete the original file

**Error conditions**:
| Error | Message | Resolution |
|-------|---------|------------|
| File not found | `✗ File not found: /path/to/file.jpg` | Check path |
| Unsupported format | `✗ Format .bmp not supported. Accepted: jpg, png, webp, heic, mp4, mov, mp3, wav, m4a` | Convert file |
| Audio assigned to non-Reel | `✗ Audio files can only be assigned to Reel slots` | Use a reel slot |
| No photos for analyze | `✗ No photos in library. Add photos first with /instagram-media add` | Add photos |
| Claude API error | `✗ Style analysis failed: <reason>` | Retry |

---

## `/instagram-generate`

**Purpose**: Generate creative assets (images + copy) for all approved items in the
current week's plan.

**Invocation**:
```
/instagram-generate
/instagram-generate --week 2026-23
/instagram-generate --item 2026-23-003   # Single item
/instagram-generate --format carousel    # Only carousel items
```

**Inputs**:
- `.instagram/memory/plans/YYYY-WW.json` (MUST exist, status MUST be "approved")
- `.instagram/memory/brand.md`
- `ANTHROPIC_API_KEY` (text generation)
- Image provider credentials (from `.env`, based on `IMAGE_PROVIDER` config)

**Outputs (CLI)**:
```
Generating assets for plan 2026-23 (7 items)...

[1/7] 2026-23-001 feed       ✓ caption.txt  ✓ image_01.jpg
[2/7] 2026-23-002 carousel   ✓ caption.txt  ✓ image_01.jpg ... image_05.jpg
[3/7] 2026-23-003 reel       ✓ script.md    (no image — Reels require operator video)
[4/7] 2026-23-004 story      ✓ caption.txt  ✗ image_01.jpg FAILED: HF rate limit
      → Item 2026-23-004 marked BLOCKED. Provide image manually or retry with:
        /instagram-generate --item 2026-23-004

Generation complete: 6/7 succeeded, 1 blocked.
Assets saved to .instagram/memory/assets/2026-23/
```

**Side effects**:
- Creates `.instagram/memory/assets/YYYY-WW/<item_id>/` directories with asset files
- Updates `status` and `assets` fields in `YYYY-WW.json`
- Appends `generated` or `blocked` events to the log

**Error conditions**:
| Error | Behaviour |
|-------|-----------|
| Image API rate limit | Item marked BLOCKED; operator notified with retry command |
| Image API error | Item marked BLOCKED with error message |
| Text generation error | Item marked FAILED; full plan generation aborted |
| Plan not approved | `✗ Plan must be approved before generating. Run /instagram-approve.` |

---

## `/instagram-publish`

**Purpose**: Publish approved, asset-ready items to Instagram immediately via the Meta
Graph API.

**Invocation**:
```
/instagram-publish
/instagram-publish --week 2026-23
/instagram-publish --item 2026-23-001    # Single item
/instagram-publish --all                 # All generated items across all weeks
```

**Inputs**:
- `.instagram/memory/plans/YYYY-WW.json` (status MUST be "approved")
- `.instagram/memory/assets/YYYY-WW/<item_id>/manifest.json` (assets MUST exist)
- `META_ACCESS_TOKEN`, `META_IG_USER_ID` (env)

**Outputs (CLI)**:
```
Publishing plan 2026-23 (6 ready items)...

⚠  Token expires in 12 days. Renew before 2026-06-17.

[1/6] 2026-23-001 feed      ✓ Published — post ID: 17924300001
[2/6] 2026-23-002 carousel  ✓ Published — post ID: 17924300002
[3/6] 2026-23-003 reel      ✗ FAILED: Reels require video upload — item skipped
      Tip: Record your Reel using the script at assets/2026-23/2026-23-003/script.md
           then upload manually or provide the video file path:
           /instagram-publish --item 2026-23-003 --video /path/to/reel.mp4
[4/6] 2026-23-004           BLOCKED — missing assets, skipped

Published: 2/6 succeeded | 1 failed (Reel) | 1 blocked | 2 pending
```

**Side effects**:
- Calls `POST /v18.0/<IG_ID>/media` and `POST /v18.0/<IG_ID>/media_publish`
- Updates `status` and `publish_event` in `YYYY-WW.json`
- Appends `publishing` and `published`/`failed` events to the log

**Error conditions**:
| Error | Behaviour |
|-------|-----------|
| Token expired | Full stop; no posts submitted; re-auth instructions displayed |
| Token expires < 7 days | Warning shown but execution continues |
| Media container error | Item retried up to 3 times; then marked failed |
| Rate limit hit | 10-second back-off between retries |
| Missing assets | Item skipped; marked BLOCKED |

**Scheduling note**: Posts are published **immediately** when this skill runs. The
`intended_time` field in the plan is operator guidance only — use OS cron or run the
skill manually at the desired time. Example cron for daily 9am post:
```
0 9 * * * cd /project && claude -p "/instagram-publish --item $(date +%Y-%m-%d)" >> .instagram/memory/logs/cron.log 2>&1
```

---

## `/instagram-insights`

**Purpose**: Fetch post performance metrics from the Meta Insights API for all published
posts in the previous week.

**Invocation**:
```
/instagram-insights
/instagram-insights --week 2026-23
/instagram-insights --item 2026-23-001
```

**Inputs**:
- `.instagram/memory/plans/YYYY-WW.json` (to identify published posts with `meta_post_id`)
- `META_ACCESS_TOKEN`, `META_IG_USER_ID` (env)

**Outputs (CLI)**:
```
Fetching insights for plan 2026-23 (5 published posts)...

2026-23-001 feed      reach: 1,250  impressions: 1,840  engagement: 10.2%  saves: 23  ⭐ top
2026-23-002 carousel  reach:   980  impressions: 1,200  engagement:  8.5%  saves: 14
2026-23-004 story     reach:   620  impressions:   740  engagement:  N/A   saves: N/A

Note: 2026-23-003 Reel insights not available (published < 48h ago).

Insights saved to .instagram/memory/insights/2026-23.json
Run /instagram-plan to use these insights for next week's planning.
```

**Side effects**:
- Writes `.instagram/memory/insights/YYYY-WW.json`
- Marks `top_performer: true` on the highest-engagement item
- Appends `insights_fetched` events to the log

**Error conditions**:
| Error | Behaviour |
|-------|-----------|
| Post published < 48h | Metric shown as "pending" with a note; partial results saved |
| Story published > 24h | Story insights unavailable; noted in output |
| Token expired | Full stop with re-auth instructions |
| No published posts for week | `No published posts found for 2026-23.` |

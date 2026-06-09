# GramPilot

**GramPilot** is an AI-powered Instagram content manager that runs entirely inside [Claude Code](https://claude.ai/code). Plan, create, and publish your weekly content through simple slash commands — no app to install, no subscription, no dashboard.

```
/instagram-init → /instagram-plan → /instagram-approve → /instagram-generate → /instagram-publish → /instagram-insights
```

Under the hood, each command is a Claude Code skill backed by a Python library. Claude writes your captions and scripts, generates images via HuggingFace (or Replicate), and publishes directly through the Meta Graph API.

---

## Prerequisites

- **[Claude Code CLI](https://claude.ai/code)** — installed and authenticated (`claude --version`)
- **Python 3.11+** (`python3 --version`)
- **Instagram Business or Creator account** connected to a Facebook Page
- **Meta Developer account** with an app configured (instructions below)

---

## Installation

**1. Clone the repo and install dependencies:**

```bash
git clone https://github.com/lucas-simoes/grampilot.git
cd grampilot
pip install -e ".[dev]"
```

Or install dependencies manually:

```bash
pip install anthropic requests python-dotenv rich huggingface_hub Pillow mutagen
```

**2. Copy the example environment file:**

```bash
cp .env.example .env
```

Fill in your credentials:

```dotenv
META_ACCESS_TOKEN=your_long_lived_token_here
META_IG_USER_ID=your_instagram_user_id_here
ANTHROPIC_API_KEY=your_anthropic_key_here
HF_API_TOKEN=your_huggingface_token_here
```

**3. Get your Meta credentials (one-time):**

1. Go to [developers.facebook.com](https://developers.facebook.com) → My Apps → Create App
2. Add the **Instagram Graph API** product
3. Under **Instagram → API Setup with Instagram Login**, connect your Instagram account
4. Generate a **Long-Lived User Access Token** (valid 60 days) with these permissions:
   - `instagram_basic`
   - `instagram_content_publish`
   - `instagram_manage_insights`
5. Find your **Instagram User ID** from the Graph API Explorer
6. Paste both values into `.env`

---

## First-time setup

Open a Claude Code session in the project folder and run:

```
/instagram-init
```

GramPilot will create the `.instagram/` workspace, guide you through setting up your brand profile, and validate all credentials. You'll see something like:

```
✓ .instagram/ directory created
✓ Brand profile written to .instagram/memory/brand.md
✓ META_ACCESS_TOKEN validated (account: @yourhandle, expires: 2026-08-04)
✓ ANTHROPIC_API_KEY validated
✓ HF_API_TOKEN validated
✓ Setup complete. Run /instagram-plan to generate your first weekly calendar.
```

To re-run setup without losing existing plans: `/instagram-init --reset`

---

## Skill reference

### `/instagram-plan` — Generate your weekly content calendar

```
/instagram-plan
/instagram-plan --week 2026-24
/instagram-plan --theme "summer launch"
```

Claude generates a 7-item content calendar tailored to your brand profile and shaped by your previous week's performance data. The plan is saved as a readable Markdown file at `.instagram/memory/plans/YYYY-WW.md` — open it in any editor, tweak captions, swap themes, adjust timing, then approve it when you're happy.

---

### `/instagram-approve` — Lock the plan for asset generation

```
/instagram-approve
/instagram-approve --week 2026-23
```

Marks the plan as approved. The generate and publish skills require this step so you never accidentally push something you haven't reviewed.

---

### `/instagram-media` — Manage your creator media library

```
/instagram-media                                          # list all files
/instagram-media add ./photos/shot.jpg                   # add a photo or video
/instagram-media add ./videos/reel.mp4 --slot 2026-23-003 --desc "Recipe tutorial"
/instagram-media assign media-001 --slot 2026-23-004     # link a file to a plan slot
/instagram-media analyze                                  # build style profile from your photos
/instagram-media remove media-002
```

Accepted formats: `jpg`, `png`, `webp`, `heic`, `mp4`, `mov`, `mp3`, `wav`, `m4a`

**Style analysis** (`/instagram-media analyze`) reads your photos with Claude Vision and builds a visual identity profile. This profile is injected into every image generation prompt so AI-generated images stay on-brand. Adding a new photo triggers a re-analysis automatically.

---

### `/instagram-generate` — Create captions, images, and scripts

```
/instagram-generate
/instagram-generate --week 2026-23
/instagram-generate --item 2026-23-003
/instagram-generate --format carousel
```

For each approved item in the plan:

- **Creator file assigned** → your file is used directly, no AI generation
- **No creator file** → image generated via HuggingFace (your style profile applied)
- **Reel** → script generated only (you supply the video)
- **Carousel** → per-slide copy and images generated (2–10 slides)

Assets land in `.instagram/memory/assets/YYYY-WW/<item-id>/`. If image generation hits a rate limit, the item is marked `BLOCKED` so you can retry it individually later.

---

### `/instagram-publish` — Publish to Instagram

```
/instagram-publish
/instagram-publish --week 2026-23
/instagram-publish --item 2026-23-001
/instagram-publish --item 2026-23-003 --video /path/to/reel.mp4
```

Posts go live **immediately** via the Meta Graph API the moment you run this. The `intended_time` in the plan is a reminder only — use OS cron if you want timed publishing (see below).

GramPilot checks your token expiry before every publish: it warns you if fewer than 7 days remain, and stops if the token has expired.

---

### `/instagram-insights` — Fetch performance metrics

```
/instagram-insights
/instagram-insights --week 2026-23
/instagram-insights --item 2026-23-001
```

Pulls reach, impressions, and engagement rate for the specified week from the Meta API and saves the results locally. Run at least **48 hours after publishing** — Meta has a data latency window. Results are automatically used the next time you run `/instagram-plan`.

---

## Typical weekly workflow

```
Weekend (before Monday):
  cp ~/Photos/this-week/*.jpg .instagram/media/
  /instagram-media add .instagram/media/reel-video.mp4 --desc "Recipe tutorial"
  /instagram-media analyze          # update style profile with new photos

Monday morning:
  /instagram-plan                   # review .instagram/memory/plans/YYYY-WW.md
  /instagram-media                  # check assigned vs unassigned slots
  /instagram-media assign media-003 --slot 2026-23-002
  /instagram-approve
  /instagram-generate               # creator files used where assigned; AI fills the rest

Each day (at your posting time):
  /instagram-publish --item YYYY-WW-NNN

Following Monday:
  /instagram-insights               # fetch last week's performance (48h latency)
  /instagram-plan                   # next week, now informed by real data
```

---

## Scheduled publishing with cron

GramPilot publishes immediately when you run the skill. To publish automatically at a set time, add a cron entry:

```bash
crontab -e
```

Publish every day at 9 AM:

```cron
0 9 * * * cd /path/to/grampilot && claude -p "/instagram-publish" >> .instagram/memory/logs/cron.log 2>&1
```

---

## Direct CLI usage (without Claude Code)

All operations are also available as a standalone Python CLI:

```bash
python3 -m instagram_manager init
python3 -m instagram_manager plan --week 2026-23
python3 -m instagram_manager approve --week 2026-23
python3 -m instagram_manager generate --week 2026-23
python3 -m instagram_manager publish --item 2026-23-001
python3 -m instagram_manager insights --week 2026-23
python3 -m instagram_manager media list
python3 -m instagram_manager media add ./photo.jpg
python3 -m instagram_manager media analyze
```

---

## Configuration

`.instagram/config.yml` controls runtime behaviour:

```yaml
image_provider: huggingface     # or: replicate
style_analysis:
  enabled: true
  auto_update: true             # re-analyze when new photos are added
  max_photos: 20
meta_api_version: v18.0
```

### Image providers

| Provider | Cost | Capacity | Config key |
|---|---|---|---|
| HuggingFace Inference API | Free (rate-limited) | ~10–20 images/day | `huggingface` |
| Replicate | ~$0.005/image | Unlimited | `replicate` |

Set `REPLICATE_API_TOKEN` in `.env` to use Replicate.

---

## Workspace structure

```
.instagram/
├── config.yml                    # Runtime settings
├── media/                        # Your creator photos and videos (gitignored)
├── scripts/bash/                 # Shell helpers invoked by the skills
└── memory/
    ├── brand.md                  # Your brand profile (edit this directly)
    ├── style-profile.md          # Visual identity extracted by Claude Vision
    ├── media-index.json          # Creator media library index
    ├── plans/
    │   ├── YYYY-WW.md            # Human-readable weekly plan (review/edit here)
    │   └── YYYY-WW.json          # Machine-readable plan
    ├── assets/
    │   └── YYYY-WW/<item-id>/    # Generated images, captions, scripts
    ├── insights/
    │   └── YYYY-WW.json          # Performance metrics per week
    └── logs/
        └── events.jsonl          # Append-only structured event log
```

---

## Renewing your Meta token

The long-lived token expires after **60 days**. GramPilot warns you when fewer than 7 days remain.

To renew: go back to the Meta Developer setup, generate a new long-lived token, and update `META_ACCESS_TOKEN` in `.env`.

---

## Running tests

```bash
python3 -m pytest tests/ -v
```

95 tests across unit and integration suites. Integration tests use mocked HTTP responses — no live API calls needed.

---

## License

Apache 2.0

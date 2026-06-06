# Quickstart: Instagram Manager CLI Skills

**Branch**: `001-instagram-ai-agent`

## Prerequisites

- Claude Code CLI installed and authenticated (`claude --version`)
- Python 3.11+ installed (`python3 --version`)
- Instagram Business or Creator account connected to a Facebook Page
- Meta Developer account with a configured app (see step 2)

---

## Step 1 — Clone or navigate to the project

```bash
cd /path/to/studio2-manager
```

---

## Step 2 — Obtain Meta credentials (one-time)

1. Go to [developers.facebook.com](https://developers.facebook.com) → My Apps → Create App
2. Add the **Instagram Graph API** product
3. Under **Instagram → API Setup with Instagram Login**, connect your Instagram account
4. Generate a **Long-Lived User Access Token** (valid 60 days) with these permissions:
   - `instagram_basic`
   - `instagram_content_publish`
   - `instagram_manage_insights`
5. Find your **Instagram User ID** from the API response or the Graph API Explorer
6. Create `.env` in the project root:

```dotenv
META_ACCESS_TOKEN=your_long_lived_token_here
META_IG_USER_ID=your_instagram_user_id_here
ANTHROPIC_API_KEY=your_anthropic_key_here   # same key used by Claude CLI
IMAGE_PROVIDER=huggingface
HF_API_TOKEN=your_huggingface_token_here    # free account at huggingface.co
```

---

## Step 3 — Install Python dependencies

```bash
pip install anthropic requests python-dotenv rich huggingface_hub pytest pytest-mock
```

---

## Step 4 — Run `/instagram-init`

```
/instagram-init
```

Follow the interactive prompts to fill in your brand profile. At the end you will see:

```
✓ Setup complete. Run /instagram-plan to generate your first weekly calendar.
```

---

## Step 5 — Add your creator media (optional but recommended)

Drop your photos and videos into `.instagram/media/` directly:

```bash
cp ~/Photos/this-week/*.jpg .instagram/media/
cp ~/Videos/reel-tuesday.mp4 .instagram/media/
```

Or use the skill to add with annotations:

```
/instagram-media add .instagram/media/photo-001.jpg --desc "Product flat lay, morning light"
```

To build the visual style profile from your photos (improves AI image generation):

```
/instagram-media analyze
```

This reads your photos with Claude Vision and writes `.instagram/memory/style-profile.md`.

---

## Step 6 — Plan the week

```
/instagram-plan
```

The skill generates a 7-day content calendar and saves it to
`.instagram/memory/plans/YYYY-WW.md`. Open this file in any editor to review and edit
the copy, themes, or scheduled times.

---

## Step 7 — Assign media to plan slots (optional)

After planning, link specific creator files to posts:

```
/instagram-media assign media-001 --slot 2026-23-002
/instagram-media assign media-004 --slot 2026-23-003   # Reel video (required)
/instagram-media assign audio-ref --slot 2026-23-003   # Audio style reference
```

Run `/instagram-media` (no args) to see assigned vs unassigned files.

---

## Step 8 — Approve the plan

When satisfied with the plan:

```
/instagram-approve
```

---

## Step 9 — Generate creative assets

```
/instagram-generate
```

- Slots with a creator photo/video assigned → creator file used directly (no AI call)
- Slots without a creator asset → AI image generated using the style profile
- Reels → script generated (includes audio style section if audio reference assigned)

Assets saved under `.instagram/memory/assets/YYYY-WW/`.

---

## Step 10 — Publish

Run when you want a post to go live (posts publish **immediately**):

```
/instagram-publish              # All approved, asset-ready posts
/instagram-publish --item <id>  # Single post
```

---

## Step 11 — Fetch insights (after 48h)

After posts have been live for at least 48 hours:

```
/instagram-insights
```

Metrics are saved and will automatically inform the next `/instagram-plan` run.

---

## Typical weekly workflow

```
Before Monday (weekend):
  cp ~/Photos/this-week/*.jpg .instagram/media/
  /instagram-media add .instagram/media/reel-video.mp4 --desc "Recipe tutorial"
  /instagram-media analyze  (if new photos added — updates style profile)

Monday morning:
  /instagram-plan           → review .instagram/memory/plans/YYYY-WW.md
  /instagram-media          → assign creator files to slots
  /instagram-approve
  /instagram-generate       → creator files used where assigned; AI fills the rest

Each day (at desired post time):
  /instagram-publish --item YYYY-WW-NNN

Following Monday:
  /instagram-insights       → fetches performance metrics (48h latency)
  /instagram-plan           → next week, informed by insights + style profile
```

---

## Renewing the Meta token (every 60 days)

The token expires after 60 days. `/instagram-publish` warns when < 7 days remain.
To renew: repeat step 2, generate a new long-lived token, update `META_ACCESS_TOKEN` in `.env`.

---

## Optional: Automated daily publishing via cron

To publish a specific item automatically at 9am every day:

```bash
crontab -e
# Add:
0 9 * * * cd /path/to/studio2-manager && claude -p "/instagram-publish" >> .instagram/memory/logs/cron.log 2>&1
```

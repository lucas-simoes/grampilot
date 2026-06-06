# Data Model: Instagram Manager CLI Skills

**Branch**: `001-instagram-ai-agent` | **Date**: 2026-06-05 (updated with Creator Media Library)

All state is stored as local files under `.instagram/`. No database engine is required.

---

## BrandProfile

**File**: `.instagram/memory/brand.md` (human-readable Markdown, edited by operator)
**Created by**: `/instagram-init`
**Read by**: `/instagram-plan`, `/instagram-generate`

```markdown
# Brand Profile

account_handle: @handle
niche: [e.g., "fitness & nutrition", "home decor", "tech reviews"]
tone_of_voice: [e.g., "friendly and motivational", "professional and concise"]
target_audience: [e.g., "Brazilian women aged 25–35 interested in healthy living"]
language: [e.g., "pt-BR", "en-US"]
post_frequency: [e.g., "7 posts/week — 1 per day"]
content_pillars:
  - [pillar 1, e.g., "Educational tips"]
  - [pillar 2, e.g., "Behind the scenes"]
  - [pillar 3, e.g., "Product showcase"]
branded_hashtags:
  - "#handle"
  - "#brandcampaign"
content_restrictions:
  - [e.g., "No political content"]
  - [e.g., "No competitor mentions"]
image_style: [e.g., "bright, warm tones, minimal text overlay"]
```

**Validation rules**:
- `account_handle` MUST start with `@`
- `language` MUST be a valid BCP-47 tag
- `content_pillars` MUST have at least 2 entries

---

## StyleProfile

**File**: `.instagram/memory/style-profile.md`
**Created/updated by**: `/instagram-media analyze`
**Read by**: `/instagram-generate` (for AI image prompt enrichment)
**Triggered**: Manually by operator (`/instagram-media analyze`) OR automatically when
new photos are added via `/instagram-media add`

```markdown
# Visual Style Profile

generated_at: 2026-06-05T14:30:00Z
photo_sample_count: 8
photos_analyzed:
  - .instagram/media/photo-001.jpg
  - .instagram/media/photo-002.jpg
  ...

## Style Description

[Natural-language output from Claude Vision, e.g.:]

**Colour palette**: Warm earth tones dominating — terracotta, sand, and olive greens.
Backgrounds are consistently clean and uncluttered, often a single neutral colour.

**Lighting**: Natural window light, soft shadows, no harsh flash. Bright but not overexposed.

**Composition**: Subjects centered or rule-of-thirds. Consistent negative space on left side.
Flat-lay style frequent for product shots.

**Subject matter**: Food preparation close-ups, hands in action, finished dishes on minimal
tableware. Occasional lifestyle shots (person cooking, kitchen environment).

**Mood**: Calm, approachable, artisanal. Not clinical or corporate.

## Generation Prompt Suffix

[Compact style descriptor appended to AI generation prompts, e.g.:]
"warm earth tones, natural window light, soft shadows, clean neutral background,
flat-lay composition, artisanal calm mood, photorealistic"
```

**Validation rules**:
- `generated_at` MUST be ISO 8601
- `photo_sample_count` MUST match the length of `photos_analyzed`
- "Generation Prompt Suffix" section MUST be present and non-empty
- File is regenerated atomically (write-then-rename) to avoid partial reads

---

## CreatorMedia

**Directory**: `.instagram/media/` (flat, operator-managed)
**Index file**: `.instagram/memory/media-index.json`
**Managed by**: `/instagram-media`
**Read by**: `/instagram-generate`, `/instagram-media analyze`

**media-index.json**:
```jsonc
{
  "last_updated": "2026-06-05T14:00:00Z",
  "files": [
    {
      "id": "media-001",
      "filename": "photo-beach-sunset.jpg",
      "path": ".instagram/media/photo-beach-sunset.jpg",
      "type": "photo",                        // photo | video | audio
      "format": "jpg",                        // jpg, png, webp, heic, mp4, mov, mp3, wav, m4a
      "description": "Sunset at Copacabana, warm golden hour light",
      "assigned_item": "2026-23-002",         // ContentItem id or null
      "added_at": "2026-06-05T13:00:00Z",
      "used": false,                          // true once asset is copied to /assets/
      "included_in_style_profile": true       // true if used in last analyze run
    }
  ]
}
```

**Media type rules**:
| Type | Publishable | Role in system |
|------|-------------|----------------|
| photo | ✅ Yes | Direct publishable asset for feed/carousel/story; included in style analysis |
| video | ✅ Yes | Required publishable asset for Reels; NOT used in style analysis |
| audio | ❌ No | Soundtrack reference for Reels scripts only; never uploaded to platform |

**Validation rules**:
- Photos: MUST be convertible to 1080×1080 or 1080×1350 px (Pillow handles resizing)
- Videos: MUST be MP4 or MOV format for Meta API compatibility
- Audio: Accepted formats MP3, WAV, M4A; used for metadata extraction only
- `assigned_item` MUST reference a valid ContentItem id in the current plan, or be null
- One video MUST be assigned per Reel slot before `/instagram-publish` is attempted
- Audio files are accepted only when assigned to a Reel slot

---

## ContentPlan

**File**: `.instagram/memory/plans/YYYY-WW.md` (human-readable) and
`.instagram/memory/plans/YYYY-WW.json` (machine-readable)
**Created by**: `/instagram-plan`
**Modified by**: `/instagram-approve` (status transition)
**Read by**: `/instagram-generate`, `/instagram-publish`

```jsonc
{
  "week": "2026-23",
  "week_start": "2026-06-01",
  "week_end": "2026-06-07",
  "status": "draft",          // draft | approved | in_progress | completed
  "created_at": "2026-06-05T10:00:00Z",
  "approved_at": null,
  "items": [
    {
      "id": "2026-23-001",
      "day": "2026-06-01",
      "intended_time": "09:00",
      "format": "feed",        // feed | carousel | reel | story
      "theme": "...",
      "copy_draft": "...",
      "hashtags": {
        "broad": ["#tag1"],
        "niche": ["#tag2"],
        "branded": ["#handle"]
      },
      "slide_count": null,     // integer 2–10 for carousel; null otherwise
      "audio_ref": null,       // media-index id of linked audio file (Reel only)
      "status": "pending",     // pending | generating | generated | publishing | published | failed | blocked
      "assets": [],            // ContentAsset references (populated by /instagram-generate)
      "publish_event": null,   // PublishEvent reference
      "insights": null         // PostInsights reference
    }
  ]
}
```

**State transitions**:
```
ContentPlan:  draft → approved → in_progress → completed
ContentItem:  pending → generating → generated → publishing → published
                                              ↘ failed
                                              ↘ blocked  (missing required asset)
```

**Validation rules**:
- `format == "reel"` → a creator video MUST be assigned in `media-index.json` before publish
- `format == "reel" && audio_ref != null` → audio file MUST exist and be of type "audio"
- `hashtags` total count MUST NOT exceed 30
- `slide_count` MUST be 2–10 when `format == "carousel"`

---

## ContentAsset

**Files**: `.instagram/memory/assets/<YYYY-WW>/<item_id>/`
**Created by**: `/instagram-generate`
**Read by**: `/instagram-publish`

```
assets/2026-23/2026-23-001/
├── image_01.jpg          # Creator photo (resized) OR AI-generated image
├── caption.txt           # Final caption with hashtags appended
├── script.md             # Reels script (format == reel only)
└── manifest.json
```

**manifest.json**:
```jsonc
{
  "item_id": "2026-23-001",
  "format": "feed",
  "generated_at": "2026-06-05T11:00:00Z",
  "images": [
    {
      "filename": "image_01.jpg",
      "asset_source": "creator",           // "creator" | "ai-generated"
      "creator_media_id": "media-001",     // null if ai-generated
      "prompt": null,                      // AI prompt used (null if creator)
      "style_profile_used": false,         // true if style profile enriched the prompt
      "width": 1080,
      "height": 1080
    }
  ],
  "caption_file": "caption.txt",
  "script_file": null,
  "audio_style_section": false            // true if script includes audio style annotation
}
```

**Validation rules**:
- `asset_source` MUST be present in every image record
- For Reels: `script_file` MUST be non-null; no image required
- `audio_style_section: true` only when `format == "reel"` and `audio_ref != null`

---

## PublishEvent

**Appended to**: `.instagram/memory/logs/events.jsonl` (JSON Lines, append-only)

```jsonc
{
  "event_id": "evt-2026-23-001-pub",
  "timestamp": "2026-06-05T09:01:30Z",
  "skill": "instagram-publish",
  "item_id": "2026-23-001",
  "plan_week": "2026-23",
  "event_type": "published",
  "outcome": "success",
  "meta_post_id": "17924312312",
  "error": null,
  "retry_count": 0
}
```

---

## PostInsights

**File**: `.instagram/memory/insights/YYYY-WW.json`
**Created/updated by**: `/instagram-insights`
**Read by**: `/instagram-plan`

```jsonc
{
  "week": "2026-23",
  "fetched_at": "2026-06-12T10:00:00Z",
  "posts": [
    {
      "item_id": "2026-23-001",
      "meta_post_id": "17924312312",
      "format": "feed",
      "asset_source": "creator",          // carried from manifest.json for analysis
      "published_at": "2026-06-05T09:01:30Z",
      "metrics": {
        "reach": 1250,
        "impressions": 1840,
        "likes": 87,
        "comments": 12,
        "shares": 5,
        "saved": 23,
        "engagement_rate": 0.102
      },
      "data_available": true,
      "top_performer": false
    }
  ],
  "summary": {
    "best_format": "carousel",
    "best_time_slot": "09:00",
    "best_asset_source": "creator",       // which source performed better on average
    "avg_engagement_rate": 0.085,
    "top_item_id": "2026-23-003"
  }
}
```

**Note**: `asset_source` is tracked in insights so `/instagram-plan` can learn whether
creator-provided media or AI-generated images perform better for this account.

---

## AuthCredential

**File**: `.env` (never committed to git)

```dotenv
META_ACCESS_TOKEN=<long-lived user access token, 60-day validity>
META_IG_USER_ID=<Instagram user ID>
ANTHROPIC_API_KEY=<Claude API key — reuses operator's existing Claude CLI key>
IMAGE_PROVIDER=huggingface          # huggingface | replicate | stable-diffusion-local
HF_API_TOKEN=<HuggingFace token — free account>
REPLICATE_API_TOKEN=<optional>
```

---

## config.yml

**File**: `.instagram/config.yml`
**Created by**: `/instagram-init`

```yaml
image_provider:
  type: huggingface                 # huggingface | replicate | stable-diffusion-local
  model: stabilityai/stable-diffusion-xl-base-1.0
  # For local SD override:
  # type: stable-diffusion-local
  # endpoint: http://localhost:7860

style_analysis:
  max_photos: 10                    # Max photos per Claude Vision analysis run
  auto_update: true                 # Re-run analyze when /instagram-media add adds photos

media:
  accepted_photo_formats: [jpg, jpeg, png, webp, heic]
  accepted_video_formats: [mp4, mov]
  accepted_audio_formats: [mp3, wav, m4a]
  max_carousel_slides: 10
```

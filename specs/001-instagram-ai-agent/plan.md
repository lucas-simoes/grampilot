# Implementation Plan: Instagram Manager CLI Skills

**Branch**: `001-instagram-ai-agent` | **Date**: 2026-06-05 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-instagram-ai-agent/spec.md`

---

## Summary

Build a Claude Code skills framework (`/instagram-*`) that allows a single operator to manage
an Instagram Business account entirely through the Claude CLI. The framework mirrors Speckit's
architecture: a `.instagram/` directory houses configuration, templates, and state; a Python
package (`src/instagram_manager/`) provides all business logic; and Claude Code skill files
(`.claude/skills/instagram-*/`) expose each capability as an interactive slash command.

Core skills: `/instagram-init`, `/instagram-plan`, `/instagram-approve`, `/instagram-media`,
`/instagram-generate`, `/instagram-publish`, `/instagram-insights`.

Text generation: Anthropic Claude API (also used for Vision-based style analysis).
Image generation: Hugging Face Inference API (free tier) with pluggable backends.
Publishing: Meta Graph API (immediate publish — Meta API does not support scheduled publishing
for Instagram). State: local files (Markdown + JSON). Creator media library: `.instagram/media/`
with cached visual style profile at `.instagram/memory/style-profile.md`.

---

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**:
- `anthropic` ≥ 0.25 — Claude SDK for text generation and Vision (style analysis)
- `requests` ≥ 2.31 — Meta Graph API and image generation HTTP calls
- `python-dotenv` ≥ 1.0 — credential and config management from `.env`
- `rich` ≥ 13.0 — formatted CLI output (tables, progress, colour)
- `huggingface_hub` ≥ 0.21 — HuggingFace Inference API client
- `Pillow` ≥ 10.0 — image resizing to Instagram-required dimensions (1080×1080)
- `mutagen` ≥ 1.47 — audio file metadata extraction (duration, format, BPM hint)
- `pytest` ≥ 8.0 — testing
- `pytest-mock` ≥ 3.12 — mocking for unit tests
- `responses` ≥ 0.25 — HTTP response mocking for Meta/HF API tests

**Storage**: Local filesystem (Markdown + JSON files). No database.
- Plans: `.instagram/memory/plans/YYYY-WW.{md,json}`
- Assets: `.instagram/memory/assets/YYYY-WW/<item_id>/`
- Creator media: `.instagram/media/` (flat; operator-managed files)
- Style profile: `.instagram/memory/style-profile.md` (cached Claude Vision output)
- Insights: `.instagram/memory/insights/YYYY-WW.json`
- Event log: `.instagram/memory/logs/events.jsonl` (JSON Lines, append-only)
- Media index: `.instagram/memory/media-index.json` (tracks files, assignments, used status)

**Testing**: `pytest` with `responses` library for HTTP mocking. Meta API tested against
mocked responses. HuggingFace and Claude Vision calls mocked in unit tests.

**Target Platform**: Linux / macOS local workstation running Claude Code CLI

**Project Type**: Claude Code skills framework + Python backend package

**Performance Goals**:
- `/instagram-plan`: < 5 minutes for a 7-item weekly plan
- `/instagram-media analyze`: < 3 minutes to build style profile from up to 20 photos
- `/instagram-generate`: < 60 seconds per item (image + copy)
- `/instagram-publish`: < 30 seconds per post (Meta API call + confirmation)
- `/instagram-insights`: < 10 seconds per published post

**Constraints**:
- Zero recurring software licensing cost
- Single Instagram Business/Creator account per deployment
- All secrets via `.env`; never hardcoded or committed
- Posts publish immediately via Meta API (no native scheduled publish available)
- HuggingFace free tier: ~10–20 images/day; generation spread across week as needed
- Claude Vision sample: up to 10 photos per style analysis run (token budget)
- Creator media: photos (JPG/PNG/WebP/HEIC), videos (MP4/MOV), audio (MP3/WAV/M4A)

**Scale/Scope**: Single operator, ~7–14 posts/week, one account, media library up to ~500 MB/week

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Gate | Status |
|-----------|------|--------|
| I. AI Skills Architecture | Each capability MUST be a discrete Claude Code skill with a single responsibility | ✅ 7 skills defined; `/instagram-media` added for media library; each independently callable |
| II. Meta API Integration | All publishing MUST go through Meta Graph API; credentials via env vars | ✅ `/instagram-publish` uses Meta Graph API; tokens in `.env`; no hardcoding |
| III. Weekly Planning Discipline | Plan MUST include format, copy, hashtags, time, and rationale; stored in machine-readable format | ✅ `YYYY-WW.json` stores all required fields; planner reads brand profile + insights + style profile |
| IV. Multi-Format Creative Output | All 4 formats MUST have dedicated generation logic; format from plan; creator media takes precedence over AI generation | ✅ feed, carousel, reel, story handled in `generator.py`; creator media checked first; AI is fallback |
| V. Observability & Traceability | All events MUST be logged in structured JSON; insights retrieved and stored; style analysis source logged | ✅ `events.jsonl` for all skill events; `/instagram-insights` stores metrics; generator logs asset source |

**No violations.** No Complexity Tracking entries required.

---

## Project Structure

### Documentation (this feature)

```text
specs/001-instagram-ai-agent/
├── plan.md              # This file
├── research.md          # Phase 0 decisions
├── data-model.md        # Entities and file schemas
├── quickstart.md        # Operator onboarding guide
├── contracts/
│   └── skill-commands.md  # CLI skill contracts (inputs, outputs, errors)
└── tasks.md             # Phase 2 output (/speckit-tasks command)
```

### Source Code (repository root)

```text
.instagram/                          # Framework config + runtime state
├── config.yml                       # Provider settings (image backend, etc.)
├── media/                           # Creator-provided media files (operator-managed)
│   ├── photo-001.jpg                # Drop files here directly OR use /instagram-media add
│   ├── video-reel-001.mp4
│   └── audio-ref-001.mp3
├── memory/
│   ├── brand.md                     # Brand profile (created by /instagram-init)
│   ├── style-profile.md             # Cached visual style description (Claude Vision output)
│   ├── media-index.json             # Tracks all media files, assignments, used status
│   ├── plans/
│   │   ├── YYYY-WW.md              # Human-readable weekly plan (operator edits here)
│   │   └── YYYY-WW.json            # Machine-readable plan (consumed by skills)
│   ├── assets/
│   │   └── YYYY-WW/
│   │       └── YYYY-WW-NNN/        # Per-item asset directory
│   │           ├── image_01.jpg    # Creator photo copy OR AI-generated image
│   │           ├── caption.txt
│   │           ├── script.md       # Reels only (includes audio style section if ref assigned)
│   │           └── manifest.json   # Records asset source: "creator" or "ai-generated"
│   ├── insights/
│   │   └── YYYY-WW.json           # Performance metrics
│   └── logs/
│       └── events.jsonl            # Structured event log (append-only)
├── scripts/bash/                   # Thin bash entry points called by skills
│   ├── init.sh
│   ├── plan.sh
│   ├── approve.sh
│   ├── media.sh
│   ├── generate.sh
│   ├── publish.sh
│   └── insights.sh
└── templates/
    ├── brand-template.md           # Brand profile template for /instagram-init
    ├── plan-template.json          # Empty plan scaffold
    └── prompts/                    # Claude prompt templates (operator-editable)
        ├── plan-week.md
        ├── generate-caption.md
        ├── generate-hashtags.md
        ├── generate-carousel.md
        ├── generate-reel-script.md
        └── analyze-style.md        # Prompt for Claude Vision style extraction

.claude/skills/                     # Claude Code skill definitions
├── instagram-init/
│   └── README.md
├── instagram-plan/
│   └── README.md
├── instagram-approve/
│   └── README.md
├── instagram-media/
│   └── README.md                   # Skill for /instagram-media (add/list/analyze/remove)
├── instagram-generate/
│   └── README.md
├── instagram-publish/
│   └── README.md
└── instagram-insights/
    └── README.md

src/
└── instagram_manager/              # Python business logic package
    ├── __init__.py
    ├── cli.py                      # Entry: python -m instagram_manager <cmd> [args]
    ├── models.py                   # Dataclasses: ContentPlan, ContentItem, CreatorMedia, etc.
    ├── brand.py                    # Brand profile read/write
    ├── planner.py                  # Weekly calendar generation (Claude API)
    ├── generator.py                # Asset generation: creator-media-first, AI fallback
    ├── media.py                    # Media library: add, list, assign, analyze (Claude Vision)
    ├── publisher.py                # Meta Graph API publishing
    ├── insights.py                 # Meta Insights API fetching
    ├── meta_client.py              # Meta API HTTP client (requests wrapper)
    ├── image_client.py             # Pluggable image generation client (HF/Replicate/local SD)
    ├── storage.py                  # File-based CRUD for plans, assets, media index, logs
    └── logger.py                   # Structured JSONL event logger

tests/
├── unit/
│   ├── test_planner.py
│   ├── test_generator.py
│   ├── test_media.py               # Media library + style analysis (Vision mocked)
│   ├── test_publisher.py
│   ├── test_insights.py
│   ├── test_storage.py
│   └── test_models.py
└── integration/
    ├── test_meta_client.py         # HTTP mocked with responses library
    └── test_image_client.py

pyproject.toml                      # Project metadata + pinned dependencies
.env                                # Credentials (in .gitignore)
.gitignore                          # Must include: .env, .instagram/media/, .instagram/memory/assets/
```

**Structure Decision**: Single-project layout. The framework directory (`.instagram/`) and
the Python package (`src/instagram_manager/`) coexist at the repository root. Skills under
`.claude/skills/` call bash scripts in `.instagram/scripts/bash/` which invoke
`python -m instagram_manager <command>`. This mirrors Speckit's architecture exactly.

---

## Phase 0: Research Findings

Research complete. See [research.md](research.md) for full decisions and rationale.

**Key findings**:
1. **Meta API does not support scheduled publishing for Instagram** — posts publish
   immediately. Scheduling guidance lives in the content plan as operator reference.
2. **Free image generation**: Hugging Face Inference API (rate-limited free tier) is the
   default. Provider is pluggable via `config.yml`. Creator media bypasses this entirely.
3. **Storage**: File-based (Markdown + JSON) — no database required at this scale.
4. **Meta Insights API**: 48h data latency; `reach`, `impressions`, `engagement_rate`,
   `saves` available for feed/carousel; story insights available 24h only.
5. **Text + Vision generation**: Anthropic Claude API reuses operator's existing Claude CLI
   credentials. Same SDK handles both text (copy, scripts) and Vision (style analysis).
6. **Style analysis**: Claude Vision reads up to 10 creator photos per run; output cached
   to `style-profile.md`; regenerated only on explicit `/instagram-media analyze` or when
   new photos are added via the CLI command. Token-efficient approach.
7. **Audio handling**: `mutagen` extracts basic metadata (duration, format); Claude reads
   the metadata + operator description to infer musical style for Reels script annotation.
   Audio files are never uploaded to any platform.

---

## Phase 1: Design Artifacts

All Phase 1 artifacts complete and updated for Creator Media Library:
- [data-model.md](data-model.md) — all entity schemas including CreatorMedia and StyleProfile
- [contracts/skill-commands.md](contracts/skill-commands.md) — full CLI contracts including `/instagram-media`
- [quickstart.md](quickstart.md) — operator onboarding guide with media workflow

---

## Post-Design Constitution Re-Check

All 5 principles re-verified against final Phase 1 design:

| Principle | Verification |
|-----------|-------------|
| I. AI Skills Architecture | 7 discrete skills; `/instagram-media` added with its own `media.py` module; no skill shares implementation with another |
| II. Meta API Integration | `meta_client.py` is the sole Meta API caller; `META_ACCESS_TOKEN` from env; 7-day expiry warning in `/instagram-publish`; audio never sent to any platform |
| III. Weekly Planning Discipline | `YYYY-WW.json` is the machine-readable plan; planner reads `brand.md` + `style-profile.md` + `insights/YYYY-WW.json` before generating |
| IV. Multi-Format Creative Output | `generator.py` checks `media-index.json` for creator asset first; uses style-profile for AI prompt enrichment; Reels always require creator video |
| V. Observability & Traceability | `manifest.json` per asset records `asset_source: "creator" \| "ai-generated"`; `events.jsonl` logs all transitions; style analysis run logged with photo sample count |

✅ All gates pass. Implementation may proceed.

# Research: Instagram Manager CLI Skills

**Branch**: `001-instagram-ai-agent` | **Date**: 2026-06-05

## Decision 1 — Post Scheduling Strategy

**Decision**: Publish immediately via Meta Graph API; content plan stores intended times as
operator guidance. Optional `/instagram-schedule` generates OS cron entries for unattended
invocation.

**Rationale**: The Meta Graph API Content Publishing endpoint (`POST /<IG_ID>/media_publish`)
does **not** support a `scheduled_publish_time` parameter for Instagram posts. Native scheduling
is only available through the Instagram app UI and Meta Business Suite — not through the API.
Therefore, a "post is live the moment `/instagram-publish` runs" model is the only
API-compliant approach.

**Alternatives considered**:
- Meta API native scheduling: Does not exist for Instagram (only for Facebook Pages).
- Background daemon polling a queue: Rejected — violates CLI-first, no-daemon constitution;
  adds OS-level complexity with no benefit since operator can use cron directly.
- Meta Business Suite scheduling UI: Out of scope — the system exists to avoid manual UI work.

**Impact on spec**: SC-003 and US3 acceptance scenarios updated in plan.md to reflect
immediate-publish model. Scheduling discipline is enforced via the approved content plan
(which defines intended times) and optional cron integration.

---

## Decision 2 — Image Generation Provider

**Decision**: Hugging Face Inference API (free tier, rate-limited) as the default image
generation backend. The provider is pluggable via `.instagram/config.yml` so operators can
switch to Replicate, local Stable Diffusion, or any HTTP-compatible endpoint.

**Rationale**: No image generation service offers a genuinely unlimited free tier at
Instagram-ready resolution (1080×1080). The available options and their practical limits:

| Provider | Free Tier | Realistic Capacity | API Key Required |
|----------|-----------|-------------------|-----------------|
| Hugging Face Inference API | Rate-limited (free account) | ~10–20 images/day | Yes (free) |
| Pollinations.ai | 1 image/hour/IP | Too slow for batch | No |
| OpenArt | Daily credits | ~5–10/day | Yes (free) |
| Stability AI | 25 credits/month | ~25 images/month | Yes (free) |
| Replicate | Pay-as-you-go (~$0.005/image) | Unlimited | Yes (paid) |

For ~14 posts/week: Hugging Face Inference API (SDXL or FLUX.1-schnell) is the best zero-cost
option with spread-out generation. For higher volume, Replicate at ~$0.07/week is negligible.

**Alternatives considered**:
- Single fixed provider: Rejected — locks operators into one service and its rate limits.
- Local Stable Diffusion: Valid option for operators with GPU; supported as override, not
  default (requires ~4–8 GB VRAM and manual model download).
- DALL-E / Midjourney: Paid-only; violates zero-cost preference.

---

## Decision 7 — Image Hosting for Meta API

**Decision**: Use Meta's upload-session flow (`POST /<IG_USER_ID>/media` with
`media_type=IMAGE` and direct binary upload) to upload image bytes without requiring a
publicly accessible URL. For carousel containers, each slide is uploaded as a separate
session before the carousel container is created. Cloudinary free tier (25 GB storage /
25 GB bandwidth/month) is supported as a config-toggled URL-based fallback.

**Rationale**: Meta's Content Publishing API historically required a publicly accessible
`image_url`. The upload-session path allows direct binary submission from the local
filesystem, eliminating any external hosting dependency for the default flow. This keeps
the system self-contained and avoids introducing a CDN dependency.

**Alternatives considered**:
- Require a public `image_url`: Forces operators to maintain external hosting; adds
  infrastructure overhead incompatible with the zero-dependency local-first design.
- Cloudinary free tier (URL path): Viable fallback but rate-limited and adds an external
  account requirement. Retained as an optional config override.
- ngrok / temporary tunnel: Rejected — fragile, requires a running process, exposes
  local filesystem to the internet.

**Impact on tasks**: T048 is split into T048 (video/resumable upload, already defined)
and T048b (image upload-session flow). Carousel publishing uses T048b for each slide.

**Implementation note**: `image_client.py` abstracts the provider behind a single
`generate_image(prompt, size) -> bytes` interface. Provider selection is read from
`.instagram/config.yml` at runtime.

---

## Decision 3 — Storage Backend

**Decision**: Local filesystem with structured Markdown (human-readable) + JSON sidecar
(machine-readable). No database.

**Rationale**: At the scale of a single operator managing ~14 posts/week, a database adds
complexity with no benefit. File-based storage is:
- Human-readable (operator can inspect/edit plans in any text editor)
- Zero-dependency (no database engine to install or manage)
- Git-friendly (plans can be version-controlled)
- Sufficient for the access patterns (sequential read of weekly plans, append-only logs)

Storage layout:
```
.instagram/memory/
├── brand.md               # Brand profile (single file, edited by operator)
├── plans/YYYY-WW.md       # Human-readable weekly plan (operator reviews/edits here)
├── plans/YYYY-WW.json     # Machine-readable plan (consumed by skills)
├── assets/YYYY-WW/<id>/   # Generated images and script files
├── insights/YYYY-WW.json  # Performance metrics per week
└── logs/events.jsonl      # Structured event log (append-only)
```

**Alternatives considered**:
- SQLite: More queryable, but adds schema migration burden and reduces readability.
- PostgreSQL: Over-engineered for single-operator, local use case.

---

## Decision 4 — Python Module as Skill Backend

**Decision**: Business logic lives in a `src/instagram_manager/` Python package. Claude Code
skills (`.claude/skills/instagram-*/`) call Python modules via bash scripts in
`.instagram/scripts/bash/`. This mirrors Speckit's architecture (bash scripts back the
skill instructions).

**Rationale**: Claude Code skills are Markdown files that instruct Claude on what to do.
For repeatable, testable operations (API calls, file I/O), the logic must live in versioned,
testable code — not inline in the skill Markdown. Python is the natural choice given the
available SDKs (Anthropic, HuggingFace, requests).

**Alternatives considered**:
- Pure bash scripts: Hard to test, poor error handling, difficult to maintain complex logic.
- Inline Claude invocations only (no Python): Viable for text generation but not for API
  calls that require structured request/response handling and retry logic.

---

## Decision 5 — Meta Graph API Client

**Decision**: Thin Python wrapper around `requests` (or `httpx`) for Meta Graph API calls.
No third-party Meta SDK.

**Rationale**: The official Meta Python SDK is unmaintained. `requests` + a thin client
class with token management, rate-limit handling, and retry logic is the right level of
abstraction for the scope of this project.

**Key Meta API endpoints used**:
```
POST /v18.0/<IG_USER_ID>/media          # Create media container
POST /v18.0/<IG_USER_ID>/media_publish  # Publish container (immediate)
GET  /v18.0/<MEDIA_ID>/insights         # Post-level performance metrics
GET  /v18.0/<IG_USER_ID>               # Account info (for onboarding)
```

**Authentication**: Long-lived User Access Token (valid 60 days). Token stored in `.env`
as `META_ACCESS_TOKEN`. The `/instagram-init` skill provides instructions for token
generation; token refresh is a manual operator step with a reminder built into
`/instagram-publish` (warns if token expires within 7 days).

**Rate limits**: Meta does not publish exact limits for Instagram Content Publishing API.
The system applies a conservative default of 1 API call per 2 seconds between batch
operations to stay well within undocumented limits.

---

## Decision 6 — Text Generation via Claude API

**Decision**: Use the Anthropic Claude API (`claude-sonnet-4-6` or latest available) for
all text generation: copy drafts, captions, hashtag sets, carousel slide text, and Reels
scripts. The operator's existing Claude CLI credentials are reused — no additional API
key management required.

**Rationale**: The operator already has Claude API access (they are using Claude Code CLI).
Reusing the same credentials eliminates onboarding friction. Claude is the highest-quality
option for Instagram copy in the languages and tones required.

**Implementation**: The `planner.py` and `generator.py` modules call the Anthropic SDK
directly. Prompts are templated and stored in `.instagram/templates/prompts/` so operators
can customise them without editing Python code.

**Alternatives considered**:
- Open-source LLMs via Ollama/LM Studio: Viable but lower quality for marketing copy;
  offered as a future extension rather than default.
- Other commercial APIs (GPT-4, Gemini): Not free, and operator already has Claude access.

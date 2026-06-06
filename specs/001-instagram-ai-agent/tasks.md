---

description: "Task list for Instagram Manager CLI Skills"
---

# Tasks: Instagram Manager CLI Skills

**Input**: Design documents from `specs/001-instagram-ai-agent/`

**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/ ✅

**Tests**: Included for all phases — unit tests with mocked I/O and integration tests with
HTTP mocking (no live API calls in CI).

**Organization**: Tasks ordered by user story priority. Each story phase is independently
completable and testable without the phases that follow it.

## Format: `[ID] [P?] [Story?] Description — file path`

- **[P]**: Can run in parallel (different files, no shared incomplete dependencies)
- **[Story]**: Which user story this task belongs to (US1–US6)
- Exact file paths included in all task descriptions

---

## Phase 1: Setup

**Purpose**: Project skeleton, configuration files, and directory structure.

- [x] T001 Create Python package structure: `src/instagram_manager/__init__.py`, `src/instagram_manager/cli.py` (stub), `tests/__init__.py`, `tests/unit/__init__.py`, `tests/integration/__init__.py`
- [x] T002 Write `pyproject.toml` with all dependencies: `anthropic>=0.25`, `requests>=2.31`, `python-dotenv>=1.0`, `rich>=13.0`, `huggingface_hub>=0.21`, `Pillow>=10.0`, `mutagen>=1.47`, `pytest>=8.0`, `pytest-mock>=3.12`, `responses>=0.25`
- [x] T003 [P] Create `.gitignore` including `.env`, `.instagram/media/`, `.instagram/memory/assets/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`
- [x] T004 [P] Create `.instagram/config.yml` with default settings: `image_provider.type: huggingface`, `style_analysis.max_photos: 10`, `style_analysis.auto_update: true`, accepted format lists per data-model.md
- [x] T005 [P] Create `.instagram/templates/brand-template.md` following the BrandProfile schema in `data-model.md`
- [x] T006 [P] Create `.instagram/templates/prompts/` directory with six empty template files: `plan-week.md`, `generate-caption.md`, `generate-hashtags.md`, `generate-carousel.md`, `generate-reel-script.md`, `analyze-style.md`
- [x] T007 [P] Create `.env.example` documenting all required env vars: `META_ACCESS_TOKEN`, `META_IG_USER_ID`, `ANTHROPIC_API_KEY`, `IMAGE_PROVIDER`, `HF_API_TOKEN`, `REPLICATE_API_TOKEN` (optional)
- [x] T008 [P] Create `.instagram/scripts/bash/` directory with stub scripts: `init.sh`, `plan.sh`, `approve.sh`, `media.sh`, `generate.sh`, `publish.sh`, `insights.sh` — each calling `python -m instagram_manager <subcommand> "$@"`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure required by every user story phase.
**Independent test**: `pytest tests/unit/test_models.py tests/unit/test_storage.py` passes.

- [x] T009 Implement all data models in `src/instagram_manager/models.py`: `ContentPlan`, `ContentItem`, `HashtagSet`, `ContentAsset`, `CreatorMedia`, `StyleProfile`, `PublishEvent`, `PostInsights` — use Python dataclasses; include all fields and state enum values from `data-model.md`
- [x] T010 [P] Implement structured JSONL event logger in `src/instagram_manager/logger.py`: `append_event(skill, item_id, plan_week, event_type, outcome, **kwargs)` writing to `.instagram/memory/logs/events.jsonl`
- [x] T011 [P] Implement config loader in `src/instagram_manager/storage.py`: reads `.instagram/config.yml` and `.env` via `python-dotenv`; exposes typed config object
- [x] T012 Implement file-based storage operations in `src/instagram_manager/storage.py`: `save_plan`, `load_plan`, `update_item_status`, `save_media_index`, `load_media_index`, `save_insights`, `load_insights` — all paths relative to `.instagram/memory/`
- [x] T013 [P] Implement brand profile reader in `src/instagram_manager/brand.py`: `load_brand() -> BrandProfile` parsing `.instagram/memory/brand.md`; raises `BrandNotFound` if missing
- [x] T014 [P] Implement CLI entry point in `src/instagram_manager/cli.py` with `argparse` subcommand routing: `init`, `plan`, `approve`, `media`, `generate`, `publish`, `insights` — each subcommand calls the matching module
- [x] T015 [P] Write unit tests for `models.py` in `tests/unit/test_models.py`: state transition validation, hashtag count enforcement (≤30), carousel slide count bounds (2–10)
- [x] T016 [P] Write unit tests for `storage.py` in `tests/unit/test_storage.py`: round-trip `save_plan`/`load_plan`, `update_item_status` transitions, JSONL append ordering

---

## Phase 3: US1 — Weekly Content Planning

**Story goal**: Operator runs `/instagram-plan` and gets a complete 7-day calendar; approves it with `/instagram-approve`.
**Independent test**: Run `/instagram-plan` against a mock brand profile and verify `YYYY-WW.json` and `YYYY-WW.md` are created with all required fields; run `/instagram-approve` and verify status transitions to `approved`.

- [x] T017 [US1] Implement `/instagram-init` skill file at `.claude/skills/instagram-init/README.md`: interactive prompts for brand profile fields, credential validation, directory creation instructions; calls `python -m instagram_manager init`
- [x] T018 [US1] Implement `init` subcommand in `src/instagram_manager/brand.py`: create `.instagram/` directory tree (memory/, media/, scripts/bash/, templates/prompts/), write `brand.md` from template with operator answers, validate that `account_handle` starts with `@` and `content_pillars` ≥ 2
- [x] T019 [US1] Implement Meta API credential validation in `src/instagram_manager/meta_client.py`: `GET /v18.0/{IG_USER_ID}?fields=id,username` — returns account info or raises `AuthError`; used by `init` to confirm token validity
- [x] T020 [US1] Write prompt template `.instagram/templates/prompts/plan-week.md`: system prompt instructing Claude to generate a 7-item weekly calendar from brand profile + insights summary, outputting structured JSON per the `ContentItem` schema in `data-model.md`
- [x] T021 [US1] Implement weekly calendar generator in `src/instagram_manager/planner.py`: `generate_plan(week: str, theme: str | None) -> ContentPlan` — loads `brand.md`, loads previous insights if available, calls Claude API with `plan-week.md` prompt, parses response into `ContentPlan`, saves `YYYY-WW.json` + `YYYY-WW.md`
- [x] T022 [US1] Implement `/instagram-plan` skill file at `.claude/skills/instagram-plan/README.md`: invokes `python -m instagram_manager plan [--week] [--theme]`, displays calendar table using `rich`, shows file path for operator review
- [x] T023 [US1] Implement `approve` subcommand in `src/instagram_manager/storage.py`: load plan, assert status is `draft`, set status to `approved` and `approved_at` to now, save; raise `AlreadyApproved` if not draft
- [x] T024 [US1] Implement `/instagram-approve` skill file at `.claude/skills/instagram-approve/README.md`: invokes `python -m instagram_manager approve [--week]`, confirms item count and displays next-step message
- [x] T025 [US1] [P] Write unit tests for `planner.py` in `tests/unit/test_planner.py`: mock Claude API response, verify `ContentPlan` structure, verify `YYYY-WW.json` written, verify fallback when insights missing, verify `--theme` override applied

---

## Phase 4: US2 — Multi-Format Content Generation

**Story goal**: Operator runs `/instagram-generate` on an approved plan; each slot gets a caption, image (AI-generated), or script; failures are marked BLOCKED.
**Independent test**: Run `/instagram-generate --item <id>` against a single approved feed slot (no creator media assigned); verify `manifest.json` exists with `asset_source: "ai-generated"`, `caption.txt` non-empty, `image_01.jpg` present at 1080×1080.

- [x] T026 [US2] Write prompt templates for generation: `generate-caption.md` (feed/story), `generate-carousel.md` (per-slide copy), `generate-reel-script.md` (intro/body/CTA + audio style section placeholder), in `.instagram/templates/prompts/`
- [x] T027 [US2] Implement text asset generation in `src/instagram_manager/generator.py`: `generate_text_assets(item: ContentItem) -> dict` — calls Claude API with the appropriate prompt template (caption, carousel, or script); returns copy strings keyed by format
- [x] T028 [US2] Implement pluggable image generation client interface in `src/instagram_manager/image_client.py`: abstract `ImageClient` base class with `generate(prompt: str, size: tuple) -> bytes`; factory function reads `IMAGE_PROVIDER` from config
- [x] T029 [US2] Implement `HuggingFaceImageClient` in `src/instagram_manager/image_client.py`: calls HF Inference API for SDXL or configured model; includes retry (3×) with exponential backoff; raises `ImageGenerationError` on exhausted retries
- [x] T030 [US2] [P] Implement `ReplicateImageClient` in `src/instagram_manager/image_client.py`: calls Replicate API; same interface as HuggingFace client; activated when `IMAGE_PROVIDER=replicate`
- [x] T031 [US2] Implement image post-processing in `src/instagram_manager/image_client.py`: `resize_to_instagram(image_bytes, format) -> bytes` using Pillow — 1080×1080 for feed/story, 1080×1350 for portrait carousel; JPEG output
- [x] T032 [US2] Implement asset directory creation and `manifest.json` writer in `src/instagram_manager/storage.py`: `save_asset(item_id, week, filename, data)` and `write_manifest(item_id, week, manifest: ContentAsset)`
- [x] T033 [US2] Implement generation orchestrator in `src/instagram_manager/generator.py`: `generate_item(item: ContentItem)` — calls `generate_text_assets`, then calls image client for feed/carousel/story; sets item status to `generated` or `blocked`; writes all files + manifest; logs event
- [x] T034 [US2] Implement `/instagram-generate` skill file at `.claude/skills/instagram-generate/README.md`: invokes `python -m instagram_manager generate [--item] [--format] [--week]`; displays per-item progress with `rich`; summarises blocked items and retry commands
- [x] T035 [US2] [P] Write unit tests for `generator.py` in `tests/unit/test_generator.py`: mock Claude API and image client; verify manifest `asset_source`, verify BLOCKED status on image error, verify carousel produces N slide images
- [x] T036 [US2] [P] Write integration tests for `image_client.py` in `tests/integration/test_image_client.py`: mock HTTP responses for HF and Replicate; verify output is valid JPEG bytes at correct dimensions

---

## Phase 5: US6 — Creator Media Library

**Story goal**: Operator adds photos/videos/audio to `.instagram/media/`, runs `/instagram-media analyze` to build style profile, assigns files to slots; generation uses creator files first.
**Independent test**: Add a JPEG to `.instagram/media/`, run `/instagram-media add`; verify `media-index.json` updated. Run `/instagram-media analyze`; verify `style-profile.md` contains "Generation Prompt Suffix" section. Run `/instagram-generate --item <id>` for a slot with creator photo assigned; verify `manifest.json` has `asset_source: "creator"`.

- [x] T037 [US6] Implement media library CRUD in `src/instagram_manager/media.py`: `add_media(path, slot_id, description)`, `list_media()`, `assign_media(media_id, slot_id)`, `remove_media(media_id)` — all operations update `media-index.json`; `add_media` validates file format against accepted lists in config
- [x] T038 [US6] Implement drop-detection in `src/instagram_manager/media.py`: `sync_dropped_files()` — scans `.instagram/media/` for files not in `media-index.json`; adds them as unassigned entries; called at start of `add`, `list`, and `generate` subcommands
- [x] T039 [US6] Implement Claude Vision style analysis in `src/instagram_manager/media.py`: `analyze_style(max_photos: int) -> str` — loads up to `max_photos` creator photos, reads them as base64 for Claude's Vision API using `analyze-style.md` prompt template; writes result to `.instagram/memory/style-profile.md` including "Generation Prompt Suffix" section
- [x] T040 [US6] Write prompt template `.instagram/templates/prompts/analyze-style.md`: instructs Claude Vision to analyse image sample and output structured style description (colour palette, lighting, composition, mood) followed by a compact "Generation Prompt Suffix" suitable for appending to image generation prompts
- [x] T041 [US6] Implement audio metadata extraction in `src/instagram_manager/media.py`: `extract_audio_metadata(path) -> dict` using `mutagen` — reads duration, format, BPM if available; returns dict used by generator to annotate Reel scripts
- [x] T042 [US6] Integrate creator-media-first logic into `src/instagram_manager/generator.py`: before calling image client, check `media-index.json` for a photo/video assigned to the slot; if found, copy and resize the creator file instead of generating; set `manifest.asset_source = "creator"`; if Reel and audio ref assigned, append audio style section to script
- [x] T043 [US6] Integrate style profile into image generation: in `generator.py`, load `style-profile.md` "Generation Prompt Suffix" section; append to image generation prompt; set `manifest.style_profile_used = true`; log which source was used
- [x] T044 [US6] Implement auto-update trigger: in `src/instagram_manager/media.py`, after `add_media` for a photo file, check `config.style_analysis.auto_update`; if true, call `analyze_style()` automatically
- [x] T045 [US6] Implement `/instagram-media` skill file at `.claude/skills/instagram-media/README.md`: handles `add/list/assign/analyze/remove` subcommands per contract in `contracts/skill-commands.md`; displays library table with `rich`
- [x] T046 [US6] [P] Write unit tests for `media.py` in `tests/unit/test_media.py`: mock Claude Vision calls; verify `media-index.json` round-trip; verify audio metadata extraction; verify style-profile.md written; verify drop-detection finds new files

---

## Phase 6: US3 — Publishing & Scheduling

**Story goal**: Operator runs `/instagram-publish`; approved, asset-ready posts are submitted to Instagram immediately via Meta Graph API; failures are logged and surfaced.
**Independent test**: Run `/instagram-publish --item <id>` against a mock HTTP server returning a valid Meta API response; verify item status transitions to `published`, `meta_post_id` recorded, event logged.

- [ ] T047 [US3] Implement full Meta Graph API client in `src/instagram_manager/meta_client.py`: `create_media_container(IG_USER_ID, media_type, image_url | video_url, caption)` → `POST /v18.0/{IG_USER_ID}/media`; `publish_container(IG_USER_ID, container_id)` → `POST /v18.0/{IG_USER_ID}/media_publish`; retry up to 3× with 10s backoff on 5xx; raise `RateLimitError` on 429
- [ ] T048 [US3] Implement image/video upload helpers in `src/instagram_manager/publisher.py`: for each format (feed, carousel, story, reel), reads asset files from `manifest.json`, uploads binary to a temporary hosting location accessible by Meta API (or uses Meta's resumable upload for videos)
- [ ] T048b [US3] Implement image upload-session flow in `src/instagram_manager/publisher.py`: `upload_image(image_bytes: bytes) -> str` — creates an upload session via `POST /v18.0/<IG_USER_ID>/media` with `media_type=IMAGE`, uploads bytes directly, returns the container ID; handles carousel by creating one session per slide before the carousel container merge step; adds Cloudinary URL path as config-toggled fallback when `publisher.image_hosting=cloudinary` is set in `config.yml`
- [ ] T049 [US3] Implement token expiry check in `src/instagram_manager/publisher.py`: `check_token_expiry()` — reads `META_ACCESS_TOKEN` expiry from a cached `.instagram/memory/.token-meta` file (written by init); warns if < 7 days; raises `TokenExpiredError` if expired
- [ ] T050 [US3] Implement publishing orchestrator in `src/instagram_manager/publisher.py`: `publish_item(item: ContentItem)` — validates assets exist, checks token, uploads media, publishes container, records `meta_post_id`, updates item status, logs `PublishEvent`; handles `RateLimitError` with backoff
- [ ] T051 [US3] Implement `/instagram-publish` skill file at `.claude/skills/instagram-publish/README.md`: single-item and `--all` batch modes per `contracts/skill-commands.md`; displays per-item outcomes; surfaces token expiry warning
- [ ] T052 [US3] [P] Write unit tests for `publisher.py` in `tests/unit/test_publisher.py`: mock meta_client; verify status transitions, retry logic, token expiry warning, BLOCKED skipping
- [ ] T053 [US3] [P] Write integration tests for `meta_client.py` in `tests/integration/test_meta_client.py`: mock HTTP with `responses` library; verify container creation, publish, 3× retry on 5xx, 429 handling

---

## Phase 7: US4 — Hashtag Research & Optimization

**Story goal**: Each ContentItem in the plan has a HashtagSet with ≤30 hashtags across broad/niche/branded tiers.
**Independent test**: Call `generate_hashtags(theme, format, brand)` with a mock Claude response; verify returned HashtagSet total ≤ 30 and all three tiers present.

- [ ] T054 [US4] Write prompt template `.instagram/templates/prompts/generate-hashtags.md`: instructs Claude to output a JSON object with `broad` (10 tags), `niche` (15 tags), `branded` (up to 5 tags) arrays for the given post theme, format, and niche from brand profile
- [ ] T055 [US4] Implement hashtag generation in `src/instagram_manager/planner.py`: `generate_hashtags(theme, format, brand) -> HashtagSet` — calls Claude API with `generate-hashtags.md`; validates total ≤ 30; raises `HashtagLimitError` if response exceeds limit
- [ ] T056 [US4] Integrate hashtag generation into `generate_plan`: call `generate_hashtags` for each `ContentItem` in the plan; attach `HashtagSet` to item; append hashtag string to `copy_draft` in `YYYY-WW.md`
- [ ] T057 [US4] [P] Add hashtag validation to `models.py`: enforce total count ≤ 30 in `HashtagSet.__post_init__`; add to `test_models.py`

---

## Phase 8: US5 — Performance Insights & Feedback Loop

**Story goal**: Operator runs `/instagram-insights`; metrics retrieved for all published posts; next `/instagram-plan` references top performers.
**Independent test**: Mock Meta Insights API returning metrics for 3 posts; verify `YYYY-WW.json` written with correct `engagement_rate` computation, `top_performer: true` on highest; verify next `/instagram-plan` call includes performance summary in generated plan.

- [ ] T058 [US5] Implement Meta Insights API client in `src/instagram_manager/insights.py`: `fetch_insights(media_id: str) -> dict` — `GET /v18.0/{MEDIA_ID}/insights?metric=reach,impressions,likes,comments,shares,saved`; handles 48h latency (returns `data_available: false` if insufficient data)
- [ ] T059 [US5] Implement insights aggregation in `src/instagram_manager/insights.py`: `compute_summary(posts: list) -> dict` — finds `best_format`, `best_time_slot`, `best_asset_source`, `avg_engagement_rate`, `top_item_id`; computes `engagement_rate = (likes+comments+shares+saved)/reach`
- [ ] T060 [US5] Implement insights storage and top-performer tagging in `src/instagram_manager/insights.py`: `save_insights(week, posts)` writes `.instagram/memory/insights/YYYY-WW.json`; marks `top_performer: true` on highest engagement item
- [ ] T061 [US5] Implement `/instagram-insights` skill file at `.claude/skills/instagram-insights/README.md`: fetches metrics for all published items in the target week, displays summary table with `rich`, notes items with `data_available: false`
- [ ] T062 [US5] Integrate insights reader into `planner.py`: at start of `generate_plan`, load insights from previous week if available; prepend a performance summary section to the Claude prompt so next week's plan is informed by top performers and best formats
- [ ] T063 [US5] [P] Write unit tests for `insights.py` in `tests/unit/test_insights.py`: mock Meta API responses; verify `engagement_rate` formula, `top_performer` assignment, `data_available: false` for recent posts, `best_asset_source` computation

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, error message consistency, prompt quality, and final validation.

- [ ] T064 Fill all six prompt template files in `.instagram/templates/prompts/` with production-quality prompt text matching the `plan-week.md`, `generate-caption.md`, `generate-hashtags.md`, `generate-carousel.md`, `generate-reel-script.md`, `analyze-style.md` roles defined in `research.md`
- [ ] T065 [P] Validate and finalise all seven `.claude/skills/instagram-*/README.md` skill files: ensure each matches the exact invocation syntax, inputs, outputs, and error messages specified in `contracts/skill-commands.md`
- [ ] T066 [P] Update all eight `.instagram/scripts/bash/` scripts: ensure each passes all CLI flags through to `python -m instagram_manager`; add `set -e` and basic error output
- [ ] T067 [P] Add `rich` progress display to `generator.py` batch mode: per-item `[N/total] item_id format ✓/✗` line; final summary count (success / blocked / failed)
- [ ] T068 [P] Validate `.env` completeness at CLI startup in `src/instagram_manager/cli.py`: check required vars present before any subcommand runs; surface clear missing-var message with reference to `.env.example`

---

## Dependencies (Story completion order)

```
Phase 1 (Setup)
  └─ Phase 2 (Foundational: models, storage, logger)
       └─ Phase 3 (US1: Planning + Init)
            ├─ Phase 4 (US2: Generation — text + AI images)
            │    └─ Phase 5 (US6: Creator Media Library — enhance generation)
            │         └─ Phase 6 (US3: Publishing)
            └─ Phase 7 (US4: Hashtags — enhances Phase 3 planner)

Phase 6 (US3: Publishing)
  └─ Phase 8 (US5: Insights — requires published posts)
       └─ Phase 3 re-run (planning now informed by insights)

Phase 9 (Polish — can start after Phase 4)
```

---

## Parallel Execution Examples

**Within Phase 2** (all independent files):
```
T010 logger.py  ||  T011 config/storage.py  ||  T013 brand.py  ||  T015 test_models.py  ||  T016 test_storage.py
```

**Within Phase 4** (after T027 generator.py core exists):
```
T030 ReplicateImageClient  ||  T035 test_generator.py  ||  T036 test_image_client.py
```

**Within Phase 5** (after T037 media CRUD exists):
```
T041 audio metadata  ||  T046 test_media.py
```

**Within Phase 6** (after T047 meta_client exists):
```
T052 test_publisher.py  ||  T053 test_meta_client.py
```

---

## Implementation Strategy — MVP Scope

**MVP = Phase 1 + Phase 2 + Phase 3** (T001–T025)

After MVP: the operator can run `/instagram-init`, `/instagram-plan`, and `/instagram-approve`.
The plan is saved with all content items, copy drafts, and placeholders for assets.

**Increment 2** = + Phase 4 (T026–T036): adds AI image generation and Reels scripts.

**Increment 3** = + Phase 5 (T037–T046): adds creator media library and style analysis.

**Increment 4** = + Phase 6 (T047–T053): adds live publishing to Instagram.

**Increment 5** = + Phase 7 + Phase 8 (T054–T063): adds hashtag optimization and insights loop.

**Increment 6** = Phase 9 (T064–T068): polish and production readiness.

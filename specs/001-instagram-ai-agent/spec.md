# Feature Specification: Instagram Manager CLI Skills

**Feature Branch**: `001-instagram-ai-agent`

**Created**: 2026-06-05

**Status**: Draft

**Input**: User description: "Eu quero criar um agente de IA usando skills especificas para criar
conteúdo para o Instagram. Preciso que o agente gere criativos, carrosséis e outras mídias para o
instagram. Ele deve planejar semanalmente, tipos de conteúdo, horarios, hastags, etc. Deve
conseguir se conectar as apis da meta para postar e agendar a postagem. Priorize soluções
open-source e de custo zero, sempre que possível."

**Clarification**: The system is a framework of Claude Code slash commands (`/instagram-*`),
mirroring Speckit's structure (`.instagram/` directory with skills, templates, scripts, and
memory). The operator manages the Instagram page interactively through the Claude CLI — there is
no autonomous background agent.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Weekly Content Planning (Priority: P1)

A social media manager invokes `/instagram-plan` in the Claude CLI to generate a complete 7-day
content calendar for the upcoming week. The calendar includes post themes, content format (feed,
carousel, reel, or story), copy drafts in the account's tone of voice, suggested hashtag sets,
and optimal publishing times. The operator reviews the plan interactively, makes edits inline,
and approves it with `/instagram-approve` — only then are assets generated and posts scheduled.

**Why this priority**: Planning is the foundation of every other capability. Without a structured
weekly plan, content generation and publishing cannot be coordinated. It is the highest-value
deliverable because it replaces hours of manual editorial work.

**Independent Test**: Can be fully tested by running `/instagram-plan` and verifying that a
complete, structured calendar is produced with all required fields filled for all 7 days —
without requiring publishing or image generation to work.

**Acceptance Scenarios**:

1. **Given** the operator runs `/instagram-plan`, **When** the skill completes, **Then** a
   structured calendar file is saved locally containing at least one post per day, each with
   format, copy draft, hashtag set, and scheduled time.
2. **Given** a weekly plan in draft state, **When** the operator edits a post's copy and runs
   `/instagram-approve`, **Then** the plan transitions to approved state and becomes eligible
   for asset generation and scheduling.
3. **Given** the plan is not approved, **When** the operator attempts to run `/instagram-publish`,
   **Then** the skill refuses and displays a clear message requiring approval first.

---

### User Story 2 - Multi-Format Creative Content Generation (Priority: P2)

A content creator invokes `/instagram-generate` in the Claude CLI to produce ready-to-use
content assets for all approved posts in the weekly plan. For feed posts, the skill generates a
composed image and final caption. For carousels, it produces a sequence of slide images with
individual copy. For Reels, it generates a structured script and thumbnail description. For
Stories, it produces layout copy and visual guidance. All assets are saved locally and linked to
their plan entries.

**Why this priority**: Content generation is the core differentiator of the skill set. Without
automated asset creation, the operator still has to produce content manually. It depends on an
approved plan (P1) but delivers the most tangible, time-saving output.

**Independent Test**: Can be fully tested by running `/instagram-generate --item <id>` against a
single approved ContentItem and verifying that the correct assets are produced for that format —
without requiring the planner or publishing skills to work.

**Acceptance Scenarios**:

1. **Given** an approved feed post, **When** the operator runs `/instagram-generate`, **Then** a
   composed image and a final caption (with hashtags) are produced and saved locally.
2. **Given** an approved carousel with 5 slides, **When** the skill runs, **Then** 5 slide images
   with individual copy texts are saved in order and linked to the plan entry.
3. **Given** an approved Reels entry, **When** the skill runs, **Then** a structured script
   (intro, body, CTA) and a thumbnail description are saved.
4. **Given** image generation fails for any item, **When** the skill encounters the error,
   **Then** the failure is logged with a clear reason, and that item is marked as blocked so
   the operator can decide whether to retry, skip, or provide an asset manually.

---

### User Story 3 - Publishing & Scheduling (Priority: P3)

A social media manager invokes `/instagram-publish` in the Claude CLI to submit approved,
asset-ready posts to Instagram. The skill handles the platform connection, token management, and
post submission. The operator does not interact with the Instagram app directly. If a post fails
to publish, the skill surfaces a clear error message immediately in the CLI session.

**Why this priority**: Publishing closes the loop from plan to live content. It depends on both
an approved plan (P1) and generated assets (P2). Its value is the elimination of any manual
steps inside the Instagram app.

**Independent Test**: Can be fully tested by running `/instagram-publish --item <id>` with a
single approved, asset-ready ContentItem and verifying that the post appears on Instagram and
the event is logged — without requiring the planner or generator to run.

**Acceptance Scenarios**:

1. **Given** an approved post with generated assets, **When** the operator runs
   `/instagram-publish`, **Then** the post is submitted to Meta Graph API immediately,
   the platform's post identifier is stored in the ContentItem, the item is marked as
   `published`, and the event is logged with the intended scheduled time as a reference field.
2. **Given** a batch of approved posts ready to publish, **When** the operator runs
   `/instagram-publish --all`, **Then** all items are submitted in sequence, each with their
   respective scheduled times, without exceeding platform rate limits, and a summary is shown.
3. **Given** the platform token is expired, **When** the operator runs `/instagram-publish`,
   **Then** the skill halts immediately, displays a re-authentication message with instructions,
   and no post is submitted.

---

### User Story 5 - Performance Insights & Feedback Loop (Priority: P5)

A content strategist invokes `/instagram-insights` in the Claude CLI to retrieve performance
metrics for all published posts from the previous week (reach, impressions, engagement rate,
saves). The skill stores the data locally alongside each ContentItem. When the operator next
runs `/instagram-plan`, the planner reads the insights and adjusts its recommendations —
favouring formats, themes, and time slots that performed above the account average.

**Why this priority**: Closing the feedback loop transforms the system from a static scheduler
into a learning content manager. It depends on published posts (P3) and enhances planning
(P1), making it a value-adding enhancement rather than a core dependency.

**Independent Test**: Can be fully tested by running `/instagram-insights` and verifying that
metrics are fetched for all posts with a platform post identifier and saved locally — without
requiring the planner or generator to run. Separately testable: verify that `/instagram-plan`
output references past performance when insights data is available.

**Acceptance Scenarios**:

1. **Given** at least one post has been published with a platform post identifier, **When** the
   operator runs `/instagram-insights`, **Then** reach, impressions, and engagement rate are
   fetched and stored for each published post.
2. **Given** insights data exists for the previous week, **When** the operator runs
   `/instagram-plan`, **Then** the generated plan includes a brief performance summary and
   adjusts format/time-slot suggestions based on top-performing entries.
3. **Given** no insights data exists yet (first week), **When** the operator runs
   `/instagram-plan`, **Then** the planner falls back to brand-profile-only recommendations
   and notes that insights will be available after the first publishing cycle.

---

### User Story 4 - Hashtag Research & Optimization (Priority: P4)

A content strategist wants each post to include a curated hashtag set that maximises organic
reach. The agent selects hashtags based on the post's theme, format, and target audience,
grouping them into three tiers: broad (high reach), niche (engaged community), and branded
(account-specific). The set respects the platform's 30-hashtag limit.

**Why this priority**: Hashtag optimization directly affects reach but is not blocking for the
core MVP. It enhances the weekly plan and can be generated as part of P1, so it is a
value-add rather than a foundation.

**Independent Test**: Can be fully tested by providing a post theme and format and verifying
that the agent returns a valid hashtag set with all three tiers represented and a total count
within the platform limit — independently of content generation or publishing.

**Acceptance Scenarios**:

1. **Given** a post with theme "home cooking, Italian pasta" and format "carousel", **When** the
   hashtag skill runs, **Then** a set of ≤30 hashtags is returned, grouped into broad, niche,
   and branded tiers.
2. **Given** a hashtag set is generated, **When** it is attached to a ContentItem,
   **Then** the full set (with tier labels) is stored and included in the generated caption.

---

### User Story 6 - Creator Media Library (Priority: P3)

A content creator drops their own photos, videos, and audio clips into the
`.instagram/media/` folder (or uses `/instagram-media add`) before the generation step.
When `/instagram-generate` runs, it checks for creator-provided assets for each plan slot
first: if a matching file exists, it uses it directly and skips AI image generation for that
item. When no creator asset is available, it falls back to AI image generation using visual
style patterns extracted from the existing media library. The `/instagram-plan` skill also
reads the media library to understand the creator's visual aesthetic and incorporate it into
its theme recommendations.

**Why this priority**: Creator-provided media produces more authentic, higher-quality content
than AI-generated images and eliminates the Reels publishing gap (where a real video is
required). It sits between generation (P2) and publishing (P3) because it directly feeds the
generation step and unblocks Reels.

**Independent Test**: Can be fully tested by adding a photo to `.instagram/media/`, running
`/instagram-generate` for a single feed slot, and verifying that the creator's photo is used
as the asset instead of an AI-generated image — without requiring publishing or insights.

**Acceptance Scenarios**:

1. **Given** a creator photo is present in `.instagram/media/` and assigned to a plan slot,
   **When** `/instagram-generate` runs for that slot, **Then** the creator photo is copied to
   the asset directory and no image generation API call is made.
2. **Given** a creator video is present in `.instagram/media/` for a Reels slot, **When**
   `/instagram-publish` runs, **Then** the creator video is uploaded directly without
   requiring the operator to provide a separate file path.
3. **Given** `.instagram/memory/style-profile.md` exists and a slot has no creator asset,
   **When** `/instagram-generate` runs, **Then** it reads the cached style profile and
   includes the style description in the AI image generation prompt — no photos are read
   at generation time. Given no style profile exists yet, `/instagram-generate` warns the
   operator and suggests running `/instagram-media analyze` first.
4. **Given** a creator adds a media file with no assigned plan slot, **When**
   `/instagram-media` lists the library, **Then** unassigned files are shown separately so
   the operator can link them to upcoming slots.
5. **Given** the creator drops a file directly into `.instagram/media/` without using the
   CLI command, **When** `/instagram-media` or `/instagram-generate` is next invoked, **Then**
   the new file is detected automatically and listed as an unassigned asset available for use.

---

### Edge Cases

- What happens when the AI generation service is unavailable during weekly planning? The plan
  generation fails gracefully with an error message; no partial plan is persisted.
- What happens when a generated image is rejected by the platform's content policy? The item is
  flagged, the operator is notified with the rejection reason, and the slot is skipped.
- What happens when two posts are scheduled at exactly the same time? The system serialises them
  with a configurable gap (default: 1 minute) and logs the adjustment.
- What happens when the operator never approves the weekly plan? No content is generated or
  published; the plan remains in draft state indefinitely.
- What happens when the platform API returns a transient error during publishing? The agent
  retries up to 3 times with exponential backoff before marking the item as failed and notifying
  the operator.
- What happens when a creator media file is assigned to a plan slot but the file format is
  incompatible with the post format (e.g., an audio file assigned to a feed image slot)? The
  system flags the item as BLOCKED, notifies the operator with the incompatibility reason, and
  does not proceed with generation or publishing for that slot.
- What happens when the creator replaces a media file after assets have already been generated?
  The operator must re-run `/instagram-generate --item <id>` to regenerate the asset; the
  system does not auto-detect file changes.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-000**: The system MUST provide an `/instagram-init` skill that creates the
  `.instagram/` directory structure and guides the operator through configuring the brand
  profile (`.instagram/memory/brand.md`) and platform credentials on first use.
- **FR-001**: The system MUST generate a complete 7-day content calendar on demand, containing
  for each day: at least one post entry with format, theme, copy draft, hashtag set, and
  scheduled publishing time. Planning MUST be informed by the brand profile.
- **FR-002**: The system MUST support four content formats: single-image feed post, multi-image
  carousel (2–10 slides), Reels (script + thumbnail description), and Story.
- **FR-003**: The system MUST require explicit operator approval of the weekly plan before
  generating assets or scheduling any publication.
- **FR-004**: The system MUST generate content assets for each approved plan entry according to
  its format. When a creator-provided media file is assigned to the slot, it MUST be used as
  the primary asset. When no creator asset is assigned, the system falls back to a free-tier
  image generation API. Local image generation (e.g., Stable Diffusion) MUST be supported as
  an optional operator-configured override. Reels MUST always require a creator-provided video.
- **FR-015**: The system MUST provide an `/instagram-media` skill that allows the operator to
  add (with optional slot assignment and description), list, and remove creator-produced media
  files in `.instagram/media/`. Media MUST also be ingestible by direct file drop — the skill
  auto-detects new files dropped into the folder when invoked. Each file may optionally be
  assigned to a specific ContentItem slot. Audio files MUST be accepted and linked to Reel
  slots as soundtrack reference; the Reels script.md MUST include a musical style section
  when an audio reference is assigned. Audio files are never published to the platform.
- **FR-016**: The system MUST maintain a cached visual style profile at
  `.instagram/memory/style-profile.md`, generated by Claude Vision reading a sample of
  creator photos in the media library. This profile MUST be used by `/instagram-generate`
  to enrich AI image generation prompts. The profile MUST be (re)generated when the operator
  runs `/instagram-media analyze` or adds new photos via the CLI command; it MUST NOT be
  re-generated on every `/instagram-generate` call. When no photos exist in the library,
  the skill falls back to brand-profile style guidance and notes the absence in its output.
- **FR-017**: The `/instagram-generate` skill MUST check for a creator-assigned media file
  before invoking any image generation API. Creator assets take precedence; AI generation is
  a fallback only. The decision MUST be logged (which source was used and why).
- **FR-005**: The system MUST expose a `/instagram-publish` skill that submits approved,
  asset-ready posts to Instagram immediately via the Meta Graph API. The post's intended
  publishing time (from the content plan) is stored as operator reference only — actual
  publication occurs the moment the skill runs. The skill MUST support both single-item
  and batch modes.
- **FR-006**: The system MUST generate hashtag sets of up to 30 hashtags per post, organised
  into broad, niche, and branded tiers.
- **FR-007**: The system MUST log every content generation, scheduling, and publishing event
  with timestamp, format, content identifier, and outcome status.
- **FR-008**: Each skill MUST display a clear, actionable status message at completion,
  including: what succeeded, what failed, and what the operator must do next (e.g., approve
  the plan, re-authenticate, retry a failed item, or provide a missing asset manually).
- **FR-009**: The system MUST handle platform authentication token expiration by pausing all
  publishing activity and alerting the operator — no silent failures.
- **FR-010**: The system MUST retry failed publishing attempts up to 3 times before marking an
  item as permanently failed and notifying the operator.
- **FR-011**: The system MUST be built using open-source components for all local processing,
  scheduling, and storage. External paid dependencies MUST be limited to the AI text/image
  generation service and the Instagram publishing platform.
- **FR-012**: The system MUST store all content plans, generated assets, and event logs locally
  in a structured, human-readable format.
- **FR-013**: The system MUST provide an `/instagram-insights` skill that retrieves reach,
  impressions, and engagement rate for all published posts via the Meta Insights API and
  stores the results alongside each ContentItem.
- **FR-014**: The `/instagram-plan` skill MUST read available insights data and use it to
  inform format, theme, and time-slot recommendations; when no insights data exists, the
  skill MUST fall back to brand-profile-only recommendations and notify the operator.

### Key Entities

- **BrandProfile**: The account's identity and content guidelines. Attributes: niche/industry,
  tone of voice, target audience description, recurring content themes, branded hashtags,
  content restrictions, account handle. Stored in `.instagram/memory/brand.md`.
- **ContentPlan**: A weekly content calendar. Attributes: week starting date, creation date,
  status (draft / approved / in-progress / completed), list of ContentItems.
- **ContentItem**: A single planned post. Attributes: format, theme, copy draft, hashtag set,
  scheduled time, asset references, status (pending / generated / published / failed),
  platform post identifier (after publishing).
- **HashtagSet**: A set of hashtags for a ContentItem. Attributes: broad-tier tags, niche-tier
  tags, branded-tier tags, total count.
- **ContentAsset**: A generated file or text artefact. Attributes: type (image / script /
  carousel-slide), content item reference, file path or text content, generation timestamp.
- **PublishEvent**: A log entry for a scheduling or publishing action. Attributes: content item
  reference, event type, timestamp, outcome, error detail (if applicable).
- **PostInsights**: Performance data for a published post. Attributes: content item reference,
  platform post identifier, reach, impressions, engagement rate, saves, fetch timestamp.
- **CreatorMedia**: A media file produced by the human creator. Attributes: file path, media
  type (photo / video / audio), description (optional), assigned content item (optional),
  date added, used status. Photos and videos may be published as post assets. Audio files are
  reference-only (soundtrack style notes for Reels scripts) and are never uploaded to the
  platform. Stored in `.instagram/media/`.
- **StyleProfile**: A cached natural-language description of the creator's visual aesthetic,
  generated by Claude Vision from the photo library. Attributes: generated timestamp, sample
  photo count, style description (colour palette, composition, lighting, subject style, mood).
  Stored in `.instagram/memory/style-profile.md`. Read by `/instagram-generate`; regenerated
  by `/instagram-media analyze`.
- **AuthCredential**: Platform authentication tokens. Attributes: account identifier, token
  value (encrypted at rest), expiration timestamp, last refresh timestamp.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A complete 7-day content calendar is generated within 5 minutes of the operator's
  request, with all required fields populated for every post entry.
- **SC-002**: All four Instagram content formats can be generated end-to-end after the plan is
  approved; feed, carousel, and story use creator media when available, falling back to AI
  generation; Reels always require a creator-provided video file.
- **SC-003**: 100% of posts submitted via `/instagram-publish` receive a platform-issued
  post identifier, which is stored locally alongside the ContentItem and written to the
  event log. Actual publication is immediate; intended publish times are preserved in the
  content plan as operator reference.
- **SC-004**: Zero posts are published without explicit operator approval of the containing plan.
- **SC-005**: The operator is notified of any failure (generation, scheduling, or publishing)
  within 5 minutes of the failure occurring.
- **SC-006**: The full system runs on open-source components with no recurring software licensing
  cost — external API usage costs (AI service, platform API) are the only possible expenses.
- **SC-007**: A new Instagram account can be fully onboarded (brand profile created, credentials
  configured via `/instagram-init`, first plan generated and approved) within 30 minutes.
- **SC-008**: After the first publishing cycle, `/instagram-insights` retrieves and stores
  performance metrics for all published posts; the subsequent `/instagram-plan` output
  explicitly references those metrics in its recommendations.

## Clarifications

### Session 2026-06-05

- Q: What is the primary execution model for the system? → A: Option A — Claude Code skills
  (`/instagram-*`) with a `.instagram/` directory structure mirroring Speckit's `.specify/`.
  The operator manages Instagram interactively through the Claude CLI; no autonomous background
  agent or daemon process.
- Q: How does the system handle posts scheduled for a future time? → A: Option A — Meta API
  native scheduling. The operator runs `/instagram-publish` at any time before the target slot;
  the skill submits the post with a `scheduled_publish_time` and the platform handles the
  actual publication. No local cron or daemon required.
- Q: How does the system generate images and creative assets? → A: Option C — Free-tier image
  generation API (e.g., Replicate free tier, Stability AI free tier). The system calls an
  external API at zero cost within the free quota; local Stable Diffusion may be offered as
  an optional override for operators who have GPU hardware available.
- Q: How does the system know the account's brand voice, niche, and content guidelines? →
  A: Option A — a persistent brand profile at `.instagram/memory/brand.md`, created once via
  `/instagram-init` and read automatically by all skills. Includes: niche, tone of voice,
  target audience, recurring themes, branded hashtags, and content restrictions.
- Q: Should the system fetch post performance data (reach, engagement) to inform future
  planning? → A: Option A — yes. A dedicated `/instagram-insights` skill retrieves metrics
  for published posts via the Meta Insights API and stores them locally. The `/instagram-plan`
  skill reads this data to inform format, theme, and time-slot recommendations.
- Q: Should the agent have access to videos, photos, and audio produced by the human creator
  as reference? → A: Option C — dual use. Creator media deposited in `.instagram/media/` is
  used as the primary publishable asset when present (bypassing AI image generation for that
  slot), AND analysed to inform visual style for AI-generated images when no creator asset is
  available. A new `/instagram-media` skill manages the media library.
- Q: How does the creator deposit media files into the library? → A: Option C — both methods
  supported. Direct file drop into `.instagram/media/` (zero-friction, auto-detected on next
  skill run); AND `/instagram-media add <file> [--slot <id>] [--desc "..."]` for annotated
  ingestion with slot assignment and description for style analysis.
- Q: How does the agent analyse creator photos for visual style extraction? → A: Option A —
  Claude Vision. When generating AI images for slots without a creator asset, the skill reads
  a sample of creator photos directly using Claude's multimodal capability and produces a
  natural-language style description (colour palette, composition, lighting, subject style).
  This description enriches the image generation prompt. No extra dependencies required.
- Q: What is the role of audio files in the creator media library? → A: Option C — soundtrack
  reference for Reels. The operator links an audio file to a Reel slot as a musical style
  note; the generated script.md includes a section describing the audio style (tempo, mood,
  genre) to guide the creator when recording. The audio file is never published to the
  platform; it is reference-only context in the script output.
- Q: Is the visual style analysis from creator photos done on-demand per generation or
  cached as a persistent profile? → A: Option B — cached style profile. Claude analyses the
  photo library and writes a natural-language style description to
  `.instagram/memory/style-profile.md` once. All subsequent `/instagram-generate` calls read
  this file instead of re-processing photos. The profile is regenerated when the operator
  runs `/instagram-media analyze` or adds new media files via the CLI command.

## Assumptions

- The operator holds an active Meta Developer account and an Instagram Business or Creator
  account with Content Publishing API access enabled.
- Image generation uses the free tier of an external image generation API (e.g., Replicate,
  Stability AI) as the default. Local Stable Diffusion is an optional override for operators
  with GPU hardware. The system degrades gracefully if the free quota is exhausted by logging
  the failure and allowing the operator to provide an image manually.
- The system is deployed on a Linux machine (local workstation or self-hosted server) —
  managed cloud platforms (AWS Lambda, GCP Cloud Run) are out of scope for v1.
- All capabilities are invoked by the operator through Claude Code slash commands; there is no
  autonomous background daemon. The framework mirrors Speckit's skill architecture.
- Weekly planning is always operator-triggered via `/instagram-plan`; autonomous scheduling is
  out of scope for v1.
- The system manages one Instagram account per deployment instance in v1; multi-account support
  is out of scope.
- Content moderation and brand-safety checks are the operator's responsibility during the plan
  review step; the agent does not perform automated brand-safety filtering in v1.
- The operator has sufficient storage to hold generated image assets and creator media locally
  (estimated 200–500 MB per week when creator videos are included).
- Creator media files are managed by the operator; the system does not fetch, download, or
  sync media from external platforms (e.g., camera roll, Google Photos). Files must be
  manually placed in `.instagram/media/` or added via `/instagram-media add`.

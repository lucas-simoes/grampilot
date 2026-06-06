<!--
SYNC IMPACT REPORT
==================
Version change: [unversioned template] → 1.0.0
Modified principles: N/A (initial ratification)
Added sections:
  - Core Principles (5 principles defined)
  - Technology Stack & Integrations
  - Development Workflow & Quality Gates
  - Governance
Templates requiring updates:
  ✅ .specify/templates/plan-template.md — Constitution Check gates aligned
  ✅ .specify/templates/spec-template.md — no structural changes required
  ✅ .specify/templates/tasks-template.md — task categories align with principles
Follow-up TODOs:
  - TODO(IMAGE_GENERATION_PROVIDER): Confirm image/creative generation provider
    (DALL-E 3, Stable Diffusion, Canva API, or Midjourney API)
  - TODO(STORAGE_BACKEND): Define storage backend for content calendar and
    performance metrics (PostgreSQL, SQLite, or cloud store)
-->

# Studio2 Manager Constitution

## Core Principles

### I. AI Skills Architecture (NON-NEGOTIABLE)

All content generation and automation capabilities MUST be implemented as
discrete, single-responsibility AI skills. Each skill encapsulates one
capability (e.g., generate caption, plan weekly calendar, suggest hashtags,
generate carousel structure). Skills MUST be independently callable, testable,
and composable into larger workflows. No monolithic content pipelines are
permitted.

**Rationale**: Modularity ensures individual capabilities can be improved,
replaced, or A/B tested without cascading changes. Skills are the deployable
unit of this system.

### II. Meta API Integration (NON-NEGOTIABLE)

All Instagram publishing and scheduling MUST go exclusively through the Meta
Graph API. Manual posting through any interface is not permitted for automated
flows. Authentication tokens and credentials MUST be managed centrally via
environment variables — never hardcoded in source files. Token refresh logic
MUST be handled gracefully before API calls fail.

**Rationale**: Centralized API access ensures consistent scheduling behaviour,
avoids rate-limit surprises, and keeps credentials auditable and rotatable.

### III. Weekly Planning Discipline

Content planning MUST operate on a weekly cadence. The weekly planner skill
MUST produce a structured content calendar that includes, at minimum: post
format (feed, carousel, reel, story), copy draft or prompt, hashtag sets,
target publishing time, and rationale for the content theme. Planning output
MUST be stored in a versioned, machine-readable format (JSON or structured
Markdown) so downstream skills can consume it without re-planning.

**Rationale**: A predictable planning rhythm allows the system and human
collaborators to review, edit, and approve content before the scheduled window.

### IV. Multi-Format Creative Output

The system MUST support all primary Instagram content formats: single-image
feed posts, multi-image carousels, Reels (script + thumbnail), and Stories.
Each format MUST have a dedicated generation skill. Format selection MUST be
driven by the weekly plan — skills MUST NOT default to a single format when
another is specified. Creative assets (images, copy) MUST be generated or
assembled before scheduling is attempted.

**Rationale**: Instagram's algorithm rewards format diversity. Locking into a
single format reduces reach and limits creative experimentation.

### V. Observability & Traceability

Every content generation event, scheduling API call, and published post MUST
be logged with: timestamp, skill name, content ID, format, and outcome status.
When the Meta API provides post performance data (reach, impressions,
engagement rate), it MUST be retrieved and stored alongside the original
content record. Logs MUST be structured (JSON) to enable filtering and future
analytics skills.

**Rationale**: Without observability there is no feedback loop. Performance
data informs future weekly planning decisions and skill improvements.

## Technology Stack & Integrations

- **Language**: Python 3.11+
- **AI Text Generation**: Anthropic Claude API (captions, hashtags, planning,
  carousel copy, Reels scripts)
- **Image/Creative Generation**: TODO(IMAGE_GENERATION_PROVIDER) — confirm
  provider (DALL-E 3, Stable Diffusion, Canva API, or Midjourney API)
- **Meta Graph API**: v18.0+ — Instagram Content Publishing, Scheduled Posts,
  Insights endpoints
- **Storage**: TODO(STORAGE_BACKEND) — confirm backend for content calendar
  and metrics (PostgreSQL, SQLite, or cloud object store)
- **Scheduling Runtime**: No daemon or scheduler process. All skill execution
  is operator-triggered via Claude Code CLI commands. Intended publish times
  live in the content plan as reference; operators may use OS-level cron to
  invoke `/instagram-publish` at a desired time if unattended operation is needed.
- **Environment Config**: `python-dotenv` for credential and config management;
  all secrets loaded from `.env`, never committed to version control

## Development Workflow & Quality Gates

- Skills are the **unit of development**. Every new capability ships as a new
  or extended skill with its own test file.
- Each skill MUST be independently runnable via CLI (e.g.,
  `python -m skills.generate_caption --prompt "..."`) to enable manual testing
  and debugging without invoking the full agent pipeline.
- All Meta API interactions MUST be tested against the Meta API sandbox or with
  mocked HTTP responses — never against live production accounts in CI.
- A skill is considered DONE only when: it has unit tests, it produces
  structured output (JSON or typed dataclass), and it handles API errors
  gracefully with a logged failure reason.
- The weekly planning skill MUST be validated by a human reviewer before
  content is auto-scheduled. Auto-publish without review is only enabled after
  explicit per-account opt-in configuration.

## Governance

This constitution supersedes all informal conventions in this repository.
Amendments require: (1) a written rationale, (2) a version bump following
semantic versioning rules (MAJOR for principle removal/redefinition, MINOR for
new principle/section, PATCH for clarifications), and (3) an update to this
document's `Last Amended` date.

All implementation plans and feature specs MUST include a "Constitution Check"
gate that verifies compliance with the five core principles before design is
approved. Complexity beyond what is required by the weekly plan MUST be
justified explicitly in the plan document.

Use `.specify/memory/constitution.md` (this file) as the authoritative
governance reference during all `/speckit-plan`, `/speckit-specify`, and
`/speckit-tasks` command executions.

**Version**: 1.0.0 | **Ratified**: 2026-06-05 | **Last Amended**: 2026-06-05

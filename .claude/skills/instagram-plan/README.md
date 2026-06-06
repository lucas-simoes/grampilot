# /instagram-plan

Generate a 7-day content calendar for the upcoming week using your brand profile and
past performance data.

## Invocation

```
/instagram-plan
/instagram-plan --week 2026-24
/instagram-plan --theme "summer recipes"
```

## How to run

```bash
python -m instagram_manager plan [--week YYYY-WW] [--theme "optional theme"]
```

## What it does

1. Loads your brand profile from `.instagram/memory/brand.md`
2. Reads previous week's performance insights (if available)
3. Calls Claude API to generate a 7-item weekly calendar
4. Saves the plan to `.instagram/memory/plans/YYYY-WW.md` (human-readable)
   and `.instagram/memory/plans/YYYY-WW.json` (machine-readable)
5. Displays the calendar in a table

## Prerequisites

- `/instagram-init` must have been run (brand profile must exist)
- `ANTHROPIC_API_KEY` must be set in `.env`

## Expected output

```
Generating weekly plan for 2026-23 (2026-06-01 → 2026-06-07)...

📅 Weekly Plan — Week 2026-23

  Day        Time   Format    Theme
  ─────────────────────────────────────────────────────────
  Mon 01/06  09:00  feed      "5 productivity tips"
  Tue 02/06  18:00  carousel  "Morning routine guide (6 slides)"
  Wed 03/06  12:00  story     "Behind the scenes"
  Thu 04/06  09:00  feed      "Product spotlight"
  Fri 05/06  19:00  reel      "Quick tutorial"
  Sat 06/06  10:00  carousel  "Weekend inspiration"
  Sun 07/06  11:00  story     "Community Q&A"

Plan saved to .instagram/memory/plans/2026-23.md
Review the plan, make edits if needed, then run /instagram-approve.
```

## Next step

Review `.instagram/memory/plans/YYYY-WW.md`, edit any post copy or themes, then run
`/instagram-approve` to proceed to asset generation.

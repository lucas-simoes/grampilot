---
name: "instagram-insights"
description: "Fetch performance metrics for published posts from the Meta Insights API and store them locally for use in future planning."
argument-hint: "[--week YYYY-WW] [--item YYYY-WW-NNN]"
compatibility: "Requires at least one published post via /instagram-publish; META_ACCESS_TOKEN in .env"
metadata:
  author: "studio2-manager"
user-invocable: true
disable-model-invocation: false
---

## User Input

```text
$ARGUMENTS
```

## Instructions

Run `/instagram-insights` to retrieve performance metrics for published posts.

1. **Run the insights command** using the Bash tool:
   ```bash
   uv run python -m instagram_manager insights $ARGUMENTS
   ```
   Stream the output to the user.

2. **Report the result**:
   - Show reach, impressions, and engagement rate per post.
   - Highlight the top-performing post.
   - For posts with "data pending" (< 48h): mention that Meta Insights has a ~48h latency.
   - Confirm where results were saved (`.instagram/memory/insights/YYYY-WW.json`).

3. **Next step**: Tell the user to run `/instagram-plan` — the planner reads this insights file to inform next week's format and time-slot recommendations.

## Argument reference

- `--week YYYY-WW` — fetch insights for a specific ISO week (default: most recent published week)
- `--item YYYY-WW-NNN` — fetch insights for a single item

## Notes on data latency

- Feed/carousel insights: ~48 hours after publishing
- Story insights: available for 24 hours after story expiry only
- Metrics: `reach`, `impressions`, `likes`, `comments`, `shares`, `saved`, `engagement_rate`

# /instagram-insights

Fetch performance metrics for published posts from the Meta Insights API and store them
locally for use in future planning.

## Invocation

```
/instagram-insights
/instagram-insights --week 2026-23
/instagram-insights --item 2026-23-001
```

## How to run

```bash
python -m instagram_manager insights [--week YYYY-WW]
```

If `--week` is omitted, uses the most recent week with published posts.

## What it does

1. Loads all published items (those with a `meta_post_id`) from the plan
2. Calls `GET /v18.0/{MEDIA_ID}/insights?metric=reach,impressions,likes,comments,shares,saved`
3. Computes engagement rate: `(likes + comments + shares + saved) / reach`
4. Tags the top-performing post
5. Saves results to `.instagram/memory/insights/YYYY-WW.json`
6. The next `/instagram-plan` run reads this file to inform next week's recommendations

## Prerequisites

- At least one post must have been published via `/instagram-publish`
- Meta Insights data is typically available 48h after publishing
- `META_ACCESS_TOKEN` must be set in `.env`

## Expected output

```
Fetching insights for plan 2026-23 (5 published posts)...

2026-23-001 feed      reach: 1,250  impressions: 1,840  engagement: 10.2%  ⭐ top performer
2026-23-002 carousel  reach:   980  impressions: 1,200  engagement:  8.5%
2026-23-004 story     reach:   620  impressions:   740  data pending (< 48h)

Saved to .instagram/memory/insights/2026-23.json
Run /instagram-plan to use these insights for next week.
```

## Note on data latency

Meta Insights data is available approximately 48 hours after publishing. Posts published
more recently will show "data pending" and will not affect the summary statistics.
Story insights are only available for 24 hours after the story expires.

## Next step

Run `/instagram-plan` after fetching insights. The planner reads the insights file and
adjusts format, theme, and time-slot recommendations based on top performers.

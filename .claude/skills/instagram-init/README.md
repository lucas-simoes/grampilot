# /instagram-init

Initialize the Instagram Manager framework. Creates the `.instagram/` directory structure,
brand profile, and validates your API credentials.

## When to use

Run this skill once on a new deployment, or with `--reset` to update the brand profile
without losing existing plans and assets.

## How to run

Invoke `python -m instagram_manager init` from the repo root. The command is interactive —
it will prompt you for brand profile details and validate your credentials.

```bash
python -m instagram_manager init
```

## What it does

1. Creates the full `.instagram/` directory structure if it doesn't exist
2. Prompts you for your brand profile (account handle, niche, tone of voice, etc.)
3. Writes `.instagram/memory/brand.md` from your answers
4. Validates `META_ACCESS_TOKEN` against the Meta Graph API
5. Confirms `ANTHROPIC_API_KEY` is set
6. Reports setup status for each step

## Prerequisites

- `.env` file exists with at minimum `META_ACCESS_TOKEN`, `META_IG_USER_ID`, `ANTHROPIC_API_KEY`
- See `.env.example` for the full list of required variables

## Expected output

```
✓ .instagram/ directory created
✓ Brand profile written to .instagram/memory/brand.md
✓ META_ACCESS_TOKEN validated (account: @handle, expires: YYYY-MM-DD)
✓ ANTHROPIC_API_KEY set
✓ Setup complete. Run /instagram-plan to generate your first weekly calendar.
```

## Next step

After init completes: run `/instagram-plan` to generate your first 7-day content calendar.

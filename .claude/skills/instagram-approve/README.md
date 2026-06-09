# /instagram-approve

Transition the current week's content plan from `draft` to `approved`, enabling asset
generation and publishing.

## Invocation

```
/instagram-approve
/instagram-approve --week 2026-23
```

## How to run

```bash
python -m instagram_manager approve [--week YYYY-WW]
```

If `--week` is omitted, approves the most recently created draft plan.

## What it does

1. Loads the plan for the specified week
2. Verifies the plan is in `draft` status
3. Transitions status to `approved` and records `approved_at` timestamp
4. Saves the updated plan

## Expected output

```
Plan 2026-23 approved. ✓
7 items ready for asset generation.
Run /instagram-generate to produce creative assets.
```

## Error cases

- **Plan not found**: "No draft plan found for 2026-23. Run /instagram-plan first."
- **Already approved**: "Plan 2026-23 is already approved."

## Next step

Run `/instagram-generate` to produce images and captions for all approved items.

---
name: "instagram-plan"
description: "Generate a 7-day content calendar for the upcoming week using your brand profile and past performance data."
argument-hint: "[--week YYYY-WW] [--theme 'optional theme']"
compatibility: "Requires /instagram-init to have been run and ANTHROPIC_API_KEY in .env"
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

Run `/instagram-plan` to generate a 7-item weekly content calendar.

1. **Check prerequisites**: Verify `.instagram/memory/brand.md` exists. If not, tell the user to run `/instagram-init` first.

2. **Run the plan command** using the Bash tool:
   ```bash
   uv run python -m instagram_manager plan $ARGUMENTS
   ```
   Stream the output to the user as it appears.

3. **Report the result**:
   - Show the generated calendar table.
   - Confirm the plan files saved (e.g., `.instagram/memory/plans/2026-23.md`).
   - If generation failed (API error, missing key): show the error and suggest the fix.

4. **Next step**: Tell the user to review and optionally edit `.instagram/memory/plans/YYYY-WW.md`, then run `/instagram-approve` when ready.

## Argument reference

- `--week YYYY-WW` — generate plan for a specific ISO week (default: next week)
- `--theme "..."` — optional creative theme to guide the week's content

## Notes

- The planner reads `brand.md`, `style-profile.md`, and previous week's insights before calling Claude.
- The output is saved as both a human-readable `.md` and a machine-readable `.json`.

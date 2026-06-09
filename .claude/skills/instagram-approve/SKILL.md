---
name: "instagram-approve"
description: "Approve the current week's content plan, enabling asset generation and publishing."
argument-hint: "[--week YYYY-WW]"
compatibility: "Requires /instagram-plan to have been run"
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

Run `/instagram-approve` to transition a draft content plan to approved status.

1. **Run the approve command** using the Bash tool:
   ```bash
   uv run python -m instagram_manager approve $ARGUMENTS
   ```
   Stream the output to the user.

2. **Report the result**:
   - If successful: confirm the week was approved and how many items are ready.
   - If the plan is not found: tell the user to run `/instagram-plan` first.
   - If already approved: inform the user and suggest running `/instagram-generate`.

3. **Next step**: Tell the user to run `/instagram-media` to add creator photos/videos, then `/instagram-generate` to produce creative assets.

## Argument reference

- `--week YYYY-WW` — approve a specific ISO week (default: most recently created draft)

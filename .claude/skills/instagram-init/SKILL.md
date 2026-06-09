---
name: "instagram-init"
description: "Initialize the Instagram Manager framework: create directory structure, brand profile, and validate API credentials."
argument-hint: "--reset to update brand profile without losing existing data"
compatibility: "Requires uv and .env file with META_ACCESS_TOKEN, META_IG_USER_ID, ANTHROPIC_API_KEY"
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

Run `/instagram-init` to initialize the Instagram Manager framework.

1. **Check prerequisites**: Verify that a `.env` file exists at the project root. If it does not exist, tell the user:
   > `.env` not found. Copy `.env.example` to `.env` and fill in your credentials before running `/instagram-init`.
   Then stop.

2. **Run the init command** using the Bash tool:
   ```bash
   uv run python -m instagram_manager init $ARGUMENTS
   ```
   Stream the output to the user as it appears.

3. **Report the result**:
   - If successful: confirm that `.instagram/memory/brand.md` was created and credentials were validated.
   - If there were errors (e.g., invalid token, missing key): show the error clearly and suggest the fix.

4. **Next step**: After a successful init, tell the user to run `/instagram-plan` to generate their first weekly content calendar.

## Notes

- `--reset` updates the brand profile without erasing existing plans or assets.
- The command is interactive — it will prompt for brand profile details (account handle, niche, tone of voice, etc.).
- All credentials are read from `.env`; never ask the user to type them in chat.

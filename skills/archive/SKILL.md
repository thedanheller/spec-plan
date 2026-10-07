---
name: archive
description: Move a change request folder into change-requests/archive/. Takes an optional plan name/slug; without one, archives the most recently modified change request. Use when the user invokes /sp:archive or asks to archive, close out, or file away a change request.
---

# Archive Plan

Deterministic cleanup step for the change-request workflow. No judgment calls — just move the folder.

## Steps

1. **Resolve which folder to archive**:
   - If the user gave a name/slug, match it against folder names under `change-requests/` (matching on the slug portion, ignoring the date prefix is fine — e.g. `order-management` matches `2026-09-17_order-management`, and `dis-42` matches `2026-10-05_dis-42-session-close`). If more than one matches, list them and ask which one.
   - If no name was given, use the most recently modified folder directly under `change-requests/` (excluding `change-requests/archive/` itself).
   - If nothing matches or `change-requests/` has no folders, say so and stop.

2. **Create `change-requests/archive/`** if it doesn't exist.

3. **Move the folder** (with its full date-prefixed name, unchanged, and everything in it — the briefing and every plan file) into `change-requests/archive/`. Use `git mv` if the repo is a git repo and the folder is tracked, otherwise a plain move.

4. Report what was archived and where. Don't ask clarifying questions beyond disambiguating which folder, and don't touch the folder's contents.

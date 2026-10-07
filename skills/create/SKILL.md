---
name: create
description: Create a new change request folder — change-requests/<date>_<slug>/, or change-requests/<date>_<issue-id>-<slug>/ when the input starts with an issue ID — with a product-briefing.md seeded from the given name or description. Use when the user invokes /sp:create or asks to start/create a new change request or product briefing.
---

# Create Plan

Deterministic scaffolding step (step 1) for the change-request workflow. No judgment calls — just create the folder and seed the file.

## Steps

1. Take the user's input (name or short description) after `/sp:create`.

2. **Detect the issue ID.** An issue ID is a tracker key such as `DIS-42`, given as the first token of the input. Read `change-requests/.sp.yml` if it exists:
   - With `issue_prefix` set (e.g. `issue_prefix: DIS`), the first token is an issue ID when it is `<prefix>-<number>`, in any letter case (`DIS-42`, `dis-42`).
   - Without `issue_prefix`, the first token is an issue ID when it matches `^[A-Z][A-Z0-9]*-[0-9]+$` (`DIS-42`, `PROJ-1307`).
   - A separator right after the ID (`:` or `-`) belongs to the ID token and is dropped from the description.
   - Any other first token is part of the description, and the change request has no issue ID.

3. **Derive the slug** from the description (the input without the issue ID): pick the 2-3 most identifying words (drop filler words like "a", "the", "for", "add", "new"), lowercase, kebab-case. Do not use the full description as the slug.
   - `"order management for the checkout flow"` → `order-management-checkout` or `order-management`
   - `"fix the retry logic in the webhook handler"` → `webhook-retry-logic`
   - `"DIS-42 close the session on logout"` → issue ID `DIS-42`, slug `session-close`

4. **Create the folder** at the repo root, using today's date. Create `change-requests/` itself if it doesn't exist.
   - With an issue ID: `change-requests/<YYYY-MM-DD>_<issue-id-lowercase>-<slug>/`, e.g. `change-requests/2026-10-05_dis-42-session-close/`
   - Without one: `change-requests/<YYYY-MM-DD>_<slug>/`, e.g. `change-requests/2026-10-05_webhook-retry-logic/`

5. **Write `product-briefing.md`** in that folder containing the user's original name/description as given — issue ID included — with `# ` prepended to the title (the first line) so it renders as a top-level heading. The rest of the text stays exactly as written — no template, no other headings, no rewriting. This file is the user's own input; the `sp:build` skill is what turns it into something structured.

6. Report the folder path created. Don't do anything else — no clarifying questions, no drafting a build plan.

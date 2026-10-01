---
name: create
description: Create a new change request folder — change-requests/<date>_<slug>/ — with a product-briefing.md seeded from the given name or description. Use when the user invokes /sp:create or asks to start/create a new change request or product briefing.
---

# Create Plan

Deterministic scaffolding step (step 1) for the change-request workflow. No judgment calls — just create the folder and seed the file.

## Steps

1. Take the user's input (name or short description) after `/sp:create`.

2. **Derive the slug**: pick the 2-3 most identifying words from the input (drop filler words like "a", "the", "for", "add", "new"), lowercase, kebab-case. Do not use the full description as the slug.
   - `"order management for the checkout flow"` → `order-management-checkout` or `order-management`
   - `"fix the retry logic in the webhook handler"` → `webhook-retry-logic`

3. **Create the folder**: `change-requests/<YYYY-MM-DD>_<slug>/` at the repo root, using today's date. Create `change-requests/` itself if it doesn't exist.

4. **Write `product-briefing.md`** in that folder containing the user's original name/description as given, with `# ` prepended to the title (the first line) so it renders as a top-level heading. The rest of the text stays exactly as written — no template, no other headings, no rewriting. This file is the user's own input; the `sp:build` skill is what turns it into something structured.

5. Report the folder path created. Don't do anything else — no clarifying questions, no drafting a build plan.

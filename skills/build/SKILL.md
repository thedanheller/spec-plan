---
name: build
description: Turn a Product Briefing into a Build Plan for a change request. Reads change-requests/<slug>/product-briefing.md, asks the clarifying questions needed to remove ambiguity, then writes change-requests/<slug>/technical-build.md. Use when the user asks to read/review a product briefing, wants a build plan or technical plan drafted, or invokes /sp:build.
---

# Build Plan

Turns a Product Briefing into an implementation-ready Build Plan. This is step 2 of the change-request workflow (step 1, writing the Product Briefing, is done by the user beforehand; step 4, implementing the Build Plan, is the separate `sp:implement` skill).

## Layout convention

```
change-requests/
  2026-09-17_order-management/
    product-briefing.md
    technical-build.md
```

- Folder name: `<YYYY-MM-DD>_<kebab-slug>`, date is when the Product Briefing was created.
- `product-briefing.md` — input, written by the user, product perspective.
- `technical-build.md` — output of this skill, technical perspective.

## Steps

1. **Locate the change request.** If the user names a slug or path, use it. Otherwise look under `change-requests/` at the repo root for the most recently modified folder and confirm it with the user before proceeding. If `change-requests/` doesn't exist at the root, ask where it lives.

2. **Read `product-briefing.md` in full** before forming any questions. Also skim the surrounding codebase enough to know what's actually feasible — don't ask questions the code already answers.

3. **Ask every clarifying question needed before drafting** — do not start `technical-build.md` until ambiguity that would change the technical approach is resolved. Batch the questions (use `AskUserQuestion` for concrete choices with clear options; plain text for open-ended ones). Typical gaps worth asking about:
   - Scope boundaries (what's explicitly out of scope)
   - Data model / schema changes and migration strategy
   - Edge cases and error states the briefing doesn't cover
   - Integration points with existing systems
   - Non-functional constraints (performance, rollout, feature-flagging)
   - Anything the briefing states as a goal without saying how

   If the user's answer changes something, don't just note it — update your understanding before writing.

4. **Append the Q&A to `product-briefing.md`** once ambiguity is resolved, before writing the Build Plan. Add a `## Clarifications` section (create it if absent) with each question and its answer, in the order asked. This is documentation of how the briefing was refined — don't rewrite or summarize the original briefing content, only append.

5. **Write `technical-build.md`**. Structure:
   - **Summary** — one paragraph, what's being built and why, in your own words (not a copy of the briefing).
   - **Approach** — the technical direction taken and the key decisions behind it, stated as final (see writing style below).
   - **Changes** — concrete list of what changes, by area/file/module.
   - **Tasks** — numbered, independently implementable units of work. This list is what `sp:implement` will dispatch, so make each task self-contained: what changes, where, and what "done" looks like. For each task, note its ambiguity level in one line — e.g. "low ambiguity: mechanical rename across N files" vs "high ambiguity: needs to decide the caching invalidation strategy" — so `sp:implement` can route it without re-deriving that judgment.
   - **Open risks** — anything that could still go sideways.

6. **Writing style**: `technical-build.md` is a decision document, not a transcript of the conversation. Write in the affirmative, final point of view — the chosen approach is simply the approach, not "instead of X we chose Y." No meta-commentary about the back-and-forth that produced it, no residue from discarded alternatives unless a risk section needs to name a real tradeoff still in play. (The `## Clarifications` section in `product-briefing.md` is the one place the raw Q&A belongs — leave it as a record, not prose to rewrite.)

7. When `technical-build.md` is written, tell the user where it is and stop — don't start implementing. That's a separate, explicit step (`sp:implement`).

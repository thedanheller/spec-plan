---
name: build
description: Turn a Product Briefing into a Build Plan for a change request. Reads change-requests/<slug>/product-briefing.md, asks the clarifying questions needed to remove ambiguity, then writes change-requests/<slug>/technical-build.md — or technical-build-<phase>.md when a phase such as front or back is given. Use when the user asks to read/review a product briefing, wants a build plan or technical plan drafted, or invokes /sp:build.
---

# Build Plan

Turns a Product Briefing into an implementation-ready Build Plan. This is step 2 of the change-request workflow (step 1, writing the Product Briefing, is done by the user beforehand; step 4, implementing the Build Plan, is the separate `sp:implement` skill).

## Layout convention

```
change-requests/
  .sp.yml                              # optional project config
  2026-09-17_order-management/         # single build
    product-briefing.md
    technical-build.md
  2026-10-05_dis-42-session-close/     # phased build
    product-briefing.md
    technical-build-back.md
    technical-build-front.md
```

- Folder name: `<YYYY-MM-DD>_<kebab-slug>`, date is when the Product Briefing was created. The slug starts with the lowercase issue ID when the change request has one.
- `product-briefing.md` — input, written by the user, product perspective.
- `technical-build.md` — output of this skill, technical perspective.
- `technical-build-<phase>.md` — output of this skill for one phase of a phased build.

## Project config

`change-requests/.sp.yml` is optional. This skill reads two keys:

```yaml
phases: [back, front]   # the project's phases, in build order
rules_docs:             # files or folders, relative to the repo root
  - docs/rules/
```

- `phases` — the phase names this project uses and the order they are built in.
- `rules_docs` — the project's rules docs, the source of truth for business behavior. This skill reads them and leaves them untouched; changes to them go through stakeholder validation.

A project with no config file runs a single build with every question asked to the user.

## Steps

1. **Locate the change request.** If the user names a slug or path, use it. Otherwise look under `change-requests/` at the repo root for the most recently modified folder and confirm it with the user before proceeding. If `change-requests/` doesn't exist at the root, ask where it lives.

2. **Resolve the phase.** The command is `/sp:build [slug] [phase]`.
   - With two arguments, the first is the slug and the second the phase.
   - With one argument: it is the phase when it is listed in `phases`; otherwise it is the slug when it matches a change request folder; otherwise it is a phase name.
   - With `phases` configured and no phase given, build the first phase in the list that has no `technical-build-<phase>.md` yet, and tell the user which one. When every phase has a plan, say so and stop.
   - With `phases` configured, a phase outside the list stops the build: report the configured phases.
   - Without `phases`, any phase name is valid, and no phase means a single build.

   The plan file is `technical-build-<phase>.md` for a phased build and `technical-build.md` for a single build.

3. **Read the inputs in full** before forming any questions:
   - `product-briefing.md`, including `## Clarifications` from earlier phases and `## Validation` when present. `## Validation` is written by the author with stakeholder feedback on an earlier phase; treat it as input with the same weight as the briefing and leave it exactly as written.
   - The rules docs listed in `rules_docs`.
   - For a later phase, the earlier phases' `technical-build-<phase>.md` files and the code they produced — the new phase builds on what exists.
   - The surrounding codebase, enough to know what's actually feasible — don't ask questions the code already answers.

4. **Resolve every ambiguity before drafting** — do not start the plan file until ambiguity that would change the technical approach is resolved. Typical gaps:
   - Scope boundaries (what's explicitly out of scope)
   - Data model / schema changes and migration strategy
   - Edge cases and error states the briefing doesn't cover
   - Integration points with existing systems
   - Non-functional constraints (performance, rollout, feature-flagging)
   - Anything the briefing states as a goal without saying how

   For each question, check the rules docs first. A question the rules docs answer is settled by them. Ask the user the remaining questions, batched (use `AskUserQuestion` for concrete choices with clear options; plain text for open-ended ones).

   If the user's answer changes something, don't just note it — update your understanding before writing.

5. **Append the Q&A to `product-briefing.md`** once ambiguity is resolved, before writing the Build Plan. Add a `## Clarifications` section (create it if absent) with each question and its answer, in the order raised. This is documentation of how the briefing was refined — don't rewrite or summarize the original briefing content, only append.
   - In a phased build, the entries go in a `### <phase>` subsection at the end of `## Clarifications`.
   - A question settled by the rules docs is recorded with the answer `Answered by <doc>#<section>`.
   - An answer from the user that defines business behavior absent from the rules docs is tagged `[rule]`. The tag applies only when `rules_docs` is configured.

   ```markdown
   ## Clarifications

   ### back

   **Q: How long does an idle session stay open?**
   Answered by docs/rules/sessions.md#idle-timeout

   **Q: Does logging out on one device close the sessions on the others?**
   [rule] Yes. Logout closes every active session of the user.

   **Q: Is the session table migrated in place?**
   Yes, with an additive migration.
   ```

6. **Write the plan file.** Structure:
   - **Summary** — one paragraph, what's being built and why, in your own words (not a copy of the briefing). In a phased build, what this phase delivers.
   - **Approach** — the technical direction taken and the key decisions behind it, stated as final (see writing style below).
   - **Changes** — concrete list of what changes, by area/file/module.
   - **Tasks** — numbered, independently implementable units of work. This list is what `sp:implement` will dispatch, so make each task self-contained: what changes, where, and what "done" looks like. For each task, note its ambiguity level in one line — e.g. "low ambiguity: mechanical rename across N files" vs "high ambiguity: needs to decide the caching invalidation strategy" — so `sp:implement` can route it without re-deriving that judgment. When a task implements behavior defined in a rules doc, cite it in one line: `Rules: docs/rules/sessions.md#idle-timeout`.
   - **Open risks** — anything that could still go sideways.
   - **Rules to update** — present only when `rules_docs` is configured and this build produced `[rule]` answers. One entry per rule: the target doc, the section, and the proposed text. The entries are proposals for the author to take to stakeholders.

     ```markdown
     ## Rules to update

     - **docs/rules/sessions.md#logout** — "Logout closes every active session of the user, on all devices."
     ```

7. **Writing style**: the plan file is a decision document, not a transcript of the conversation. Write in the affirmative, final point of view — the chosen approach is simply the approach, not "instead of X we chose Y." No meta-commentary about the back-and-forth that produced it, no residue from discarded alternatives unless a risk section needs to name a real tradeoff still in play. (The `## Clarifications` section in `product-briefing.md` is the one place the raw Q&A belongs — leave it as a record, not prose to rewrite.)

8. When the plan file is written, tell the user where it is and stop — don't start implementing. That's a separate, explicit step (`sp:implement`).

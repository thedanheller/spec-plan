---
name: verify
description: Verify an implemented Build Plan — technical-build.md, or technical-build-<phase>.md for one phase of a phased build — against its acceptance scenarios. Checks deterministically that every scenario has a passing test, then has an independent reviewer (Claude, Codex or Kimi) judge whether each scenario is implemented, whether its test proves it, and whether anything was built beyond the plan. Read-only; writes verify.md or verify-<phase>.md into the change request folder. Use when the user asks to verify, check or review an implemented change request, or invokes /sp:verify.
---

# Verify Plan

Checks an implementation produced by the `sp:implement` skill against the scenarios in its Build Plan. This is step 5 of the change-request workflow, after `sp:implement` and before `sp:archive`.

This skill is read-only. It never edits code, tests, the plan or the briefing, and it never fixes what it finds: fixes go back through `/sp:implement`. Its only output is the report file `verify.md` (single build) or `verify-<phase>.md` (phased build) in the change request folder, and a summary to the user.

## Project config

`change-requests/.sp.yml` is optional. This skill reads one key:

```yaml
verifier: claude   # claude (default) | codex | kimi
```

- `verifier` — who runs the behavior review (layer 2). Without the key, or without the file, it is `claude`.

## Steps

1. **Locate the change request and its plan file** the same way `sp:implement` does. The command is `/sp:verify [slug] [phase]`. If the user names a slug or path, use that folder under `change-requests/`. Otherwise find the most recently modified folder under `change-requests/` and confirm it with the user. Then pick the plan file:
   - With a phase, use `technical-build-<phase>.md`. A single argument is the phase when it is listed in `phases` in `change-requests/.sp.yml` or matches a `technical-build-<phase>.md` in the located folder; otherwise it is the slug.
   - Without a phase, use the folder's only plan file. When the folder holds several plan files, list them — in the order of `phases` when configured — and ask which one to verify.

   The report is `verify-<phase>.md` for a phased plan and `verify.md` for `technical-build.md`. An existing report is replaced.

2. **Read the inputs in full:** the plan file, `product-briefing.md` (its `## Clarifications` and `## Validation` sections in particular; a briefing without `## Validation` is normal and not worth reporting), and every rules doc section the plan cites, through `Rules:` lines or scenario references. Collect the cited sections — under their own headings, verbatim — into `rules.md` in a temporary directory (`tmp="$(mktemp -d)"`), which also holds the reviewer's other inputs below.

3. **Get the diff of this build.** `sp:implement` records the working tree as it was before the build under `refs/sp/<folder>/<phase>` (phased) or `refs/sp/<folder>/build` (single build). Snapshot the working tree as it is now, the same way, and diff the two, leaving out the change request docs. From the repo root:

   ```sh
   snapshot() {
     idx="$(mktemp -d)/index"
     cp "$(git rev-parse --git-path index)" "$idx" 2>/dev/null || true
     GIT_INDEX_FILE="$idx" git add -A
     GIT_INDEX_FILE="$idx" git write-tree
   }
   base="refs/sp/2026-10-05_dis-42-session-close/back"
   now="$(snapshot)"
   git diff "$base" "$now" -- . ':(exclude)change-requests' > "$tmp/diff.patch"
   ```

   This covers uncommitted work, work committed on a branch, and a phase built on top of an earlier one: each phase's base already contains the earlier phases' work, so the diff holds this phase only.

   When the ref doesn't exist (a plan implemented before `sp:implement` recorded bases), fall back, and say in the report which base was used:
   - On a branch other than the default branch (`git symbolic-ref --short refs/remotes/origin/HEAD`, else `main` or `master`), the base is `git merge-base HEAD <default>`. For a phased plan, warn that the diff may include earlier phases' work.
   - On the default branch, the base is `HEAD`.
   - When the resulting diff is empty, ask the user for the base commit or branch.
   - Outside a git repo, there is no diff: ask the user which files to review.

4. **Layer 1 — coverage.** Deterministic: no judgment calls here.
   1. **Find the test command** from the repo: the `test` script in `package.json`, the `test` target of a `Makefile`, pytest configuration, `go.mod` (`go test ./...`), `Cargo.toml` (`cargo test`), and so on. When the repo doesn't make it clear, ask the user.
   2. **Run it once**, and keep its exit code and output. Get per-test results without changing the project — no new dependencies, no config edits — in the first form the runner offers:
      - A JUnit XML report written to `$tmp`, when the runner has one built in (e.g. pytest `--junitxml`, vitest `--reporter=junit --outputFile`, `node --test --test-reporter=junit --test-reporter-destination`).
      - Otherwise the runner's verbose or JSON output, rewritten as `$tmp/names.txt` with one `PASS|FAIL|SKIP<TAB><full test name>` line per test. The full name includes the enclosing describe/class/suite names.
      - When the runner can't report test names at all, a static scan of the test files.
   3. **Match scenarios to tests** with the `match_scenarios.py` script in this skill's base directory:

      ```sh
      python3 <skill-dir>/match_scenarios.py <plan-file> --junit "$tmp/junit.xml" > "$tmp/coverage.json"
      python3 <skill-dir>/match_scenarios.py <plan-file> --names "$tmp/names.txt" > "$tmp/coverage.json"
      python3 <skill-dir>/match_scenarios.py <plan-file> --scan <test dirs or files> > "$tmp/coverage.json"
      ```

      The script reads the `Scenarios:` bullets of the plan and matches each to the tests whose full name contains its rule reference (when present) and its scenario text. Both sides are normalized the same way first: letter case, accents, punctuation, underscores, camelCase and spacing don't matter, so `[ORD-04] WHEN the cart subtotal is 99.99, THEN …`, `test_ord_04_when_the_cart_subtotal_is_99_99_then_…` and `ord04WhenTheCartSubtotalIs9999Then…` all match. For each scenario it reports `covered`, `uncovered` or `pending`, the matching tests with their status, and, for an uncovered scenario, the closest test name as a hint. A hint is never a match. Bullets in a `Scenarios:` block that don't parse as a scenario come back as `malformed`.
   4. **Take its output as is.** Don't reinterpret a match or promote a hint to a match. When `python3` isn't available, apply the same rules by hand and say so in the report. A scan gives coverage only: per-scenario "passes" then follows the test command's exit code, and the report says so.

   A plan with no `Scenarios:` blocks (written before `sp:build` produced them) has no layer 1: say so, and run layer 2 against the tasks' "done" criteria.

5. **Layer 2 — behavior review**, by an independent reviewer that hasn't seen the implementation conversation. Put its inputs in `$tmp`: `rules.md`, `diff.patch` and `coverage.json`. Snapshot the working tree (`snapshot`) right before the review.

   The reviewer prompt, with paths filled in:

   ```text
   You are reviewing an implementation against its Build Plan. You are read-only:
   don't edit, create or delete any file. Judge only from the files below and the
   code in this repository.

   - Build Plan: <plan-file>. Each task has acceptance scenarios
     ("WHEN <condition>, THEN <outcome>"); scenarios marked "(pending: …)" are out of scope.
   - Product briefing: <briefing-file>. Read its "## Clarifications" and "## Validation" sections.
   - Rules docs sections the plan cites: <tmp>/rules.md
   - Diff of this build: <tmp>/diff.patch
   - Tests matched to each scenario: <tmp>/coverage.json

   For every non-pending scenario, answer:
   1. Implemented? yes / partial / no. Cite the code that implements it (file:line).
   2. Does its test prove it? proves / weak / not proven. "weak" means the test passes
      but misses part of the outcome; "not proven" means it would pass without the
      behavior (tautological, asserts on mocks only, asserts nothing that matters) or
      there is no test. Cite the test (file:line) and say why.
   Then list scope creep: behavior in the diff that no task, scenario, clarification or
   rules section asks for. Tests, and refactors the plan's Changes section names, are not
   scope creep. Cite file:line for each item.

   Answer in exactly this format, one block per scenario, in plan order:

   SCENARIO: <scenario text as written in the plan>
   IMPLEMENTED: <yes|partial|no> — <file:line> — <one line>
   TEST: <proves|weak|not proven> — <file:line> — <one line>

   SCOPE CREEP:
   - <file:line> — <what was built> — <why it is outside the plan>
   (or "SCOPE CREEP: none")
   ```

   Run it with the configured `verifier`:
   - **`claude`** (default) — a fresh Opus subagent: `Agent({ subagent_type: "general-purpose", model: "opus", prompt: <reviewer prompt> })`. Not a fork: the reviewer must start without this conversation.
   - **`codex`** — from the repo root: `codex exec -s read-only -C <repo-root> "<reviewer prompt>"`. Its final message is the review.
   - **`kimi`** — Kimi Code has no read-only flag, and `-p` can't be combined with `--plan`, so restrict its tools with an agent file. Write `$tmp/sp-verifier.md`:

     ```markdown
     ---
     name: sp-verifier
     description: Read-only reviewer for /sp:verify
     tools: [Read, Grep, Glob]
     ---

     You review an implementation against its Build Plan and never modify files.
     Your last message is the complete review: it is the whole handoff to the caller.
     ```

     Then, from the repo root: `kimi --agent-file "$tmp/sp-verifier.md" --add-dir "$tmp" -p "<reviewer prompt>"`. The text on stdout is the review.

   When the configured CLI isn't installed, say so and stop; don't switch reviewers on your own.

   After the review, snapshot the working tree again. When it differs from the snapshot taken before the review, the reviewer changed files: name them in the report and to the user, and leave them as they are.

6. **Check every finding against the code.** A reviewer reports what it believes, not necessarily what is true. For each `partial`, `no`, `weak` and `not proven` answer, and each scope creep item, open the cited code and confirm it:
   - Confirmed — keep it.
   - Partly right — correct it, and say what changed.
   - Wrong, or the citation doesn't support it — drop it.

   Every dropped or corrected finding goes in the report with the reason. A finding is never dropped silently.

7. **Write the report** to `verify.md` or `verify-<phase>.md` in the change request folder:

   ```markdown
   # Verify: <briefing title>[ — <phase>]

   - Plan: technical-build-back.md
   - Base: refs/sp/2026-10-05_dis-42-session-close/back
   - Test command: `npm test` — exit 0
   - Reviewer: claude (Opus subagent)

   | Rule | Scenario | Covered by test | Test passes | Reviewer | Note |
   |---|---|---|---|---|---|
   | ORD-04 | WHEN the cart subtotal is 99.99, THEN the order total is 99.99 and no discount line is shown | yes | yes | ok | |
   | ORD-04 | WHEN the cart subtotal is 120.00 and the discount threshold is 100.00, THEN the order total is 108.00 | yes | yes | weak test | asserts the total, not the discount line |
   | — | WHEN a guest submits an empty cart, THEN checkout returns 422 with the message "cart is empty" | no | — | not proven | closest test: "rejects empty cart" (hint) |

   ## Scope creep
   ## Pending scenarios
   ## Dropped reviewer findings
   ## Status
   pass with notes
   ```

   - One row per scenario, in plan order, pending scenarios included (`pending` in "Covered by test"). Rule is `—` when the scenario has none. A malformed scenario bullet gets a row with `unparsed` in "Covered by test".
   - Reviewer is the worst confirmed answer for the scenario: `not implemented`, `partial`, `not proven`, `weak test`, or `ok`.
   - **Scope creep** lists the confirmed items; **Pending scenarios** lists each with the open item it waits on; **Dropped reviewer findings** lists what step 6 dropped or corrected, and why. Write `None.` under an empty section.
   - **Status:**
     - `fail` — the test command fails, or a non-pending scenario is uncovered, unparsed or has a failing test, or a confirmed `not implemented`, `partial` or `not proven`.
     - `pass with notes` — no failure, but a confirmed `weak test`, confirmed scope creep, pending scenarios, a fallback base, or a reviewer that changed files.
     - `pass` — none of the above.

8. **Report a summary** to the user: the status, the counts (scenarios covered, failing, pending), the issues that drive the status, the dropped findings, and the report path. When the status isn't `pass`, point to `/sp:implement` for the fixes. Don't commit or push.

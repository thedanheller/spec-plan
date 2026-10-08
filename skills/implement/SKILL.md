---
name: implement
description: Implement a Build Plan — technical-build.md, or technical-build-<phase>.md for one phase of a phased build — by breaking it into tasks and dispatching each to the right implementer — Sonnet subagents for low-ambiguity tasks, Opus subagents or the codex/kimi CLIs for high-ambiguity ones. Use when the user asks to implement/build a change request, execute a build plan, or invokes /sp:implement.
---

# Implement Plan

Implements a Build Plan written by the `sp:build` skill. This is step 4 of the change-request workflow.

## Steps

1. **Locate the change request and its plan file.** The command is `/sp:implement [slug] [phase]`. If the user names a slug or path, use that folder under `change-requests/`. Otherwise find the most recently modified folder under `change-requests/` and confirm it with the user. Then pick the plan file:
   - With a phase, use `technical-build-<phase>.md` (`/sp:implement back` → `technical-build-back.md`). A single argument is the phase when it is listed in `phases` in `change-requests/.sp.yml` or matches a `technical-build-<phase>.md` in the located folder; otherwise it is the slug.
   - Without a phase, use the folder's only plan file. When the folder holds several plan files, list them — in the order of `phases` when configured — and ask which one to implement.

2. **Read the plan file in full.** Its Tasks section is the unit of dispatch. When a task cites a rules doc (`Rules: docs/rules/sessions.md#idle-timeout`), include that section in the implementer's prompt. If a task's ambiguity level isn't already noted there, classify it yourself:
   - **Low ambiguity**: the change is mechanical or fully specified — clear inputs/outputs, no architectural judgment call, low risk of misreading intent.
   - **High ambiguity**: the task requires a design decision, touches unclear or cross-cutting logic, or the plan itself leaves something open.

3. **Turn scenarios into tests.** Include the task's `Scenarios:` block in the implementer's prompt, with these instructions:
   - Each scenario becomes at least one automated test, in the project's existing test framework and layout, that sets up the scenario's condition and asserts its outcome.
   - The test's full name, as the test runner reports it, contains the rule reference in brackets (when the scenario has one) followed by the scenario text, verbatim from `WHEN` to the end: `it("[ORD-04] WHEN the cart subtotal is 99.99, THEN the order total is 99.99 and no discount line is shown")`. Where the framework names tests by identifier only, use its display-name mechanism when it has one, otherwise spell the same words as the identifier (`test_ord_04_when_the_cart_subtotal_is_99_99_then_the_order_total_is_99_99_and_no_discount_line_is_shown`).
   - Test names never contain task numbers, the change request slug, the phase, or anything else local to the plan. Plans get archived; test names stay.
   - A scenario ending in `(pending: <item>)` gets no test, and the implementer leaves the open item undecided.

   When the repo has no test setup at all, ask the user which framework to use before dispatching.

4. **Record the base snapshot.** Before dispatching the first task, record the state of the working tree so that `sp:verify` can diff exactly this build later. The ref is `refs/sp/<folder>/<phase>` for a phased build and `refs/sp/<folder>/build` for a single build, where `<folder>` is the change request folder name. Use `scripts/snapshot.sh` from the plugin root, two levels above this skill's base directory:

   ```sh
   sh <plugin-root>/scripts/snapshot.sh refs/sp/2026-10-05_dis-42-session-close/back
   ```

   The script records the ref only when it doesn't exist yet, so a re-run of this skill to fix findings keeps the original base. It snapshots through a temporary index, capturing staged, unstaged and untracked files (honoring `.gitignore`) and leaving the real index, the branch and the files untouched. The ref is local and a normal push doesn't send it.

   When the script exits non-zero, no ref is written: stop before dispatching and show the user its message. It refuses to snapshot when a submodule or other nested repository has uncommitted changes, because those would be missing from the snapshot; the user commits or stashes them inside that repository and runs `/sp:implement` again. Skip this step when the project isn't a git repo.

5. **Route each task:**
   - **Low ambiguity → Sonnet subagent.** `Agent({ subagent_type: "general-purpose", model: "sonnet", prompt: <task, with enough file/context detail to act without re-deriving intent> })`.
   - **High ambiguity → exactly one of Opus, Codex, or Kimi**, whichever best fits that specific task:
     - **Opus subagent** (`Agent({ subagent_type: "general-purpose", model: "opus", ... })`) — default choice for ambiguity that's really about deep reasoning over this codebase's own context (existing patterns, prior decisions, subtle invariants).
     - **Codex CLI** — good fit when the task benefits from a second, independent implementation opinion or a different model family's judgment on an isolated, well-bounded piece of hard logic. Run non-interactively:
       `codex exec -s workspace-write -C <repo-or-worktree-dir> "<task prompt>"`
     - **Kimi CLI** — same idea as Codex, pick when it's the better-suited alternative for the task at hand. Run non-interactively:
       `kimi -p "<task prompt>" --auto`
     Don't run more than one of these per task — pick one. If genuinely unsure, default to the Opus subagent; it has full conversation context that Codex/Kimi don't.

6. **Isolate before parallelizing.** Tasks that touch disjoint files can run concurrently; tasks that touch the same files must run sequentially. For concurrent dispatch, give each task its own git worktree so implementers can't clobber each other:
   - Claude subagents: pass `isolation: "worktree"` on the `Agent` call.
   - Codex/Kimi: `git worktree add <path> -b <branch>` yourself first, then point `-C <path>` (codex) or run kimi from that directory at it.
   After each task finishes, review its diff, merge the branch (or apply the patch) into the working tree, and remove the worktree.

   **Branch name.** When the change request folder carries an issue ID, its branch name is the folder name without the date prefix: `2026-10-05_dis-42-session-close` → `dis-42-session-close`. Use that name whenever the change needs a branch of its own — as the branch task worktrees merge into, or as the branch created for a commit the user asks for — so trackers like Linear, Jira and GitHub link it to the issue. Task worktree branches derive from it: `dis-42-session-close-task-3`.

7. **Respect dependencies.** If a task depends on another's output (shared interface, schema, etc.), dispatch it only after the dependency lands and its diff is merged in. Don't guess at an interface another task is about to define.

8. **Review every result before moving on.** A subagent or CLI run reports what it intended to do, not necessarily what it did — check the actual diff against the task's "done" criteria before treating it as complete. Check that every non-pending scenario of the task has a test named as step 3 says, and run those tests. If a result is wrong or incomplete, fix it directly or redispatch; don't silently accept it.

9. **When all tasks land**, report a short summary: what was implemented, which tasks went to which implementer, and anything that needs the user's review (design calls made without asking, deviations from the Build Plan, anything left unresolved). List the pending scenarios that were skipped, each with the open item it waits on. When the plan has a "Rules to update" section, repeat its entries in the summary as pending stakeholder validation; the rules docs themselves stay untouched. Point the user to `/sp:verify` as the next step. Don't commit or push unless asked.

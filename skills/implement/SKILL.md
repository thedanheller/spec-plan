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

3. **Route each task:**
   - **Low ambiguity → Sonnet subagent.** `Agent({ subagent_type: "general-purpose", model: "sonnet", prompt: <task, with enough file/context detail to act without re-deriving intent> })`.
   - **High ambiguity → exactly one of Opus, Codex, or Kimi**, whichever best fits that specific task:
     - **Opus subagent** (`Agent({ subagent_type: "general-purpose", model: "opus", ... })`) — default choice for ambiguity that's really about deep reasoning over this codebase's own context (existing patterns, prior decisions, subtle invariants).
     - **Codex CLI** — good fit when the task benefits from a second, independent implementation opinion or a different model family's judgment on an isolated, well-bounded piece of hard logic. Run non-interactively:
       `codex exec -s workspace-write -C <repo-or-worktree-dir> "<task prompt>"`
     - **Kimi CLI** — same idea as Codex, pick when it's the better-suited alternative for the task at hand. Run non-interactively:
       `kimi -p "<task prompt>" --auto`
     Don't run more than one of these per task — pick one. If genuinely unsure, default to the Opus subagent; it has full conversation context that Codex/Kimi don't.

4. **Isolate before parallelizing.** Tasks that touch disjoint files can run concurrently; tasks that touch the same files must run sequentially. For concurrent dispatch, give each task its own git worktree so implementers can't clobber each other:
   - Claude subagents: pass `isolation: "worktree"` on the `Agent` call.
   - Codex/Kimi: `git worktree add <path> -b <branch>` yourself first, then point `-C <path>` (codex) or run kimi from that directory at it.
   After each task finishes, review its diff, merge the branch (or apply the patch) into the working tree, and remove the worktree.

   **Branch name.** When the change request folder carries an issue ID, its branch name is the folder name without the date prefix: `2026-10-05_dis-42-session-close` → `dis-42-session-close`. Use that name whenever the change needs a branch of its own — as the branch task worktrees merge into, or as the branch created for a commit the user asks for — so trackers like Linear, Jira and GitHub link it to the issue. Task worktree branches derive from it: `dis-42-session-close-task-3`.

5. **Respect dependencies.** If a task depends on another's output (shared interface, schema, etc.), dispatch it only after the dependency lands and its diff is merged in. Don't guess at an interface another task is about to define.

6. **Review every result before moving on.** A subagent or CLI run reports what it intended to do, not necessarily what it did — check the actual diff against the task's "done" criteria before treating it as complete. If a result is wrong or incomplete, fix it directly or redispatch; don't silently accept it.

7. **When all tasks land**, report a short summary: what was implemented, which tasks went to which implementer, and anything that needs the user's review (design calls made without asking, deviations from the Build Plan, anything left unresolved). When the plan has a "Rules to update" section, repeat its entries in the summary as pending stakeholder validation; the rules docs themselves stay untouched. Don't commit or push unless asked.

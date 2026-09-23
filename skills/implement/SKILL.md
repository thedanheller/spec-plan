---
name: implement
description: Implement a Build Plan by breaking it into tasks and dispatching each to the right implementer — Sonnet subagents for low-ambiguity tasks, Opus subagents or the codex/kimi CLIs for high-ambiguity ones. Use when the user asks to implement/build a change request, execute a build plan, or invokes /sp:implement.
---

# Implement Plan

Implements a Build Plan written by the `sp:build` skill. This is step 4 of the change-request workflow.

## Steps

1. **Locate the change request.** If the user names a slug or path, use `change-requests/<slug>/technical-build.md`. Otherwise find the most recently modified folder under `change-requests/` and confirm it with the user.

2. **Read `technical-build.md` in full.** Its Tasks section is the unit of dispatch. If a task's ambiguity level isn't already noted there, classify it yourself:
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

5. **Respect dependencies.** If a task depends on another's output (shared interface, schema, etc.), dispatch it only after the dependency lands and its diff is merged in. Don't guess at an interface another task is about to define.

6. **Review every result before moving on.** A subagent or CLI run reports what it intended to do, not necessarily what it did — check the actual diff against the task's "done" criteria before treating it as complete. If a result is wrong or incomplete, fix it directly or redispatch; don't silently accept it.

7. **When all tasks land**, report a short summary: what was implemented, which tasks went to which implementer, and anything that needs the user's review (design calls made without asking, deviations from the Build Plan, anything left unresolved). Don't commit or push unless asked.

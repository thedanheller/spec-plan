# spec-plan

A Claude Code plugin for a change-request workflow. Each change lives in its own folder under `change-requests/` and moves through five commands:

| Command | Step | Output |
|---|---|---|
| `/sp:create [issue-id] <description>` | Scaffold the change request | `change-requests/<YYYY-MM-DD>_<slug>/product-briefing.md` |
| `/sp:build [slug] [phase]` | Clarify the briefing and write the technical plan | `## Clarifications` in the briefing, `technical-build.md` or `technical-build-<phase>.md` |
| `/sp:implement [slug] [phase]` | Dispatch the plan's tasks to Sonnet, Opus, Codex or Kimi, turning each scenario into a test | Code and tests in the working tree |
| `/sp:verify [slug] [phase]` | Check every scenario has a passing test, then have an independent reviewer check the behavior | `verify.md` or `verify-<phase>.md` |
| `/sp:archive [slug]` | File the change request away | `change-requests/archive/<folder>` |

The flow is `create → build → implement → verify → archive`, with `build → implement → verify` once per phase in a phased build.

## Scenarios

Every task in a Build Plan ends with acceptance scenarios, one per line, as `WHEN <condition>, THEN <observable outcome>`:

```markdown
2. Apply the threshold discount in the checkout totals service. Done when order totals reflect the discount rule.
   Low ambiguity: threshold, rate and rounding are specified.
   Scenarios:
   - WHEN the cart subtotal is 120.00 and the discount threshold is 100.00, THEN the order total is 108.00
   - WHEN the cart subtotal is 99.99, THEN the order total is 99.99 and no discount line is shown
```

- Scenarios are concrete: real values in, an observable outcome out.
- A scenario restates behavior that the briefing, the rules docs or `## Clarifications` already define; it never adds behavior. A scenario that needs a fact none of them gives becomes a clarifying question in `/sp:build`.
- `/sp:implement` turns each scenario into at least one automated test whose name contains the scenario text (and its rule reference, see [Rules docs](#rules-docs)). Test names never contain task numbers or anything else local to the plan, because plans get archived and tests stay.

## Verification

`/sp:verify` checks an implemented plan in two layers and writes `verify.md` (or `verify-<phase>.md`) into the change request folder. It is read-only: fixes go back through `/sp:implement`.

1. **Coverage** — deterministic. It runs the project's test command (asking when the repo doesn't make it clear) and matches every scenario to the tests whose name contains it, ignoring case, punctuation, underscores and camelCase. Unmatched scenarios are listed, never dropped.
2. **Behavior review** — an independent reviewer reads the plan, the cited rules sections, the Clarifications, `## Validation` and the diff of the build, and answers for each scenario whether it is implemented and whether its test actually proves it, then lists anything built beyond the plan. `/sp:verify` checks each finding against the code before reporting it and lists the ones it dropped.

The diff covers exactly one build: `/sp:implement` records the working tree under a local ref, `refs/sp/<folder>/<phase>` or `refs/sp/<folder>/build`, before its first task, and `/sp:verify` diffs the current working tree against it. Uncommitted work, branch commits and a phase built on an earlier phase all diff correctly.

```markdown
| Rule | Scenario | Covered by test | Test passes | Reviewer | Note |
|---|---|---|---|---|---|
| — | WHEN the cart subtotal is 99.99, THEN the order total is 99.99 and no discount line is shown | yes | yes | ok | |
| — | WHEN the cart subtotal is 120.00 and the discount threshold is 100.00, THEN the order total is 108.00 | yes | yes | weak test | asserts the total, not the discount line |
```

The table is followed by scope creep findings, pending scenarios, dropped reviewer findings and a final status: `pass`, `pass with notes` or `fail`.

## Project config

Each project tunes the workflow with an optional `change-requests/.sp.yml`. Every key is optional, and a project without the file runs the plain flow above.

```yaml
issue_prefix: DIS       # issue IDs look like DIS-42
phases: [back, front]   # the project's phases, in build order
rules_docs:             # source of truth for business behavior
  - docs/rules/
verifier: codex         # claude (default) | codex | kimi
```

| Key | Effect |
|---|---|
| `issue_prefix` | `/sp:create` recognizes `<prefix>-<number>` as the issue ID, in any letter case. Without the key, an uppercase tracker key (`DIS-42`, `PROJ-1307`) at the start of the description is recognized. |
| `phases` | `/sp:build` and `/sp:implement` accept these phase names. `/sp:build` with no phase builds the next phase in the list that has no plan yet. Without the key, any phase name is accepted and no phase means a single build. |
| `rules_docs` | `/sp:build` reads these files and folders before asking questions, cites them in tasks and scenarios, and proposes additions to them. |
| `verifier` | Who runs the `/sp:verify` behavior review. `claude` (default) is a fresh Opus subagent that hasn't seen the implementation conversation; `codex` runs `codex exec -s read-only`; `kimi` runs Kimi Code with an agent file that allows only its read tools. |

### Issue IDs

```
/sp:create DIS-42 close the session on logout
→ change-requests/2026-10-05_dis-42-session-close/product-briefing.md
```

The briefing title keeps the ID as typed (`# DIS-42 close the session on logout`). When `/sp:implement` needs a branch for the change, it uses `dis-42-session-close`, which Linear, Jira and GitHub link to the issue.

### Phased builds

```
/sp:build back        → technical-build-back.md, clarifications under "### back"
/sp:implement back
/sp:verify back       → verify-back.md
                      # the author adds "## Validation" to the briefing with stakeholder feedback
/sp:build front       → technical-build-front.md, clarifications under "### front"
/sp:implement front
/sp:verify front      → verify-front.md, reviewing only the front phase's diff
/sp:archive           # moves the whole folder
```

A later phase reads the briefing, its `## Validation` section, the earlier phases' plans and the code they produced. `## Validation` belongs to the author; the skills read it and leave it as written.

```
change-requests/2026-10-05_dis-42-session-close/
  product-briefing.md        # briefing, ## Clarifications (### back, ### front), ## Validation
  technical-build-back.md
  verify-back.md
  technical-build-front.md
  verify-front.md
```

### Rules docs

With `rules_docs` configured, `/sp:build` checks the rules docs before asking each question and records the ones they settle:

```markdown
## Clarifications

**Q: How long does an idle session stay open?**
Answered by docs/rules/sessions.md#idle-timeout
```

Tasks in the Build Plan cite the section they implement, and each scenario starts with the reference of the rule it derives from: the identifier the rules doc uses (`[SES-03]`), or the cited anchor when the doc has no identifiers (`[docs/rules/sessions.md#idle-timeout]`):

```markdown
3. Expire idle sessions in the session middleware. Done when a session idle past the timeout returns 401.
   Low ambiguity: the timeout and the response are specified.
   Rules: docs/rules/sessions.md#idle-timeout
   Scenarios:
   - [SES-03] WHEN a session has been idle for 31 minutes and the timeout is 30 minutes, THEN the next request returns 401
   - [SES-03] WHEN a session has been idle for 29 minutes, THEN the next request succeeds
   - [SES-05] WHEN an upload is in progress at the timeout, THEN the session stays open until the grace period ends (pending: SES-05 upload grace period)
```

The test for the first scenario is named `[SES-03] WHEN a session has been idle for 31 minutes and the timeout is 30 minutes, THEN the next request returns 401`, or the closest form the test framework allows. A scenario that depends on an item the rules docs mark as open is marked `(pending: <item>)`: it gets no test, and `/sp:implement` and `/sp:verify` list it until the rules doc settles it.

### New business rules

An answer that defines business behavior absent from the rules docs is tagged `[rule]` in Clarifications, and the Build Plan lists it under "Rules to update" with the target doc, the section and the proposed text:

```markdown
**Q: Does logging out on one device close the sessions on the others?**
[rule] Yes. Logout closes every active session of the user.
```

```markdown
## Rules to update

- **docs/rules/sessions.md#logout** — "Logout closes every active session of the user, on all devices."
```

The author takes these proposals to stakeholders and edits the rules docs once they are validated.

## Layout

```
.claude-plugin/
  plugin.json        # plugin manifest — the name "sp" sets the command prefix
  marketplace.json   # single-plugin marketplace pointing at this repo
skills/
  create/SKILL.md    # /sp:create
  build/SKILL.md     # /sp:build
  implement/SKILL.md # /sp:implement
  verify/SKILL.md    # /sp:verify
  verify/match_scenarios.py  # deterministic scenario-to-test matching for /sp:verify
  archive/SKILL.md   # /sp:archive
install.sh           # installs into ~/.claude or the current directory
```

## Installation

`install.sh` registers this repo as the `spec-plan` marketplace and enables `sp@spec-plan`. The plugin loads in place from the repo, so edits to `skills/` take effect at the next session start or `/reload-plugins`. Re-running the script is safe.

```sh
~/dev/spec-plan/install.sh --global               # ~/.claude/settings.json — every project
~/dev/spec-plan/install.sh --local                # ./.claude/settings.local.json — current directory only
~/dev/spec-plan/install.sh --local ~/dev/my-app   # .claude/settings.local.json in the given directory
```

Add `--uninstall` to any of these to remove the plugin and marketplace from that scope.

## Development

Load the plugin from the working copy for a single session, with nothing installed:

```sh
claude --plugin-dir ~/dev/spec-plan
```

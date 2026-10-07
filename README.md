# spec-plan

A Claude Code plugin for a change-request workflow. Each change lives in its own folder under `change-requests/` and moves through four commands:

| Command | Step | Output |
|---|---|---|
| `/sp:create [issue-id] <description>` | Scaffold the change request | `change-requests/<YYYY-MM-DD>_<slug>/product-briefing.md` |
| `/sp:build [slug] [phase]` | Clarify the briefing and write the technical plan | `## Clarifications` in the briefing, `technical-build.md` or `technical-build-<phase>.md` |
| `/sp:implement [slug] [phase]` | Dispatch the plan's tasks to Sonnet, Opus, Codex or Kimi | Code changes in the working tree |
| `/sp:archive [slug]` | File the change request away | `change-requests/archive/<folder>` |

## Project config

Each project tunes the workflow with an optional `change-requests/.sp.yml`. Every key is optional, and a project without the file runs the plain four-command flow above.

```yaml
issue_prefix: DIS       # issue IDs look like DIS-42
phases: [back, front]   # the project's phases, in build order
rules_docs:             # source of truth for business behavior
  - docs/rules/
```

| Key | Effect |
|---|---|
| `issue_prefix` | `/sp:create` recognizes `<prefix>-<number>` as the issue ID, in any letter case. Without the key, an uppercase tracker key (`DIS-42`, `PROJ-1307`) at the start of the description is recognized. |
| `phases` | `/sp:build` and `/sp:implement` accept these phase names. `/sp:build` with no phase builds the next phase in the list that has no plan yet. Without the key, any phase name is accepted and no phase means a single build. |
| `rules_docs` | `/sp:build` reads these files and folders before asking questions, cites them in tasks, and proposes additions to them. |

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
                      # the author adds "## Validation" to the briefing with stakeholder feedback
/sp:build front       → technical-build-front.md, clarifications under "### front"
/sp:implement front
/sp:archive           # moves the whole folder
```

A later phase reads the briefing, its `## Validation` section, the earlier phases' plans and the code they produced. `## Validation` belongs to the author; the skills read it and leave it as written.

```
change-requests/2026-10-05_dis-42-session-close/
  product-briefing.md        # briefing, ## Clarifications (### back, ### front), ## Validation
  technical-build-back.md
  technical-build-front.md
```

### Rules docs

With `rules_docs` configured, `/sp:build` checks the rules docs before asking each question and records the ones they settle:

```markdown
## Clarifications

**Q: How long does an idle session stay open?**
Answered by docs/rules/sessions.md#idle-timeout
```

Tasks in the Build Plan cite the section they implement:

```markdown
3. Expire idle sessions in the session middleware. Done when a session idle past the timeout returns 401.
   Low ambiguity: the timeout and the response are specified.
   Rules: docs/rules/sessions.md#idle-timeout
```

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

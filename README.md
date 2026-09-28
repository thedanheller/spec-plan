# spec-plan

A Claude Code plugin for a change-request workflow. Each change lives in its own folder under `change-requests/` and moves through four commands:

| Command | Step | Output |
|---|---|---|
| `/sp:create <description>` | Scaffold the change request | `change-requests/<YYYY-MM-DD>_<slug>/product-briefing.md` |
| `/sp:build [slug]` | Clarify the briefing and write the technical plan | `## Clarifications` in the briefing, `technical-build.md` |
| `/sp:implement [slug]` | Dispatch the plan's tasks to Sonnet, Opus, Codex or Kimi | Code changes in the working tree |
| `/sp:archive [slug]` | File the change request away | `change-requests/archive/<folder>` |

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

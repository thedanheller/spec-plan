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
```

## Development

Load the plugin straight from the working copy for a session:

```sh
claude --plugin-dir ~/dev/spec-plan
```

Edits to `skills/*/SKILL.md` take effect in the next session started this way.

## Installation

From inside Claude Code:

```
/plugin marketplace add ~/dev/spec-plan
/plugin install sp@spec-plan
```

After pushing the repo to GitHub, replace the local path with `<owner>/spec-plan`. Pull new versions with `/plugin marketplace update spec-plan`.

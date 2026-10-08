# spec-plan

This repo is the source of the `sp` Claude Code plugin. Each skill under `skills/<name>/SKILL.md` becomes the command `/sp:<name>`.

## Conventions

- The skill's frontmatter `name` matches its folder name (`create`, `build`, `implement`, `verify`, `archive`); the `sp:` prefix comes from the plugin name in `.claude-plugin/plugin.json`.
- Skills refer to each other as `sp:<name>` (e.g. "the `sp:build` skill") and to commands as `/sp:<name>`.
- Bump `version` in `.claude-plugin/plugin.json` on every change meant to reach installed copies.
- Keep `README.md`'s command table in sync with the skills.

## Testing a change

Run `claude --plugin-dir <path-to-this-repo>` from a scratch repo, or `./install.sh --local <scratch-repo>`, and exercise the full flow: `/sp:create` → `/sp:build` → `/sp:implement` → `/sp:verify` → `/sp:archive`.

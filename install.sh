#!/usr/bin/env bash
# Install the sp plugin from this repo into Claude Code.
#
#   ./install.sh --global              # ~/.claude/settings.json, every project
#   ./install.sh --local [dir]         # <dir>/.claude/settings.local.json (default: current directory)
#   ./install.sh --global --uninstall
#   ./install.sh --local [dir] --uninstall
#
# The plugin loads in place from this repo, so edits to skills/ take effect at
# the next session start or /reload-plugins. Re-running is safe.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MARKETPLACE="spec-plan"
PLUGIN="sp@${MARKETPLACE}"

usage() {
  sed -n '2,10p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
  exit "${1:-0}"
}

scope=""
target_dir="$PWD"
action="install"

while [[ $# -gt 0 ]]; do
  case "$1" in
    -g|--global) scope="user" ;;
    -l|--local)
      scope="local"
      if [[ $# -gt 1 && "$2" != -* ]]; then
        target_dir="$2"
        shift
      fi
      ;;
    -u|--uninstall) action="uninstall" ;;
    -h|--help) usage 0 ;;
    *) echo "Unknown argument: $1" >&2; usage 1 ;;
  esac
  shift
done

[[ -n "$scope" ]] || { echo "Choose --global or --local." >&2; usage 1; }
command -v claude >/dev/null || { echo "claude CLI not found on PATH." >&2; exit 1; }

if [[ "$scope" == "local" ]]; then
  [[ -d "$target_dir" ]] || { echo "Directory not found: $target_dir" >&2; exit 1; }
  cd "$target_dir"
  echo "Target: $(pwd)/.claude/settings.local.json"
else
  echo "Target: ${CLAUDE_CONFIG_DIR:-$HOME/.claude}/settings.json"
fi

if [[ "$action" == "install" ]]; then
  claude plugin validate "$REPO_DIR" >/dev/null
  claude plugin marketplace add "$REPO_DIR" --scope "$scope"
  claude plugin install "$PLUGIN" --scope "$scope"
else
  claude plugin uninstall "$PLUGIN" --scope "$scope"
  claude plugin marketplace remove "$MARKETPLACE" --scope "$scope"
fi

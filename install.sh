#!/usr/bin/env bash
# Install the sp plugin from this repo into Claude Code.
#
#   ./install.sh --global              # ~/.claude/settings.json, every project
#   ./install.sh --local [dir]         # <dir>/.claude/settings.local.json (default: current directory)
#   ./install.sh --global --uninstall
#   ./install.sh --local [dir] --uninstall
#
# Installing copies the plugin into Claude Code's plugin cache, replacing any
# earlier install in that scope. Re-run it to pick up edits to skills/.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MARKETPLACE="spec-plan"
PLUGIN="sp@${MARKETPLACE}"
PLUGINS_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/plugins"
CACHE_DIR="${PLUGINS_DIR}/cache/${MARKETPLACE}/sp"
REGISTRY="${PLUGINS_DIR}/installed_plugins.json"

# Delete cached copies of the plugin that no install, in any scope, still uses.
prune_cache() {
  local dir
  for dir in "$CACHE_DIR"/*/; do
    dir="${dir%/}"
    [[ -d "$dir" ]] || continue
    if [[ -f "$REGISTRY" ]] && grep -qF "\"$dir\"" "$REGISTRY"; then
      continue
    fi
    echo "Removing old copy: $dir"
    rm -rf "$dir"
  done
}

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
  if claude plugin uninstall "$PLUGIN" --scope "$scope" >/dev/null 2>&1; then
    echo "Removed previous install of $PLUGIN."
  fi
  prune_cache
  claude plugin marketplace add "$REPO_DIR" --scope "$scope"
  claude plugin install "$PLUGIN" --scope "$scope"
else
  claude plugin uninstall "$PLUGIN" --scope "$scope"
  claude plugin marketplace remove "$MARKETPLACE" --scope "$scope"
  prune_cache
fi

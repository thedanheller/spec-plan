#!/bin/sh
# Snapshot the working tree of the current git repo for the sp workflow.
#
#   sh snapshot.sh          print the tree of the working tree as it is now
#   sh snapshot.sh REF      record that tree as a commit at REF, unless REF exists
#
# The snapshot goes through a temporary index, so it captures staged, unstaged
# and untracked files (honoring .gitignore) and leaves the real index, the
# branch and the files untouched.
#
# A nested repository (a submodule or an embedded repo) is captured only as
# the commit it has checked out. When one has uncommitted changes, the
# snapshot would miss them, so this script fails instead. Any failure exits
# non-zero with a message on stderr, before a ref is written.
set -eu

ref="${1:-}"
if [ -n "$ref" ] && git rev-parse -q --verify "$ref" >/dev/null; then
  echo "exists: $ref"
  exit 0
fi

cd "$(git rev-parse --show-toplevel)"

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
idx="$tmp/index"
cp "$(git rev-parse --git-path index)" "$idx" 2>/dev/null || true

if ! GIT_INDEX_FILE="$idx" git add -A; then
  echo "snapshot failed: git add -A could not stage the working tree" >&2
  exit 1
fi
tree="$(GIT_INDEX_FILE="$idx" git write-tree)"

# Nested repositories show up in the tree as gitlinks ("commit" entries).
dirty=""
git ls-tree -r "$tree" | awk -F '\t' '$1 ~ / commit / { print $2 }' > "$tmp/gitlinks"
while IFS= read -r path; do
  [ -e "$path/.git" ] || continue
  if [ -n "$(git -C "$path" status --porcelain)" ]; then
    dirty="$dirty $path"
  fi
done < "$tmp/gitlinks"
if [ -n "$dirty" ]; then
  echo "snapshot failed: uncommitted changes inside nested repositories:$dirty" >&2
  echo "Commit or stash them inside each repository, then run again." >&2
  exit 1
fi

if [ -z "$ref" ]; then
  echo "$tree"
  exit 0
fi

if parent="$(git rev-parse -q --verify HEAD)"; then
  commit="$(git -c user.name=sp -c user.email=sp@localhost commit-tree "$tree" -p "$parent" -m "sp base: $ref")"
else
  commit="$(git -c user.name=sp -c user.email=sp@localhost commit-tree "$tree" -m "sp base: $ref")"
fi
git update-ref "$ref" "$commit"
echo "recorded: $ref $commit"

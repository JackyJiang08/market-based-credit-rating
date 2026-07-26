#!/bin/sh
# Install the repository's git hooks into .git/hooks/.
#
# This copies files rather than setting core.hooksPath, because changing git
# config is the repository owner's decision (see CLAUDE.md "Git rules"). If you
# would rather have the hooks tracked and shared automatically, run:
#     git config core.hooksPath .githooks
set -eu

root=$(git rev-parse --show-toplevel)
src="$root/.githooks"
dst="$root/.git/hooks"

[ -d "$src" ] || { echo "no .githooks/ directory found" >&2; exit 1; }
mkdir -p "$dst"

for hook in "$src"/*; do
    [ -f "$hook" ] || continue
    name=$(basename "$hook")
    cp "$hook" "$dst/$name"
    chmod +x "$dst/$name"
    echo "installed $name -> .git/hooks/$name"
done

echo
echo "The pre-push hook rejects a push whose commits do not touch docs/DEVLOG.md."
echo "Emergency bypass: ALLOW_MISSING_DEVLOG=1 git push ..."

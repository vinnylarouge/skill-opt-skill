#!/usr/bin/env bash
set -euo pipefail
SRC="$(cd "$(dirname "$0")/skill" && pwd)"
DEST="$HOME/.claude/skills/skill-opt"
if [ -L "$DEST" ]; then
  rm -f "$DEST"
elif [ -e "$DEST" ]; then
  echo "refusing to overwrite $DEST: exists and is not a symlink. Remove it manually." >&2
  exit 1
fi
ln -s "$SRC" "$DEST"
echo "linked $DEST -> $SRC"

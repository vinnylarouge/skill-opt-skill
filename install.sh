#!/usr/bin/env bash
set -euo pipefail
SRC="$(cd "$(dirname "$0")/skill" && pwd)"
DEST="$HOME/.claude/skills/skill-opt"
if [ -L "$DEST" ] || [ -e "$DEST" ]; then
  echo "removing existing $DEST"; rm -rf "$DEST"
fi
ln -s "$SRC" "$DEST"
echo "linked $DEST -> $SRC"

#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${WORKBUDDY_SKILLS_DIR:-$HOME/.workbuddy/skills}"

python3 "$ROOT/scripts/sync-workbuddy-skills.py"
mkdir -p "$DEST"

for skill_dir in "$ROOT"/workbuddy-skills/*; do
  [ -d "$skill_dir" ] || continue
  name="$(basename "$skill_dir")"
  rm -rf "$DEST/$name"
  cp -R "$skill_dir" "$DEST/$name"
done

echo "Installed WorkBuddy skills to $DEST"
echo "NOTE: 'ai-berkshire-tools' is a shared dependency of the other AI Berkshire"
echo "      skills (tool resolution chain step 2). Keep it installed alongside them."
echo "NOTE: Skills with the same name at the destination are overwritten."
echo "Restart WorkBuddy (or refresh its skill list) to pick up new skills."
